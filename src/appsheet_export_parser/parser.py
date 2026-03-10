"""Top-level parse orchestrator — ties all stages together."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .analyze.classifier import classify_tables_auto, load_table_classification
from .analyze.computed_fields import extract_computed_fields
from .analyze.enums import extract_enum_fields
from .analyze.relationships import extract_relationships
from .analyze.validator import ValidationReport, validate_counts
from .extract.cleaner import clean_text
from .extract.header import HeaderCounts, extract_app_metadata, extract_header_counts
from .extract.pdf import extract_text_from_pdf, get_page_count
from .generate.json_output import build_export, write_json
from .parse.section_finder import find_sections
from .parse.schema_parser import parse_all_schemas
from .parse.action_parser import parse_actions
from .parse.slice_parser import parse_slices


def parse_pdf(
    pdf_path: str | Path,
    output_path: str | Path | None = None,
    app_config_path: str | Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Parse an AppSheet documentation PDF into structured data.

    This is the main entry point for PDF-based parsing. It orchestrates
    the full pipeline: extract → parse → analyze → generate.

    Args:
        pdf_path: Path to the AppSheet documentation PDF.
        output_path: Optional path to write JSON output.
        app_config_path: Optional path to app config YAML for table classification.
        verbose: Print progress to stdout.

    Returns:
        The parsed export dict.
    """
    pdf_path = Path(pdf_path)
    _log = print if verbose else lambda *a, **k: None

    # Stage 1: Extract
    _log(f"Extracting text from {pdf_path.name}...")
    raw_text = extract_text_from_pdf(pdf_path)
    page_count = get_page_count(raw_text)
    _log(f"  {len(raw_text):,} characters, {page_count or '?'} pages")

    # Extract header counts for validation
    header_counts = extract_header_counts(raw_text)
    app_meta = extract_app_metadata(raw_text)
    if header_counts.has_data:
        _log(f"  Header: {header_counts.tables} tables, {header_counts.columns} columns, "
             f"{header_counts.actions} actions")

    # Clean text
    cleaned = clean_text(raw_text, page_count)
    lines = cleaned.split("\n")
    _log(f"  Cleaned to {len(lines):,} lines")

    # Stage 2: Parse
    _log("Finding sections...")
    sections = find_sections(lines)
    _log(f"  Schema blocks: {len(sections.schema_blocks)}")

    _log("Parsing schemas...")
    schemas = parse_all_schemas(lines, sections)
    total_cols = sum(len(cols) for cols in schemas.values())
    _log(f"  {len(schemas)} tables, {total_cols} columns")

    _log("Parsing actions...")
    actions = parse_actions(lines, sections)
    _log(f"  {len(actions)} actions")

    _log("Parsing slices...")
    slices = parse_slices(lines, sections)
    _log(f"  {len(slices)} slices")

    # Stage 3: Analyze
    _log("Analyzing relationships...")
    rels = extract_relationships(schemas)
    relationships = [r.model_dump() for r in rels]
    _log(f"  {len(relationships)} relationships")

    _log("Extracting computed fields...")
    comp = extract_computed_fields(schemas)
    computed_fields = [c.model_dump() for c in comp]
    _log(f"  {len(computed_fields)} computed fields")

    _log("Extracting enum fields...")
    enum_list = extract_enum_fields(schemas)
    enum_fields = [e.model_dump() for e in enum_list]
    _log(f"  {len(enum_fields)} enum fields")

    # Classify tables
    all_table_names = list(schemas.keys())
    if app_config_path:
        classification = load_table_classification(app_config_path, all_table_names)
    else:
        classification = classify_tables_auto(all_table_names)

    # Validate
    _log("Validating against header counts...")
    validation = validate_counts(
        header_counts, schemas, actions, slices,
        process_tables=classification.process,
    )
    _log(validation.format_report())

    # Stage 4: Generate
    export = build_export(
        schemas=schemas,
        relationships=relationships,
        actions=actions,
        slices=slices,
        computed_fields=computed_fields,
        enum_fields=enum_fields,
        core_tables=classification.core,
        process_tables=classification.process,
        header_counts=header_counts,
        app_metadata=app_meta,
        source_file=str(pdf_path),
        source_pages=page_count or 0,
    )

    if output_path:
        out = write_json(export, output_path)
        _log(f"\nJSON output: {out}")

    return export
