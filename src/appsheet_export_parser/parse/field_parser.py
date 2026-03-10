"""Shared key-value field extraction from cleaned text lines.

AppSheet documentation uses a consistent format for field data:
    FieldName
    (blank line)
    Value
    (blank line)
    NextFieldName
    ...

After cleaning (blank lines removed), this becomes:
    FieldName, Value, FieldName, Value, ...

Some values span multiple lines (e.g., Type Qualifier JSON, formulas).
The parser uses KNOWN_FIELDS to detect where values end and new fields begin.
"""

from __future__ import annotations

import json
from typing import Any

# Known field names that appear in AppSheet column definitions.
# Used as boundary markers when parsing multi-line values.
KNOWN_FIELDS = frozenset({
    "Column name",
    "Visible?",
    "Type",
    "Type Qualifier",
    "Description",
    "Read-Only",
    "Hidden",
    "Label",
    "Formula version",
    "Reset on edit?",
    "Initial value",
    "System Defined?",
    "Key",
    "Part of Key?",
    "Fixed definition?",
    "Virtual?",
    "LocaleName",
    "Searchable",
    "Scannable",
    "Sensitive data",
    "App formula",
    "Spreadsheet formula",
    "Display name",
    "Editable Initial Value? Yes",
    "Editable Initial Value? No",
})

# Known field names for action blocks
ACTION_FIELDS = frozenset({
    "Action name",
    "Bulk action?",
    "Modifies data?",
    "Needs confirmation?",
    "Prominence",
    "Action order",
    "With these properties",
    "Do this",
    "Attach to column",
    "For a record of this table",
    "Does this action apply to",
    "the whole table?",
    "To this value",
    "Visible?",
    "Set these columns",
    "Confirmation message",
    "Action icon",
    "Disable automatic updates?",
})


def extract_multiline_value(
    cleaned_lines: list[str],
    start_index: int,
    boundary_fields: frozenset[str],
) -> tuple[str, int]:
    """Extract a multi-line value starting at start_index.

    Collects lines until hitting a known field name boundary.

    Returns:
        (value_string, next_index) where next_index is the position
        of the boundary field (or end of list).
    """
    parts: list[str] = []
    j = start_index
    while j < len(cleaned_lines):
        if cleaned_lines[j] in boundary_fields:
            break
        parts.append(cleaned_lines[j])
        j += 1
    return " ".join(parts), j


def parse_type_qualifier(raw_parts: list[str]) -> dict[str, Any] | None:
    """Parse a Type Qualifier JSON blob from collected line parts.

    The JSON may be broken across PDF page boundaries.
    Attempts parsing as-is first, then tries basic JSON repair.

    Returns parsed dict or None if parsing fails.
    """
    tq_str = "".join(raw_parts)
    try:
        return json.loads(tq_str)
    except (json.JSONDecodeError, TypeError):
        # Try repair
        from .json_repair import repair_json
        repaired = repair_json(tq_str)
        try:
            return json.loads(repaired)
        except (json.JSONDecodeError, TypeError):
            return None


def parse_bool_field(value: str) -> bool:
    """Parse a Yes/No field value to boolean."""
    return value.strip().lower() in ("yes", "true", "1")
