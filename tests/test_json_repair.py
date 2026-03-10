"""Tests for parse/json_repair.py — broken JSON recovery."""

import json

from appsheet_export_parser.parse.json_repair import (
    extract_ref_table_from_broken_json,
    repair_json,
)


class TestRepairJson:
    def test_valid_json_unchanged(self):
        original = '{"key": "value"}'
        result = repair_json(original)
        assert json.loads(result) == {"key": "value"}

    def test_removes_page_numbers(self):
        broken = '{"key": "val42/2718ue"}'
        result = repair_json(broken)
        parsed = json.loads(result)
        assert "key" in parsed

    def test_removes_date_headers(self):
        broken = '{"key": "value3/8/2026, 10:30 AM"}'
        result = repair_json(broken)
        assert "3/8/2026" not in result

    def test_removes_appsheet_urls(self):
        broken = '{"key": "https://www.appsheet.com/template/appdoc?appId=abc value"}'
        result = repair_json(broken)
        assert "appsheet.com" not in result

    def test_removes_form_feeds(self):
        broken = '{"key": "val\x0cue"}'
        result = repair_json(broken)
        assert "\x0c" not in result

    def test_balances_braces(self):
        broken = '{"key": "value"'
        result = repair_json(broken)
        assert result.count("{") == result.count("}")

    def test_balances_brackets(self):
        broken = '["a", "b"'
        result = repair_json(broken)
        assert result.count("[") == result.count("]")

    def test_removes_trailing_commas(self):
        broken = '{"a": 1, "b": 2, }'
        result = repair_json(broken)
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": 2}

    def test_handles_empty_input(self):
        assert repair_json("") == ""
        assert repair_json("   ") == "   "

    def test_complex_broken_json(self):
        broken = '{"ReferencedTableName": "Employee", "IsA42/2718PartOf": false'
        result = repair_json(broken)
        assert result.count("{") == result.count("}")


class TestExtractRefTableFromBrokenJson:
    def test_extracts_from_clean_json(self):
        parts = ['{"ReferencedTableName": "Employee", "IsAPartOf": false}']
        assert extract_ref_table_from_broken_json(parts) == "Employee"

    def test_extracts_from_broken_json(self):
        parts = ['"ReferencedTableName": "Work_Card"', "some garbage"]
        assert extract_ref_table_from_broken_json(parts) == "Work_Card"

    def test_returns_none_when_not_found(self):
        parts = ['{"SomeOtherKey": "value"}']
        assert extract_ref_table_from_broken_json(parts) is None

    def test_handles_missing_quotes(self):
        parts = ['ReferencedTableName: "Shops"']
        result = extract_ref_table_from_broken_json(parts)
        assert result == "Shops"
