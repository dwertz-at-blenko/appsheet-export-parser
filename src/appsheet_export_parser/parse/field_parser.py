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
import re
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
    Tries multiple join strategies (space-join preserves string values,
    no-space join preserves keywords), then repair, then regex fallback.

    Returns parsed dict or None if parsing fails completely.
    """
    space_joined = " ".join(raw_parts)    # Preserves string value spaces
    nospace_joined = "".join(raw_parts)   # Preserves keyword integrity

    # Attempt 1: space-join (best for string values with page-break splits)
    try:
        return json.loads(space_joined)
    except (json.JSONDecodeError, TypeError):
        pass

    # Attempt 2: repair space-joined (fixes split keywords while preserving
    # string value spaces — must come before raw no-space join)
    from .json_repair import repair_json, extract_ref_table_from_broken_json
    repaired = repair_json(space_joined)
    try:
        return json.loads(repaired)
    except (json.JSONDecodeError, TypeError):
        pass

    # Attempt 3: no-space join (fallback for structural breaks)
    try:
        return json.loads(nospace_joined)
    except (json.JSONDecodeError, TypeError):
        pass

    # Attempt 4: repair no-space version
    repaired2 = repair_json(nospace_joined)
    try:
        return json.loads(repaired2)
    except (json.JSONDecodeError, TypeError):
        # Last resort: regex extraction
        result: dict[str, Any] = {}
        ref_table = extract_ref_table_from_broken_json(raw_parts)
        if ref_table:
            result["ReferencedTableName"] = ref_table
        raw = "".join(raw_parts)
        for key in ("ReferencedType", "Valid_If", "Show_If", "Required_If", "Editable_If"):
            m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', raw)
            if m:
                result[key] = m.group(1)
        # Extract EnumValues array — try multiple patterns for malformed JSON
        m = re.search(r'"EnumValues"\s*:\s*\[([^\]]*)\]', raw)
        if not m:
            # Fallback: unquoted key or broken brackets
            m = re.search(r'EnumValues\s*:?\s*\[([^\]]*)\]', raw)
        if m:
            try:
                vals = json.loads(f"[{m.group(1)}]")
                result["EnumValues"] = vals
            except (json.JSONDecodeError, TypeError):
                # Last resort: split by comma, strip quotes
                raw_vals = m.group(1).strip()
                if raw_vals:
                    vals = [v.strip().strip('"').strip("'") for v in raw_vals.split(",") if v.strip()]
                    if vals:
                        result["EnumValues"] = vals
        return result if result else None


def parse_bool_field(value: str) -> bool:
    """Parse a Yes/No field value to boolean."""
    return value.strip().lower() in ("yes", "true", "1")
