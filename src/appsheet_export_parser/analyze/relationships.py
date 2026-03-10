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
                inferred = _infer_ref_target(
                    col.get("name", ""), all_tables, source_table=table,
                )
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


def _infer_ref_target(
    column_name: str,
    all_tables: set[str],
    source_table: str = "",
) -> str | None:
    """Infer the target table from a Ref column's name.

    AppSheet naming conventions:
    - Column "Employee" → Table "Employee"
    - Column "Related Work_Cards" → Table "Work_Card"
    - Column "Shop_ID" → Table "Shops" (strip _ID suffix)
    - Column "Shop" → Table "Shops"

    Tries exact match, suffix stripping, singular/plural, then partial match.
    """
    candidates = _generate_candidates(column_name)

    for candidate in candidates:
        # Direct match
        if candidate in all_tables and candidate != source_table:
            return candidate

        # Underscore/space normalization
        for variant in (candidate.replace(" ", "_"), candidate.replace("_", " ")):
            if variant in all_tables and variant != source_table:
                return variant

        # Singular/plural
        if candidate.endswith("s") and candidate[:-1] in all_tables:
            t = candidate[:-1]
            if t != source_table:
                return t
        plus_s = candidate + "s"
        if plus_s in all_tables and plus_s != source_table:
            return plus_s

    # Case-insensitive match
    lower_map = {t.lower(): t for t in all_tables}
    for candidate in candidates:
        low = candidate.lower()
        if low in lower_map and lower_map[low] != source_table:
            return lower_map[low]
        # Normalized variants
        for variant in (low.replace(" ", "_"), low.replace("_", " ")):
            if variant in lower_map and lower_map[variant] != source_table:
                return lower_map[variant]

    # Partial match — candidate contained in table name or vice versa
    # Require minimum 3 chars to avoid false matches
    # When multiple tables match, prefer exact prefix match over substring
    for candidate in candidates:
        if len(candidate) < 3:
            continue
        matches = []
        for table in sorted(all_tables):
            if table == source_table:
                continue
            if candidate.lower() in table.lower() or table.lower() in candidate.lower():
                matches.append(table)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # Disambiguate: prefer table whose name starts with the candidate
            prefix_matches = [t for t in matches if t.lower().startswith(candidate.lower())
                             or t.lower().replace("_", " ").startswith(candidate.lower().replace("_", " "))]
            if len(prefix_matches) == 1:
                return prefix_matches[0]
            # Further disambiguate: prefer table with matching PK convention
            # e.g., column "Batch ID" → table with PK "batch_id"
            pk_matches = [t for t in matches
                         if f"{candidate.lower().replace(' ', '_')}_id" == t.lower().replace(" ", "_").rstrip("s") + "_id"
                         or f"{candidate.lower().replace(' ', '_')}" == t.lower().replace(" ", "_").rstrip("s")]
            if pk_matches:
                return pk_matches[0]
            # Default: return shortest match (most specific)
            return min(matches, key=len)

    return None


def _generate_candidates(column_name: str) -> list[str]:
    """Generate candidate table names from a column name."""
    candidates = [column_name]

    # Strip common prefixes
    for prefix in ("Related ", "Ref ", "FK_", "fk_"):
        if column_name.startswith(prefix):
            stripped = column_name[len(prefix):]
            candidates.append(stripped)
            column_name = stripped
            break

    # Strip _ID / _Id / ID suffix (common AppSheet convention)
    for suffix in ("_ID", "_Id", "_id", " ID", " Id"):
        if column_name.endswith(suffix):
            base = column_name[: -len(suffix)]
            if base:
                candidates.append(base)

    # Strip "Batch_ID" → try just the prefix part
    m = re.match(r"^(.+?)_\d*(?:ID|Id)$", column_name)
    if m:
        candidates.append(m.group(1))

    return candidates
