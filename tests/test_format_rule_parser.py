"""Tests for parse/format_rule_parser.py — format rule parsing."""

from appsheet_export_parser.parse.section_finder import find_sections
from appsheet_export_parser.parse.format_rule_parser import parse_format_rules


class TestParseFormatRules:
    def test_parses_format_rules_with_rule_name_markers(self):
        lines = [
            "UX",
            "View name\tSomeView",
            "View type\ttable",
            "Format Rules",
            "Rule name Older than 1 hour",
            "Rule name",
            "Older than 1 hour",
            "For this data",
            "Furnace Temperature Log",
            "If this condition is true",
            "=AND(1=1)",
            "Rule order",
            "1",
            "Is this format rule disabled?",
            "Yes",
            "Rule name Bold Row",
            "Rule name",
            "Bold Row",
            "For this data",
            "Pull_Totals",
            "Rule order",
            "2",
            "Behavior",
        ]
        sections = find_sections(lines)
        rules = parse_format_rules(lines, sections)
        assert len(rules) == 2
        assert rules[0]["name"] == "Older than 1 hour"
        assert rules[0]["table"] == "Furnace Temperature Log"
        assert rules[0]["condition"] == "=AND(1=1)"
        assert rules[0]["order"] == 1
        assert rules[0]["disabled"] is True
        assert rules[1]["name"] == "Bold Row"
        assert rules[1]["table"] == "Pull_Totals"

    def test_deduplicates_inline_and_bare_markers(self):
        """Each rule appears twice: inline + bare. Should deduplicate."""
        lines = [
            "UX",
            "Format Rules",
            "Rule name Test Rule",
            "Rule name",
            "Test Rule",
            "For this data",
            "Table1",
            "Behavior",
        ]
        sections = find_sections(lines)
        rules = parse_format_rules(lines, sections)
        assert len(rules) == 1
        assert rules[0]["name"] == "Test Rule"

    def test_empty_when_no_format_rules_header(self):
        lines = [
            "UX",
            "View name\tSomeView",
            "Behavior",
        ]
        sections = find_sections(lines)
        rules = parse_format_rules(lines, sections)
        assert rules == []

    def test_empty_when_no_ux_section(self):
        lines = [
            "Schema Name Test_Schema",
            "content",
            "Behavior",
        ]
        sections = find_sections(lines)
        rules = parse_format_rules(lines, sections)
        assert rules == []
