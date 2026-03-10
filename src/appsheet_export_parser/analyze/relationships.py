"""Extract and analyze Ref relationships between tables.

Handles both clean Ref columns (with explicit ReferencedTableName)
and broken references where the target table needs inference.
"""

from __future__ import annotations

import re
from typing import Any

from ..models.analysis import Relationship


def extract_relationships(
    schemas: dict[str, list[dict[str, Any]]],
) -> list[Relationship]:
    """Extract Ref relationships from parsed schemas.

    For each column with type "Ref" and a referenced_table, creates a
    Relationship record.
    """
    rels: list[Relationship] = []
    all_tables = set(schemas.keys())

    for table, cols in schemas.items():
        for col in cols:
            if col.get("type") != "Ref":
                continue

            target = col.get("referenced_table")

            # If target is missing or broken, try inference
            if not target or target not in all_tables:
                inferred = _infer_ref_target(col.get("name", ""), all_tables)
                if inferred:
                    target = inferred

            if target:
                rels.append(Relationship(
                    from_table=table,
                    from_column=col["name"],
                    to_table=target,
                    referenced_type=col.get("referenced_type"),
                ))

    return rels


def _infer_ref_target(column_name: str, all_tables: set[str]) -> str | None:
    """Infer the target table from a Ref column's name.

    AppSheet naming conventions:
    - Column "Employee" → Table "Employee"
    - Column "Related Work_Cards" → Table "Work_Card"
    - Column "Shop" → Table "Shops"

    Tries exact match, then singular/plural variants, then partial match.
    """
    # Direct match
    if column_name in all_tables:
        return column_name

    # Strip common prefixes
    stripped = column_name
    for prefix in ("Related ", "Ref ", "FK_", "fk_"):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]

    if stripped in all_tables:
        return stripped

    # Try singular/plural
    if stripped.endswith("s") and stripped[:-1] in all_tables:
        return stripped[:-1]
    if stripped + "s" in all_tables:
        return stripped + "s"

    # Underscore/space normalization
    normalized = stripped.replace(" ", "_")
    if normalized in all_tables:
        return normalized
    normalized = stripped.replace("_", " ")
    if normalized in all_tables:
        return normalized

    # Partial match (column name contained in table name or vice versa)
    for table in all_tables:
        if stripped.lower() in table.lower() or table.lower() in stripped.lower():
            return table

    return None
