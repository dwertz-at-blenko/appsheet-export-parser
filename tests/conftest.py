"""Shared test fixtures for appsheet-export-parser."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BERP_DIR = FIXTURES_DIR / "berp"
BERP_PDF = BERP_DIR / "BERP 1.7 Live Documentation 3-8-26.pdf"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def berp_pdf() -> Path:
    return BERP_PDF
