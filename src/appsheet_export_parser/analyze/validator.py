"""Validate parser output against official header counts.

This is the single most important quality gate. If the parser's output
doesn't match the header counts, something is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..extract.header import HeaderCounts


@dataclass
class ValidationResult:
    """Result of comparing parsed counts against official header counts."""

    field: str
    expected: int
    actual: int
    status: str  # "match", "expected_diff", "warning", "error"
    note: str = ""

    @property
    def matches(self) -> bool:
        return self.status in ("match", "expected_diff")


@dataclass
class ValidationReport:
    """Full validation report comparing parsed output against header."""

    results: list[ValidationResult] = field(default_factory=list)

    @property
    def all_pass(self) -> bool:
        return all(r.matches for r in self.results)

    @property
    def errors(self) -> list[ValidationResult]:
        return [r for r in self.results if r.status == "error"]

    @property
    def warnings(self) -> list[ValidationResult]:
        return [r for r in self.results if r.status == "warning"]

    def format_report(self) -> str:
        """Format validation report as human-readable text."""
        lines: list[str] = []
        for r in self.results:
            icon = {
                "match": "OK",
                "expected_diff": "OK",
                "warning": "WARN",
                "error": "ERR",
            }.get(r.status, "??")

            line = f"  [{icon}] {r.field}: {r.actual}/{r.expected}"
            if r.note:
                line += f" -- {r.note}"
            lines.append(line)
        return "\n".join(lines)


def validate_counts(
    header: HeaderCounts,
    schemas: dict[str, list[dict[str, Any]]],
    actions: list[dict[str, Any]],
    slices: list[dict[str, Any]],
    views: list[dict[str, Any]] | None = None,
    format_rules: list[dict[str, Any]] | None = None,
) -> ValidationReport:
    """Compare parsed extraction counts against official header counts.

    Args:
        header: Official counts from the document header.
        schemas: Parsed schemas (table_name → columns).
        actions: Parsed actions list.
        slices: Parsed slices list.
        views: Parsed views list.
        format_rules: Parsed format rules list.
    """
    report = ValidationReport()
    views = views or []
    format_rules = format_rules or []

    if not header.has_data:
        return report  # No header to validate against

    # Tables
    parsed_tables = len(schemas)
    if parsed_tables == header.tables:
        report.results.append(ValidationResult(
            "Tables", header.tables, parsed_tables, "match",
        ))
    else:
        diff = header.tables - parsed_tables
        status = "warning" if abs(diff) <= 5 else "error"
        report.results.append(ValidationResult(
            "Tables", header.tables, parsed_tables, status,
            f"Missing {diff}" if diff > 0 else f"Extra {abs(diff)}",
        ))

    # Columns
    parsed_cols = sum(len(cols) for cols in schemas.values())
    if parsed_cols == header.columns:
        report.results.append(ValidationResult(
            "Columns", header.columns, parsed_cols, "match",
            "EXACT MATCH",
        ))
    else:
        diff = header.columns - parsed_cols
        status = "warning" if abs(diff) / max(header.columns, 1) < 0.05 else "error"
        report.results.append(ValidationResult(
            "Columns", header.columns, parsed_cols, status,
            f"Delta: {diff}",
        ))

    # Actions
    parsed_actions = len(actions)
    if parsed_actions == header.actions:
        report.results.append(ValidationResult(
            "Actions", header.actions, parsed_actions, "match",
        ))
    else:
        diff = header.actions - parsed_actions
        status = "warning" if abs(diff) / max(header.actions, 1) < 0.1 else "error"
        report.results.append(ValidationResult(
            "Actions", header.actions, parsed_actions, status,
            f"Delta: {diff}",
        ))

    # Slices
    parsed_slices = len(slices)
    if parsed_slices == header.slices:
        report.results.append(ValidationResult(
            "Slices", header.slices, parsed_slices, "match",
        ))
    else:
        diff = header.slices - parsed_slices
        report.results.append(ValidationResult(
            "Slices", header.slices, parsed_slices, "warning",
            f"Delta: {diff}",
        ))

    # Views
    if header.views > 0:
        parsed_views = len(views)
        if parsed_views == header.views:
            report.results.append(ValidationResult(
                "Views", header.views, parsed_views, "match",
            ))
        else:
            diff = header.views - parsed_views
            status = "warning" if abs(diff) / max(header.views, 1) < 0.1 else "error"
            report.results.append(ValidationResult(
                "Views", header.views, parsed_views, status,
                f"Delta: {diff}",
            ))

    # Format Rules
    if header.format_rules > 0:
        parsed_fr = len(format_rules)
        if parsed_fr == header.format_rules:
            report.results.append(ValidationResult(
                "Format Rules", header.format_rules, parsed_fr, "match",
            ))
        else:
            diff = header.format_rules - parsed_fr
            report.results.append(ValidationResult(
                "Format Rules", header.format_rules, parsed_fr, "warning",
                f"Delta: {diff}",
            ))

    return report


def validate_per_table_columns(
    schemas: dict[str, list[dict[str, Any]]],
    official_column_counts: dict[str, int] | None = None,
) -> list[ValidationResult]:
    """Validate per-table column counts against official counts.

    If official_column_counts is provided (table_name → expected_count),
    compare each table's parsed column count against the expected count
    and return warnings for discrepancies.
    """
    results: list[ValidationResult] = []
    if not official_column_counts:
        return results

    for table_name, expected in official_column_counts.items():
        actual = len(schemas.get(table_name, []))
        if actual == 0 and table_name not in schemas:
            results.append(ValidationResult(
                f"Table:{table_name}", expected, 0, "warning",
                "Table not found in parsed output",
            ))
        elif actual != expected:
            results.append(ValidationResult(
                f"Table:{table_name}", expected, actual, "warning",
                f"Parsed {actual}/{expected} columns — {expected - actual} missing",
            ))

    return results


def generate_delta_report(
    schemas: dict[str, list[dict[str, Any]]],
    official_column_counts: dict[str, int] | None = None,
) -> str:
    """Generate a delta report showing which tables are short on columns.

    Returns a human-readable string showing per-table deltas.
    """
    if not official_column_counts:
        return "No official per-table counts available for comparison."

    lines: list[str] = ["Per-table column delta report:"]
    total_missing = 0
    total_extra = 0

    for table_name in sorted(official_column_counts.keys()):
        expected = official_column_counts[table_name]
        actual = len(schemas.get(table_name, []))
        diff = expected - actual

        if diff == 0:
            continue

        if diff > 0:
            total_missing += diff
            lines.append(f"  {table_name}: {actual}/{expected} (-{diff} missing)")
        else:
            total_extra += abs(diff)
            lines.append(f"  {table_name}: {actual}/{expected} (+{abs(diff)} extra)")

    if total_missing == 0 and total_extra == 0:
        lines.append("  All tables match expected column counts.")
    else:
        lines.append(f"  Total: {total_missing} missing, {total_extra} extra")

    return "\n".join(lines)
