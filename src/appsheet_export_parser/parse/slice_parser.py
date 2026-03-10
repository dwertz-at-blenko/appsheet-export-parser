"""Parse slices from AppSheet documentation text.

Refactored from parse_berp_v2.py — uses section_finder boundaries
instead of hardcoded `i > 200000`.
"""

from __future__ import annotations

import re
from typing import Any

from ..extract.cleaner import clean_lines
from .section_finder import DocumentSections


def parse_slices(
    lines: list[str],
    sections: DocumentSections,
) -> list[dict[str, Any]]:
    """Parse all slices from the Slices section."""
    slices: list[dict[str, Any]] = []

    if not sections.slices:
        return slices

    start = sections.slices.start_line
    end = sections.slices.end_line

    block = lines[start:end]
    cleaned = clean_lines(block)
    clean = [line.strip() for line in cleaned if line.strip()]

    current_slice: dict[str, Any] | None = None
    i = 0

    while i < len(clean):
        field = clean[i]

        # Detect slice start
        m = re.match(r"^Slice Name (.+)$", field)
        if m or field == "Slice Name":
            if current_slice and current_slice.get("name"):
                slices.append(current_slice)
            current_slice = {}
            if m:
                current_slice["name"] = m.group(1).strip()
            elif i + 1 < len(clean):
                i += 1
                current_slice["name"] = clean[i]
            i += 1
            continue

        if current_slice is not None:
            if field == "Source Table" and i + 1 < len(clean):
                current_slice["source_table"] = clean[i + 1]
                i += 2
            elif field == "Row Filter Condition" and i + 1 < len(clean):
                val_parts: list[str] = []
                j = i + 1
                while (
                    j < len(clean)
                    and not clean[j].startswith("Slice ")
                    and clean[j] != "Source Table"
                ):
                    val_parts.append(clean[j])
                    j += 1
                current_slice["filter"] = " ".join(val_parts)
                i = j
            elif field == "Slice Columns" and i + 1 < len(clean):
                val_parts = []
                j = i + 1
                while (
                    j < len(clean)
                    and not clean[j].startswith("Slice ")
                    and clean[j] not in ("Source Table", "Row Filter Condition")
                ):
                    val_parts.append(clean[j])
                    j += 1
                current_slice["columns"] = " ".join(val_parts)
                i = j
            else:
                i += 1
        else:
            i += 1

    if current_slice and current_slice.get("name"):
        slices.append(current_slice)

    # Deduplicate: AppSheet docs repeat slice headers. Keep the version
    # with the most data (has source_table, filter, etc.)
    deduped: dict[str, dict[str, Any]] = {}
    for s in slices:
        name = s.get("name", "")
        if not name:
            continue
        existing = deduped.get(name)
        if existing is None:
            deduped[name] = s
        else:
            # Keep whichever has more fields populated
            if len(s) > len(existing):
                deduped[name] = s
            elif len(s) == len(existing) and s.get("source_table") and not existing.get("source_table"):
                deduped[name] = s

    return list(deduped.values())
