"""Clean extracted PDF text — remove page headers, footers, form feeds."""

from __future__ import annotations

import re


def clean_text(text: str, page_count: int | None = None) -> str:
    """Remove page noise from pdftotext output.

    Strips:
    - Form feed characters and associated date headers
    - Page number patterns (e.g., "42/2718")
    - Date/time headers from page breaks
    - "Application Documentation" header lines
    - AppSheet URLs from page headers

    Args:
        text: Raw pdftotext output.
        page_count: Total page count for matching "N/TOTAL" patterns.
            If None, auto-detects from the text.
    """
    lines = text.split("\n")
    return "\n".join(clean_lines(lines, page_count))


def clean_lines(raw_lines: list[str], page_count: int | None = None) -> list[str]:
    """Remove page noise from a list of lines.

    Auto-detects page count if not provided, building a regex pattern
    that matches "N/TOTAL" where TOTAL is the actual page count.
    """
    # Auto-detect page count if needed
    if page_count is None:
        for line in raw_lines[:1000]:
            m = re.match(r"^\s*\d+/(\d+)\s*$", line.strip())
            if m:
                page_count = int(m.group(1))
                break

    # Build page number pattern
    if page_count:
        page_pattern = re.compile(rf"^\d+/{page_count}$")
    else:
        # Fallback: match any "N/M" where M > 10
        page_pattern = re.compile(r"^\d+/\d{2,}$")

    date_pattern = re.compile(r"^\d+/\d+/\d+,\s+\d+:\d+\s+(AM|PM)$")

    cleaned: list[str] = []
    for line in raw_lines:
        s = line.strip()

        # Skip form feed + date header
        if s.startswith("\x0c"):
            continue

        # Skip page numbers
        if page_pattern.match(s):
            continue

        # Skip date headers
        if date_pattern.match(s):
            continue

        # Skip boilerplate headers
        if s == "Application Documentation":
            continue
        if s.startswith("https://www.appsheet.com"):
            continue

        cleaned.append(line)

    return cleaned
