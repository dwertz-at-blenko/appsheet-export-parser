"""Integration tests — full parse against BERP v1.7 Live PDF.

These tests require the BERP PDF fixture at:
  tests/fixtures/berp/BERP 1.7 Live Documentation 3-8-26.pdf

Skip with: pytest -m "not integration"
"""

from __future__ import annotations

from pathlib import Path

import pytest

BERP_PDF = Path(__file__).parent / "fixtures" / "berp" / "BERP 1.7 Live Documentation 3-8-26.pdf"

pytestmark = pytest.mark.skipif(
    not BERP_PDF.exists(),
    reason="BERP PDF fixture not available",
)


class TestBerpLiveParse:
    """Validate parser against BERP v1.7 Live known counts."""

    @pytest.fixture(scope="class")
    def parsed(self):
        from appsheet_export_parser.parser import parse_pdf
        return parse_pdf(str(BERP_PDF), verbose=False)

    def test_app_metadata(self, parsed):
        meta = parsed["metadata"]
        assert meta["app_name"] == "BERP V1.7 - Live"
        assert meta["version"] == "5.001266"

    def test_table_count(self, parsed):
        schemas = parsed["schemas"]
        assert len(schemas) == 55

    def test_column_count_exact(self, parsed):
        """Column count must be an EXACT MATCH with header."""
        schemas = parsed["schemas"]
        total_cols = sum(len(cols) for cols in schemas.values())
        assert total_cols == 3044

    def test_official_counts_in_output(self, parsed):
        official = parsed["metadata"]["official_counts"]
        assert official["tables"] == 55
        assert official["columns"] == 3044
        assert official["slices"] == 36
        assert official["actions"] == 293

    def test_slice_count(self, parsed):
        """Slices should be deduplicated to match header count."""
        assert len(parsed["slices"]) == 36

    def test_action_count(self, parsed):
        """Actions include cross-table instances — should match header exactly."""
        actions = parsed["actions"]
        assert len(actions) == 293

    def test_relationships_extracted(self, parsed):
        rels = parsed["relationships"]
        assert len(rels) > 80  # PDF mode loses some refs

    def test_enum_fields(self, parsed):
        enums = parsed["enum_fields"]
        assert len(enums) == 41

    def test_core_process_classification(self, parsed):
        summary = parsed["metadata"]["summary"]
        # Auto-classifier puts Home/Buttons in 'skip', so core + process < 55
        assert summary["core_tables"] + summary["process_tables"] <= 55
        assert summary["core_tables"] > 15  # Expect at least 15 core tables
        assert summary["process_tables"] > 20  # Expect at least 20 process tables

    def test_known_tables_present(self, parsed):
        """Key BERP tables must be present."""
        schemas = parsed["schemas"]
        expected_tables = [
            "Employee",
            "Work_Card",
            "WorkCardGrading",
            "Shops",
            "Grinding",
        ]
        for table in expected_tables:
            assert table in schemas, f"Missing table: {table}"

    def test_employee_columns(self, parsed):
        """Spot-check Employee table has expected columns."""
        emp_cols = parsed["schemas"]["Employee"]
        col_names = [c["name"] for c in emp_cols]
        assert "First Name" in col_names or "Combined Name" in col_names
        assert len(emp_cols) > 10  # Employee has many columns

    def test_schema_version(self, parsed):
        assert parsed["schema_version"] == "1.0.0"
