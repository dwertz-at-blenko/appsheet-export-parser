"""Parse table schemas from AppSheet documentation text.

Uses section_finder for boundaries and field_parser for key-value
extraction. Handles page-break artifacts and split column markers.
"""

from __future__ import annotations

import re
from typing import Any

from ..extract.cleaner import clean_lines
from .field_parser import KNOWN_FIELDS, parse_type_qualifier
from .section_finder import DocumentSections


def parse_all_schemas(
    lines: list[str],
    sections: DocumentSections,
) -> dict[str, list[dict[str, Any]]]:
    """Parse all schema blocks into table → columns mapping.

    Uses schema block markers from section_finder instead of hardcoded
    line numbers. Each schema block is bounded by "Schema Name XXX_Schema"
    markers.

    Returns:
        Dict mapping table_name → list of column dicts.
    """
    schemas: dict[str, list[dict[str, Any]]] = {}

    if not sections.schema_blocks:
        return schemas

    # End of schemas section
    schemas_end = sections.schemas.end_line if sections.schemas else len(lines)

    for idx, (start_line, schema_name) in enumerate(sections.schema_blocks):
        # End is next schema start or end of schemas section
        if idx + 1 < len(sections.schema_blocks):
            end_line = sections.schema_blocks[idx + 1][0]
        else:
            end_line = schemas_end

        # Extract table name from schema name (remove _Schema suffix)
        table_name = schema_name
        if table_name.endswith("_Schema"):
            table_name = table_name[:-7]

        # Skip if already parsed (some schemas appear twice in the doc)
        if table_name in schemas:
            continue

        # Extract and clean the block
        block_lines = lines[start_line:end_line]
        block_cleaned = clean_lines(block_lines)

        columns = _parse_columns_from_block(block_cleaned)
        schemas[table_name] = columns

    return schemas


def _parse_columns_from_block(block_lines: list[str]) -> list[dict[str, Any]]:
    """Parse columns from a schema block using 'Column N: Name' delimiters.

    Handles three formats for column markers:
    1. Normal: "Column 5: ColumnName"
    2. Split across page break: "Column 5:" on one line, "ColumnName" on the next
    3. Merged with "Column name" field: look for column name after "Column name" label
    """
    columns: list[dict[str, Any]] = []

    # Find all column markers — handle split markers too
    col_starts: list[tuple[int, int, str]] = []
    i = 0
    while i < len(block_lines):
        line = block_lines[i].strip()

        # Format 1: Normal inline "Column N: Name"
        m = re.match(r"^Column (\d+): (.+)$", line)
        if m:
            col_starts.append((i, int(m.group(1)), m.group(2).strip()))
            i += 1
            continue

        # Format 2: Split — "Column N:" alone, name on next non-blank line
        m = re.match(r"^Column (\d+):$", line)
        if m:
            col_num = int(m.group(1))
            # Look ahead for the column name
            for j in range(i + 1, min(i + 3, len(block_lines))):
                next_line = block_lines[j].strip()
                if next_line and next_line not in KNOWN_FIELDS:
                    col_starts.append((i, col_num, next_line))
                    break
            i += 1
            continue

        i += 1

    for idx, (start_i, col_num, col_name) in enumerate(col_starts):
        end_i = col_starts[idx + 1][0] if idx + 1 < len(col_starts) else len(block_lines)
        col_lines = block_lines[start_i:end_i]
        col_data = _parse_single_column(col_lines, col_name)
        columns.append(col_data)

    return columns


def _parse_single_column(col_lines: list[str], col_name: str) -> dict[str, Any]:
    """Parse a single column's properties from its line block."""
    col: dict[str, Any] = {"name": col_name}

    # Build cleaned list of non-blank lines
    cleaned = [line.strip() for line in col_lines if line.strip()]

    i = 0
    while i < len(cleaned):
        field = cleaned[i]

        # Skip header lines — handle both "Column N: Name" and bare "Column N:"
        if re.match(r"^Column \d+:", field):
            i += 1
            continue
        if field == "Column name":
            # Skip field name and value (already have name from header)
            # But guard against column name being the last line
            if i + 1 < len(cleaned) and cleaned[i + 1] not in KNOWN_FIELDS:
                i += 2
            else:
                i += 1
            continue

        # Simple key-value fields
        if field == "Type" and i + 1 < len(cleaned):
            col["type"] = cleaned[i + 1]
            i += 2
        elif field == "Visible?" and i + 1 < len(cleaned):
            col["visible"] = cleaned[i + 1]
            i += 2
        elif field == "Description" and i + 1 < len(cleaned):
            val_parts: list[str] = []
            j = i + 1
            while j < len(cleaned) and cleaned[j] not in KNOWN_FIELDS:
                val_parts.append(cleaned[j])
                j += 1
            desc = " ".join(val_parts).strip()
            if desc and desc not in KNOWN_FIELDS:
                col["description"] = desc
            i = j
        elif field == "Read-Only" and i + 1 < len(cleaned):
            col["read_only"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Hidden" and i + 1 < len(cleaned):
            col["hidden"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Label" and i + 1 < len(cleaned):
            col["is_label"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Key" and i + 1 < len(cleaned):
            col["is_key"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Part of Key?" and i + 1 < len(cleaned):
            col["part_of_key"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "System Defined?" and i + 1 < len(cleaned):
            col["system_defined"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Virtual?" and i + 1 < len(cleaned):
            col["virtual"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Searchable" and i + 1 < len(cleaned):
            col["searchable"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Scannable" and i + 1 < len(cleaned):
            col["scannable"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Sensitive data" and i + 1 < len(cleaned):
            col["sensitive"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Reset on edit?" and i + 1 < len(cleaned):
            col["reset_on_edit"] = cleaned[i + 1] == "Yes"
            i += 2
        elif field == "Display name" and i + 1 < len(cleaned):
            col["display_name"] = cleaned[i + 1]
            i += 2
        elif field in ("Fixed definition?", "Formula version", "LocaleName"):
            i += 2  # skip unneeded fields
        elif field.startswith("Editable Initial Value?"):
            i += 1

        # Multi-line value fields
        elif field == "Initial value" and i + 1 < len(cleaned):
            val_parts: list[str] = []
            j = i + 1
            while j < len(cleaned) and cleaned[j] not in KNOWN_FIELDS:
                val_parts.append(cleaned[j])
                j += 1
            col["initial_value"] = " ".join(val_parts)
            i = j

        elif field == "App formula" and i + 1 < len(cleaned):
            val_parts = []
            j = i + 1
            while j < len(cleaned) and cleaned[j] not in KNOWN_FIELDS:
                val_parts.append(cleaned[j])
                j += 1
            col["app_formula"] = " ".join(val_parts)
            i = j

        elif field == "Spreadsheet formula" and i + 1 < len(cleaned):
            val_parts = []
            j = i + 1
            while j < len(cleaned) and cleaned[j] not in KNOWN_FIELDS:
                val_parts.append(cleaned[j])
                j += 1
            col["spreadsheet_formula"] = " ".join(val_parts)
            i = j

        # Type Qualifier (JSON blob, may span multiple lines)
        elif field == "Type Qualifier" and i + 1 < len(cleaned):
            json_parts: list[str] = []
            j = i + 1
            while j < len(cleaned) and cleaned[j] not in KNOWN_FIELDS:
                json_parts.append(cleaned[j])
                j += 1

            tq = parse_type_qualifier(json_parts)
            if tq:
                if tq.get("ReferencedTableName"):
                    col["referenced_table"] = tq["ReferencedTableName"]
                if tq.get("ReferencedType"):
                    col["referenced_type"] = tq["ReferencedType"]
                if tq.get("Valid_If"):
                    col["valid_if"] = tq["Valid_If"]
                if tq.get("Show_If"):
                    col["show_if"] = tq["Show_If"]
                if tq.get("Required_If"):
                    col["required_if"] = tq["Required_If"]
                if tq.get("Editable_If"):
                    col["editable_if"] = tq["Editable_If"]
                if tq.get("EnumValues"):
                    col["enum_values"] = tq["EnumValues"]
                if tq.get("Items"):
                    col["items"] = tq["Items"]
                for key in ("MaxValue", "MinValue", "MaxLength", "MinLength"):
                    if tq.get(key) is not None:
                        col[key.lower()] = tq[key]

                # P1: If Type Qualifier has ReferencedTableName, override type to "Ref"
                # This catches columns where the raw PDF type says "Number" but
                # the column actually stores a foreign key reference (e.g. department_id)
                if col.get("referenced_table") and col.get("type") != "Ref":
                    col["_original_type"] = col["type"]
                    col["type"] = "Ref"

            i = j

        # Condition (inline format)
        elif field.startswith("Only if this condition is true"):
            cond = field.replace("Only if this condition is true", "").strip()
            if cond:
                col["condition"] = cond
            i += 1

        else:
            i += 1

    return col
