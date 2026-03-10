"""Extract official summary counts from the AppSheet documentation header.

AppSheet documentation exports contain a summary header in two possible formats:

Multi-line (PDF extraction):
    Data Summary
    53 Tables
    2151 Columns
    32 Slices

Single-line (URL/live page):
    Data Summary: 55 Tables, 3044 Columns, 36 Slices

These counts serve as the parser's self-validation target.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class HeaderCounts:
    """Official counts from the AppSheet documentation header."""

    tables: int = 0
    columns: int = 0
    slices: int = 0
    views: int = 0
    format_rules: int = 0
    actions: int = 0
    workflow_rules: int = 0

    @property
    def has_data(self) -> bool:
        return self.tables > 0 or self.columns > 0


def extract_header_counts(text: str) -> HeaderCounts:
    """Extract official summary counts from the doc header.

    Searches the first ~500 lines for summary counts.
    Handles both single-line and multi-line formats.
    """
    counts = HeaderCounts()
    header_lines = text.split("\n")[:500]
    header_text = "\n".join(header_lines)

    # Try single-line format first (URL/live page)
    m = re.search(
        r"Data Summary:\s*(\d+)\s*Tables?,\s*(\d+)\s*Columns?,\s*(\d+)\s*Slices?",
        header_text,
    )
    if m:
        counts.tables = int(m.group(1))
        counts.columns = int(m.group(2))
        counts.slices = int(m.group(3))
    else:
        # Multi-line format (PDF extraction)
        _parse_multiline_summary(header_lines, counts)

    # UX Summary — single-line
    m = re.search(
        r"UX Summary:\s*(\d+)\s*Views?,\s*(\d+)\s*Format Rules?",
        header_text,
    )
    if m:
        counts.views = int(m.group(1))
        counts.format_rules = int(m.group(2))

    # Behavior Summary — single-line
    m = re.search(
        r"Behavior Summary:\s*(\d+)\s*Actions?,\s*(\d+)\s*Workflow Rules?",
        header_text,
    )
    if m:
        counts.actions = int(m.group(1))
        counts.workflow_rules = int(m.group(2))

    # If single-line didn't work for UX/Behavior, try multi-line
    if counts.views == 0 and counts.actions == 0:
        _parse_multiline_summary(header_lines, counts)

    return counts


def _parse_multiline_summary(lines: list[str], counts: HeaderCounts) -> None:
    """Parse multi-line summary format from PDF extraction.

    Looks for patterns like:
        Data Summary
        (blank)
        53 Tables
        2151 Columns
        32 Slices
    """
    for i, line in enumerate(lines):
        s = line.strip()

        # "N Tables", "N Columns", etc.
        m = re.match(r"^(\d+)\s+Tables?$", s)
        if m and counts.tables == 0:
            counts.tables = int(m.group(1))
            continue

        m = re.match(r"^(\d+)\s+Columns?$", s)
        if m and counts.columns == 0:
            counts.columns = int(m.group(1))
            continue

        m = re.match(r"^(\d+)\s+Slices?$", s)
        if m and counts.slices == 0:
            counts.slices = int(m.group(1))
            continue

        m = re.match(r"^(\d+)\s+Views?$", s)
        if m and counts.views == 0:
            counts.views = int(m.group(1))
            continue

        m = re.match(r"^(\d+)\s+Format Rules?$", s)
        if m and counts.format_rules == 0:
            counts.format_rules = int(m.group(1))
            continue

        m = re.match(r"^(\d+)\s+Actions?$", s)
        if m and counts.actions == 0:
            counts.actions = int(m.group(1))
            continue

        m = re.match(r"^(\d+)\s+Workflow Rules?$", s)
        if m and counts.workflow_rules == 0:
            counts.workflow_rules = int(m.group(1))
            continue


def extract_app_metadata(text: str) -> dict[str, str]:
    """Extract app name, version, and other metadata from the doc header.

    Handles the multi-line key/value format from PDF extraction:
        Short Name
        (blank)
        My App v2.0
    """
    metadata: dict[str, str] = {}
    lines = text.split("\n")[:200]

    for i, line in enumerate(lines):
        s = line.strip()

        if s == "Short Name":
            # Look ahead for value (skip blank lines)
            for j in range(i + 1, min(i + 4, len(lines))):
                val = lines[j].strip()
                if val and val not in ("Version", "Stable Version", "Short Description"):
                    metadata["app_name"] = val
                    break

        elif s == "Version" and "app_name" in metadata:
            # Only match Version after we've found the app name (to avoid false matches)
            for j in range(i + 1, min(i + 4, len(lines))):
                val = lines[j].strip()
                if val and re.match(r"^[\d.]+$", val):
                    metadata["version"] = val
                    break

        elif s == "Stable Version":
            for j in range(i + 1, min(i + 4, len(lines))):
                val = lines[j].strip()
                if val and re.match(r"^[\d.]+$", val):
                    metadata["stable_version"] = val
                    break

    return metadata
