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
    process_tables: list[str] | None = None,
) -> ValidationReport:
    """Compare parsed extraction counts against official header counts.

    Args:
        header: Official counts from the document header.
        schemas: Parsed schemas (table_name → columns).
        actions: Parsed actions list.
        slices: Parsed slices list.
        process_tables: Optional list of process table names (explains
            the difference between header table count and parsed count).
    """
    report = ValidationReport()

    if not header.has_data:
        return report  # No header to validate against

    # Tables
    parsed_tables = len(schemas)
    process_count = len(process_tables) if process_tables else 0
    if parsed_tables == header.tables:
        report.results.append(ValidationResult(
            "Tables", header.tables, parsed_tables, "match",
        ))
    elif process_count > 0 and parsed_tables + process_count >= header.tables:
        report.results.append(ValidationResult(
            "Tables", header.tables, parsed_tables, "expected_diff",
            f"{header.tables - parsed_tables} are Process/Output tables",
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
        note = f"Delta: {diff}"
        if diff > 0 and diff > 30:
            note += " (cross-table duplicates may need dedup)"
        report.results.append(ValidationResult(
            "Actions", header.actions, parsed_actions, "warning", note,
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

    return report
