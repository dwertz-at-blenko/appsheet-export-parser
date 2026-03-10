"""Shared test fixtures for appsheet-export-parser."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_DIR = FIXTURES_DIR / "sample"
SAMPLE_PDF = SAMPLE_DIR / "sample-app-documentation.pdf"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_pdf() -> Path:
    return SAMPLE_PDF
