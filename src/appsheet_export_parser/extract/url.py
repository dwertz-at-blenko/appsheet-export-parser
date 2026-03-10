"""URL-based extraction — fetch live AppSheet documentation page.

This is the preferred extraction path (better data quality than PDF).
Full implementation in Phase 2.
"""

from __future__ import annotations


def extract_text_from_url(url: str) -> str:
    """Fetch and extract text from a live AppSheet documentation URL.

    Preferred over PDF extraction because:
    - No page boundary issues (broken JSON, truncated formulas)
    - Structured HTML is easier to parse
    - Live data is more current

    Args:
        url: AppSheet documentation URL
            (e.g., "https://www.appsheet.com/template/appdoc?appId=...")

    Returns:
        Extracted text suitable for the parse stage.

    Raises:
        NotImplementedError: URL extraction is not yet implemented (Phase 2).
    """
    raise NotImplementedError(
        "URL extraction is not yet implemented. "
        "Use PDF mode instead: appsheet-parse parse <pdf-path>\n"
        "URL support coming in v0.2.0."
    )
