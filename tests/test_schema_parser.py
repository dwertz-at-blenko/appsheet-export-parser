"""Tests for parse/schema_parser.py — table and column parsing."""

from appsheet_export_parser.parse.schema_parser import (
    _parse_columns_from_block,
    _parse_single_column,
    parse_all_schemas,
)
from appsheet_export_parser.parse.section_finder import find_sections


class TestParseAllSchemas:
    def test_parses_single_table(self):
        lines = [
            "Schema Name Employee_Schema",
            "",
            "Column 1: Name",
            "",
            "Column name",
            "",
            "Name",
            "",
            "Type",
            "",
            "Text",
            "",
            "Column 2: Email",
            "",
            "Column name",
            "",
            "Email",
            "",
            "Type",
            "",
            "Email",
            "",
            "Slices",
        ]
        sections = find_sections(lines)
        schemas = parse_all_schemas(lines, sections)
        assert "Employee" in schemas
        assert len(schemas["Employee"]) == 2
        assert schemas["Employee"][0]["name"] == "Name"
        assert schemas["Employee"][0]["type"] == "Text"
        assert schemas["Employee"][1]["name"] == "Email"
        assert schemas["Employee"][1]["type"] == "Email"

    def test_parses_multiple_tables(self):
        lines = [
            "Schema Name Employee_Schema",
            "",
            "Column 1: Name",
            "Column name",
            "Name",
            "Type",
            "Text",
            "",
            "Schema Name Work_Card_Schema",
            "",
            "Column 1: ID",
            "Column name",
            "ID",
            "Type",
            "Number",
            "",
            "Slices",
        ]
        sections = find_sections(lines)
        schemas = parse_all_schemas(lines, sections)
        assert len(schemas) == 2
        assert "Employee" in schemas
        assert "Work_Card" in schemas

    def test_skips_duplicate_schemas(self):
        lines = [
            "Schema Name Test_Schema",
            "Column 1: A",
            "Type",
            "Text",
            "Schema Name Test_Schema",
            "Column 1: A",
            "Type",
            "Text",
            "Slices",
        ]
        sections = find_sections(lines)
        schemas = parse_all_schemas(lines, sections)
        assert len(schemas) == 1


class TestParseSingleColumn:
    def test_basic_column(self):
        lines = [
            "Column 1: Name",
            "Column name",
            "Name",
            "Type",
            "Text",
            "Visible?",
            "Yes",
        ]
        col = _parse_single_column(lines, "Name")
        assert col["name"] == "Name"
        assert col["type"] == "Text"
        assert col["visible"] == "Yes"

    def test_boolean_fields(self):
        lines = [
            "Column 1: ID",
            "Type",
            "Number",
            "Key",
            "Yes",
            "Read-Only",
            "Yes",
            "Hidden",
            "No",
            "Label",
            "Yes",
        ]
        col = _parse_single_column(lines, "ID")
        assert col["is_key"] is True
        assert col["read_only"] is True
        assert col["hidden"] is False
        assert col["is_label"] is True

    def test_ref_column_with_type_qualifier(self):
        lines = [
            "Column 1: Employee",
            "Type",
            "Ref",
            "Type Qualifier",
            '{"ReferencedTableName": "Employee", "IsAPartOf": false}',
        ]
        col = _parse_single_column(lines, "Employee")
        assert col["type"] == "Ref"
        assert col["referenced_table"] == "Employee"

    def test_app_formula_multiline(self):
        lines = [
            "Column 1: Total",
            "Type",
            "Number",
            "App formula",
            "SUM(",
            "  [Quantity] * [Price]",
            ")",
            "Visible?",
            "Yes",
        ]
        col = _parse_single_column(lines, "Total")
        assert "SUM(" in col["app_formula"]
        assert "[Quantity]" in col["app_formula"]

    def test_enum_values(self):
        lines = [
            "Column 1: Status",
            "Type",
            "Enum",
            "Type Qualifier",
            '{"EnumValues": ["Active", "Inactive", "Pending"]}',
        ]
        col = _parse_single_column(lines, "Status")
        assert col["enum_values"] == ["Active", "Inactive", "Pending"]


    def test_multiline_description(self):
        """Description spanning multiple lines should be joined."""
        lines = [
            "Column 1: GrindingID",
            "Type",
            "Text",
            "Description",
            "References the value in the Grinding_ID",
            "column of the Grinding table",
            "Visible?",
            "Yes",
        ]
        col = _parse_single_column(lines, "GrindingID")
        assert col["description"] == "References the value in the Grinding_ID column of the Grinding table"

    def test_description_guard_against_known_field(self):
        """When 'Type' immediately follows 'Description', don't capture it as the description."""
        lines = [
            "Column 1: Status",
            "Description",
            "Type",
            "Enum",
        ]
        col = _parse_single_column(lines, "Status")
        assert "description" not in col
        assert col["type"] == "Enum"

    def test_ref_override_from_type_qualifier(self):
        """P1: When Type Qualifier has ReferencedTableName but raw type is Number,
        the column type should be overridden to Ref."""
        lines = [
            "Column 1: Furnace Number",
            "Type",
            "Number",
            "Type Qualifier",
            '{"ReferencedTableName": "Furnace Data", "IsAPartOf": false}',
        ]
        col = _parse_single_column(lines, "Furnace Number")
        assert col["type"] == "Ref"
        assert col["referenced_table"] == "Furnace Data"
        assert col.get("_original_type") == "Number"

    def test_ref_type_stays_ref(self):
        """P1: When raw type is already Ref, no _original_type is set."""
        lines = [
            "Column 1: Employee",
            "Type",
            "Ref",
            "Type Qualifier",
            '{"ReferencedTableName": "Employee", "IsAPartOf": false}',
        ]
        col = _parse_single_column(lines, "Employee")
        assert col["type"] == "Ref"
        assert col["referenced_table"] == "Employee"
        assert "_original_type" not in col

    def test_enum_values_broken_json(self):
        """P3: Enum extraction from malformed JSON with unquoted key."""
        lines = [
            "Column 1: Status",
            "Type",
            "Enum",
            "Type Qualifier",
            '{EnumValues: ["Active", "Inactive"]}',
        ]
        col = _parse_single_column(lines, "Status")
        assert col.get("enum_values") == ["Active", "Inactive"]


class TestParseColumnsFromBlock:
    def test_handles_empty_block(self):
        cols = _parse_columns_from_block(["Schema Name Test_Schema"])
        assert cols == []

    def test_parses_multiple_columns(self):
        lines = [
            "Schema Name Test_Schema",
            "Column 1: A",
            "Type",
            "Text",
            "Column 2: B",
            "Type",
            "Number",
            "Column 3: C",
            "Type",
            "Ref",
        ]
        cols = _parse_columns_from_block(lines)
        assert len(cols) == 3
        assert cols[0]["name"] == "A"
        assert cols[1]["name"] == "B"
        assert cols[2]["name"] == "C"

    def test_handles_split_column_marker(self):
        """Column marker split across page break: 'Column N:' alone, name on next line."""
        lines = [
            "Schema Name Test_Schema",
            "Column 1: Normal",
            "Type",
            "Text",
            "Column 2:",
            "Split Name",
            "Type",
            "Number",
            "Column 3: Also Normal",
            "Type",
            "Ref",
        ]
        cols = _parse_columns_from_block(lines)
        assert len(cols) == 3
        assert cols[0]["name"] == "Normal"
        assert cols[1]["name"] == "Split Name"
        assert cols[2]["name"] == "Also Normal"
