"""Parse views from the UX section of AppSheet documentation.

Views appear in the UX section with this structure:
    View name	<name>
    View type	<type>
    Position	<position>
    For this data	<table>
    View configuration	<json>

In cleaned text (blank lines removed), fields alternate: label, value.
Tab-delimited in URL source, line-separated in PDF source.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..extract.cleaner import clean_lines
from .section_finder import DocumentSections


# Fields that start a new view or act as boundaries
_VIEW_FIELDS = frozenset({
    "View name",
    "View type",
    "Position",
    "For this data",
    "View configuration",
    "Column order",
    "Sort by",
    "Group by",
    "Group aggregate",
    "Is this view disabled?",
    "Is this view visible?",
    "Format Rules",
})


def parse_views(
    lines: list[str],
    sections: DocumentSections,
) -> list[dict[str, Any]]:
    """Parse all views from the UX section.

    Scans for "View name" markers within the UX section and extracts
    name, type, position, table, and configuration for each view.
    """
    views: list[dict[str, Any]] = []

    if not sections.ux:
        return views

    start = sections.ux.start_line
    end = sections.ux.end_line

    # Find the views region — it's between the UX header and "Format Rules" header
    # (or end of UX section if no format rules)
    block = lines[start:end]
    cleaned = clean_lines(block)
    clean = [line.strip() for line in cleaned if line.strip()]

    # Find all "View name" markers
    view_starts: list[tuple[int, str]] = []
    i = 0
    while i < len(clean):
        line = clean[i]

        # Tab-delimited format: "View name\tSomeName"
        if line.startswith("View name\t"):
            name = line.split("\t", 1)[1].strip()
            view_starts.append((i, name))
            i += 1
            continue

        # Line-separated format: "View name" on one line, name on next
        if line == "View name" and i + 1 < len(clean):
            name = clean[i + 1]
            if name not in _VIEW_FIELDS and name != "Format Rules":
                view_starts.append((i, name))
            i += 1
            continue

        # Stop at Format Rules section
        if line == "Format Rules":
            break

        i += 1

    # Parse each view block
    for idx, (start_i, name) in enumerate(view_starts):
        if idx + 1 < len(view_starts):
            end_i = view_starts[idx + 1][0]
        else:
            # Find end — either "Format Rules" or end of cleaned list
            end_i = len(clean)
            for j in range(start_i + 1, len(clean)):
                if clean[j] == "Format Rules":
                    end_i = j
                    break

        view_lines = clean[start_i:end_i]
        view = _parse_single_view(view_lines, name)
        views.append(view)

    return views


def _parse_single_view(
    cleaned_lines: list[str],
    view_name: str,
) -> dict[str, Any]:
    """Parse a single view block."""
    view: dict[str, Any] = {"name": view_name}

    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]

        # Handle tab-delimited fields
        if "\t" in line:
            parts = line.split("\t", 1)
            key = parts[0].strip()
            val = parts[1].strip() if len(parts) > 1 else ""
            _assign_view_field(view, key, val)
            i += 1
            continue

        # Handle line-separated fields
        if line == "View name":
            i += 2  # skip name (already captured)
            continue
        if line == "View type" and i + 1 < len(cleaned_lines):
            view["type"] = cleaned_lines[i + 1]
            i += 2
        elif line == "Position" and i + 1 < len(cleaned_lines):
            view["position"] = cleaned_lines[i + 1]
            i += 2
        elif line == "For this data" and i + 1 < len(cleaned_lines):
            view["table"] = cleaned_lines[i + 1]
            i += 2
        elif line == "View configuration" and i + 1 < len(cleaned_lines):
            # Collect JSON which may span multiple lines
            json_parts: list[str] = []
            j = i + 1
            while j < len(cleaned_lines) and cleaned_lines[j] not in _VIEW_FIELDS:
                json_parts.append(cleaned_lines[j])
                j += 1
            raw = " ".join(json_parts)
            try:
                view["config"] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                view["config_raw"] = raw
            i = j
        elif line == "Column order" and i + 1 < len(cleaned_lines):
            view["column_order"] = cleaned_lines[i + 1]
            i += 2
        elif line == "Sort by" and i + 1 < len(cleaned_lines):
            view["sort_by"] = cleaned_lines[i + 1]
            i += 2
        elif line == "Group by" and i + 1 < len(cleaned_lines):
            view["group_by"] = cleaned_lines[i + 1]
            i += 2
        elif line == "Group aggregate" and i + 1 < len(cleaned_lines):
            view["group_aggregate"] = cleaned_lines[i + 1]
            i += 2
        else:
            i += 1

    return view


def _assign_view_field(view: dict[str, Any], key: str, val: str) -> None:
    """Assign a tab-delimited field to the view dict."""
    mapping = {
        "View name": "name",
        "View type": "type",
        "Position": "position",
        "For this data": "table",
        "Column order": "column_order",
        "Sort by": "sort_by",
        "Group by": "group_by",
        "Group aggregate": "group_aggregate",
    }
    if key in mapping:
        view[mapping[key]] = val
    elif key == "View configuration":
        try:
            view["config"] = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            view["config_raw"] = val
