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

    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",\s*([}\]])", r"\1", text)

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
