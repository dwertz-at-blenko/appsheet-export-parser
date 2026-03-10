"""Tests for analyze/validator.py — count validation."""

from appsheet_export_parser.analyze.validator import validate_counts
from appsheet_export_parser.extract.header import HeaderCounts


class TestValidateCounts:
    def test_exact_match(self):
        header = HeaderCounts(tables=5, columns=100, actions=20, slices=3)
        schemas = {f"Table{i}": [{"name": "col"}] * 20 for i in range(5)}
        actions = [{"name": f"action{i}"} for i in range(20)]
        slices = [{"name": f"slice{i}"} for i in range(3)]

        report = validate_counts(header, schemas, actions, slices)
        assert report.all_pass

    def test_table_count_warning(self):
        header = HeaderCounts(tables=10, columns=100)
        schemas = {f"Table{i}": [{"name": "col"}] * 10 for i in range(7)}

        report = validate_counts(header, schemas, [], [])
        table_result = next(r for r in report.results if r.field == "Tables")
        assert table_result.status == "warning"  # 3 missing, within tolerance

    def test_column_mismatch_warning(self):
        header = HeaderCounts(tables=1, columns=100)
        schemas = {"Table1": [{"name": "col"}] * 98}

        report = validate_counts(header, schemas, [], [])
        col_result = next(r for r in report.results if r.field == "Columns")
        assert col_result.status == "warning"  # 2% diff

    def test_column_mismatch_error(self):
        header = HeaderCounts(tables=1, columns=100)
        schemas = {"Table1": [{"name": "col"}] * 50}

        report = validate_counts(header, schemas, [], [])
        col_result = next(r for r in report.results if r.field == "Columns")
        assert col_result.status == "error"  # 50% diff

    def test_empty_header(self):
        header = HeaderCounts()
        report = validate_counts(header, {}, [], [])
        assert len(report.results) == 0

    def test_format_report(self):
        header = HeaderCounts(tables=5, columns=100)
        schemas = {f"T{i}": [{"name": "c"}] * 20 for i in range(5)}
        report = validate_counts(header, schemas, [], [])
        text = report.format_report()
        assert "OK" in text
        assert "Tables" in text

    def test_action_warning(self):
        header = HeaderCounts(tables=1, columns=1, actions=100)
        schemas = {"T1": [{"name": "c"}]}
        actions = [{"name": f"a{i}"} for i in range(95)]  # 5% diff = warning
        report = validate_counts(header, schemas, actions, [])
        action_result = next(r for r in report.results if r.field == "Actions")
        assert action_result.status == "warning"

    def test_action_error(self):
        header = HeaderCounts(tables=1, columns=1, actions=100)
        schemas = {"T1": [{"name": "c"}]}
        actions = [{"name": f"a{i}"} for i in range(70)]  # 30% diff = error
        report = validate_counts(header, schemas, actions, [])
        action_result = next(r for r in report.results if r.field == "Actions")
        assert action_result.status == "error"
