"""PDF text extraction using pdftotext."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def check_pdftotext() -> bool:
    """Check if pdftotext is available."""
    return shutil.which("pdftotext") is not None


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract text from a PDF using pdftotext.

    Returns the full extracted text as a string.
    Raises RuntimeError if pdftotext is not installed or fails.
    """
    if not check_pdftotext():
        raise RuntimeError(
            "pdftotext not found. Install poppler-utils:\n"
            "  Ubuntu/Debian: sudo apt install poppler-utils\n"
            "  macOS: brew install poppler\n"
            "  Or use URL mode instead: appsheet-parse parse <url>"
        )

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    result = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {result.stderr}")

    return result.stdout


def get_page_count(text: str) -> int | None:
    """Auto-detect the page count from page number patterns in extracted text.

    AppSheet PDFs have page numbers like "42/2718" scattered throughout.
    Scans the first ~1000 lines to find the pattern and extract the total.
    """
    import re

    for line in text.split("\n")[:1000]:
        m = re.match(r"^\s*\d+/(\d+)\s*$", line.strip())
        if m:
            return int(m.group(1))
    return None
