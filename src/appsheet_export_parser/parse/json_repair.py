"""Repair JSON broken across PDF page boundaries.

When pdftotext extracts text, page breaks can land in the middle of JSON
objects (like Type Qualifier), causing:
- Truncated strings
- Missing closing braces/brackets
- Broken escape sequences
- Inserted page headers mid-JSON
"""

from __future__ import annotations

import re


def repair_json(broken: str) -> str:
    """Attempt to repair broken JSON from PDF extraction.

    Applies a series of heuristic fixes:
    1. Remove page noise injected mid-JSON
    2. Fix unescaped quotes in values
    3. Balance braces and brackets
    4. Remove trailing commas
    """
    if not broken or not broken.strip():
        return broken

    text = broken

    # Remove page break noise that may have been injected into JSON
    # Pattern: page numbers like "42/2718" or date headers
    text = re.sub(r"\d+/\d{2,}\s*", "", text)
    text = re.sub(r"\d+/\d+/\d+,\s+\d+:\d+\s+(AM|PM)\s*", "", text)
    text = re.sub(r"Application Documentation\s*", "", text)
    text = re.sub(r"https://www\.appsheet\.com\S*\s*", "", text)

    # Remove form feeds and surrounding whitespace
    text = text.replace("\x0c", "")

    # Fix JSON keywords split by spaces (from space-join of page-broken lines)
    # Anchored after ":" to avoid matching inside string values
    for keyword in ('true', 'false', 'null'):
        for split_pos in range(1, len(keyword)):
            left = re.escape(keyword[:split_pos])
            right = re.escape(keyword[split_pos:])
            text = re.sub(rf':\s*{left}\s+{right}(?=[,\s\}}\]])', f':{keyword}', text)

    # Fix truncated key-value pairs (missing closing quote + value)
    # e.g., "ReferencedTableName": " → "ReferencedTableName": ""
    text = re.sub(r'":\s*"([^"]*?)$', r'": "\1"', text, flags=re.MULTILINE)

    # Fix keys that lost their colon separator
    text = re.sub(r'"([A-Za-z_]+)"\s+"', r'"\1": "', text)

    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Try to extract ReferencedTableName even from severely broken JSON
    # This handles cases where the JSON is too broken to parse but we
    # can still find the table name
    if "ReferencedTableName" in text:
        m = re.search(r'"ReferencedTableName"\s*:\s*"([^"]+)"', text)
        if m:
            # If we can find the key value, ensure the JSON structure is valid enough
            pass  # The regular repair below should handle it

    # Balance braces
    open_braces = text.count("{")
    close_braces = text.count("}")
    if open_braces > close_braces:
        text = text + "}" * (open_braces - close_braces)
    elif close_braces > open_braces:
        text = "{" * (close_braces - open_braces) + text

    # Balance brackets
    open_brackets = text.count("[")
    close_brackets = text.count("]")
    if open_brackets > close_brackets:
        text = text + "]" * (open_brackets - close_brackets)
    elif close_brackets > open_brackets:
        text = "[" * (close_brackets - open_brackets) + text

    return text


def extract_ref_table_from_broken_json(raw_parts: list[str]) -> str | None:
    """Last-resort extraction of ReferencedTableName from broken JSON.

    When repair_json + json.loads fails, scan the raw text for the
    ReferencedTableName field value directly.
    """
    raw = "".join(raw_parts)
    m = re.search(r'"?ReferencedTableName"?\s*:?\s*"([^"]+)"', raw)
    if m:
        return m.group(1)
    return None
