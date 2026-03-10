"""Canonical versioned JSON output from parsed AppSheet data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models.app import SCHEMA_VERSION, AppExport, AppMetadata, AppSummary, OfficialCounts
from ..extract.header import HeaderCounts


def build_export(
    schemas: dict[str, list[dict[str, Any]]],
    relationships: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    slices: list[dict[str, Any]],
    views: list[dict[str, Any]] | None = None,
    format_rules: list[dict[str, Any]] | None = None,
    computed_fields: list[dict[str, Any]] | None = None,
    enum_fields: list[dict[str, Any]] | None = None,
    core_tables: list[str] | None = None,
    process_tables: list[str] | None = None,
    header_counts: HeaderCounts | None = None,
    app_metadata: dict[str, str] | None = None,
    source_file: str = "",
    source_pages: int = 0,
) -> dict[str, Any]:
    """Build the canonical export dict from parsed components.

    Returns a plain dict suitable for JSON serialization.
    Uses Pydantic models internally for validation, then dumps to dict.
    """
    meta = app_metadata or {}
    views = views or []
    format_rules = format_rules or []
    computed_fields = computed_fields or []
    enum_fields = enum_fields or []
    core_tables = core_tables or []
    process_tables = process_tables or []

    summary = AppSummary(
        total_tables=len(schemas),
        core_tables=len(core_tables),
        process_tables=len(process_tables),
        total_columns=sum(len(cols) for cols in schemas.values()),
        total_actions=len(actions),
        total_slices=len(slices),
        total_relationships=len(relationships),
        total_computed_fields=len(computed_fields),
        total_enum_fields=len(enum_fields),
    )

    official = None
    if header_counts and header_counts.has_data:
        official = OfficialCounts(
            tables=header_counts.tables,
            columns=header_counts.columns,
            slices=header_counts.slices,
            actions=header_counts.actions,
            views=header_counts.views,
            format_rules=header_counts.format_rules,
            workflow_rules=header_counts.workflow_rules,
        )

    sections = ["schemas", "relationships", "computed_fields", "enum_fields"]
    if actions:
        sections.append("actions")
    if slices:
        sections.append("slices")
    if views:
        sections.append("views")
    if format_rules:
        sections.append("format_rules")

    metadata = AppMetadata(
        app_name=meta.get("app_name", ""),
        version=meta.get("version", ""),
        stable_version=meta.get("stable_version", ""),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        parser_version=SCHEMA_VERSION,
        source_file=source_file,
        source_pages=source_pages,
        summary=summary,
        official_counts=official,
        sections_captured=sections,
    )

    export = {
        "schema_version": SCHEMA_VERSION,
        "metadata": metadata.model_dump(mode="json", exclude_none=True),
        "core_table_names": core_tables,
        "process_table_names": process_tables,
        "schemas": {
            table: [
                {k: v for k, v in col.items() if not k.startswith("_")}
                for col in cols
            ]
            for table, cols in schemas.items()
        },
        "relationships": relationships,
        "computed_fields": computed_fields,
        "enum_fields": enum_fields,
        "actions": actions,
        "slices": slices,
        "views": views,
        "format_rules": format_rules,
    }

    return export


def write_json(export: dict[str, Any], output_path: str | Path) -> Path:
    """Write export dict to a JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(export, f, indent=2, default=str)

    return output_path
