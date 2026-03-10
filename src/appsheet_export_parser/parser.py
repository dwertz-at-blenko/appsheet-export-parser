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
from .parse.view_parser import parse_views
from .parse.format_rule_parser import parse_format_rules


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

    return _run_pipeline(
        lines=lines,
        header_counts=header_counts,
        app_meta=app_meta,
        app_config_path=app_config_path,
        source_file=str(pdf_path),
        source_pages=page_count or 0,
        output_path=output_path,
        verbose=verbose,
    )


def parse_url(
    app_id: str,
    output_path: str | Path | None = None,
    app_config_path: str | Path | None = None,
    chrome_profile: str = "/tmp/chrome-shopify-app",
    verbose: bool = False,
) -> dict[str, Any]:
    """Parse an AppSheet app directly from its live documentation URL.

    Uses Chrome CDP to fetch the live page, then runs the same parse
    pipeline as parse_pdf but skips PDF extraction.

    Args:
        app_id: AppSheet app ID (e.g., "c5c1b987-2ea4-48fe-8e73-3f6e18a77b19").
        output_path: Optional path to write JSON output.
        app_config_path: Optional path to app config YAML for table classification.
        chrome_profile: Path to Chrome user-data-dir with auth cookies.
        verbose: Print progress to stdout.

    Returns:
        The parsed export dict.
    """
    from .extract.url_fetcher import fetch_appdoc_text

    _log = print if verbose else lambda *a, **k: None

    url = f"https://www.appsheet.com/template/appdoc?appId={app_id}"
    _log(f"Fetching live page for app {app_id}...")
    raw_text = fetch_appdoc_text(url, chrome_profile)
    _log(f"  {len(raw_text):,} characters")

    # Extract header counts and metadata
    header_counts = extract_header_counts(raw_text)
    app_meta = extract_app_metadata(raw_text)
    if header_counts.has_data:
        _log(f"  Header: {header_counts.tables} tables, {header_counts.columns} columns, "
             f"{header_counts.actions} actions")

    # URL text is already clean — no page breaks or PDF artifacts
    lines = raw_text.split("\n")
    _log(f"  {len(lines):,} lines")

    return _run_pipeline(
        lines=lines,
        header_counts=header_counts,
        app_meta=app_meta,
        app_config_path=app_config_path,
        source_file=url,
        source_pages=0,
        output_path=output_path,
        verbose=verbose,
    )


def _run_pipeline(
    lines: list[str],
    header_counts: HeaderCounts,
    app_meta: dict[str, str],
    app_config_path: str | Path | None,
    source_file: str,
    source_pages: int,
    output_path: str | Path | None,
    verbose: bool,
) -> dict[str, Any]:
    """Shared pipeline: parse → analyze → generate."""
    _log = print if verbose else lambda *a, **k: None

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

    _log("Parsing views...")
    views = parse_views(lines, sections)
    _log(f"  {len(views)} views")

    _log("Parsing format rules...")
    format_rules = parse_format_rules(lines, sections)
    _log(f"  {len(format_rules)} format rules")

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
        header_counts, schemas, actions, slices, views, format_rules,
    )
    _log(validation.format_report())

    # Stage 4: Generate
    export = build_export(
        schemas=schemas,
        relationships=relationships,
        actions=actions,
        slices=slices,
        views=views,
        format_rules=format_rules,
        computed_fields=computed_fields,
        enum_fields=enum_fields,
        core_tables=classification.core,
        process_tables=classification.process,
        header_counts=header_counts,
        app_metadata=app_meta,
        source_file=source_file,
        source_pages=source_pages,
    )

    if output_path:
        out = write_json(export, output_path)
        _log(f"\nJSON output: {out}")

    return export
