"""Integration tests — full parse against a sample AppSheet PDF.

These tests require a PDF fixture at:
  tests/fixtures/sample/sample-app-documentation.pdf

Skip with: pytest -m "not integration"
"""

from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE_PDF = Path(__file__).parent / "fixtures" / "sample" / "sample-app-documentation.pdf"

pytestmark = pytest.mark.skipif(
    not SAMPLE_PDF.exists(),
    reason="Sample PDF fixture not available",
)


class TestSampleAppParse:
    """Validate parser against a sample AppSheet app.

    To use: place any AppSheet documentation PDF in the fixture path above,
    then update the expected counts below to match your app.
    """

    @pytest.fixture(scope="class")
    def parsed(self):
        from appsheet_export_parser.parser import parse_pdf
        return parse_pdf(str(SAMPLE_PDF), verbose=False)

    def test_has_metadata(self, parsed):
        meta = parsed["metadata"]
        assert "app_name" in meta or "version" in meta

    def test_has_tables(self, parsed):
        schemas = parsed["schemas"]
        assert len(schemas) > 0

    def test_has_columns(self, parsed):
        schemas = parsed["schemas"]
        total_cols = sum(len(cols) for cols in schemas.values())
        assert total_cols > 0

    def test_official_counts_present(self, parsed):
        official = parsed["metadata"]["official_counts"]
        assert "tables" in official
        assert "columns" in official

    def test_relationships_extracted(self, parsed):
        rels = parsed["relationships"]
        assert isinstance(rels, list)

    def test_schema_version(self, parsed):
        assert parsed["schema_version"] == "1.0.0"
