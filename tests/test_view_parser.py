"""Tests for parse/view_parser.py — view parsing."""

from appsheet_export_parser.parse.section_finder import DocumentSections, Section, find_sections
from appsheet_export_parser.parse.view_parser import parse_views


class TestParseViews:
    def test_parses_tab_delimited_views(self):
        lines = [
            "Slices",
            "some slice content",
            "UX",
            "View name\tSales Chart",
            "View type\tchart",
            "Position\tcenter",
            "For this data\tSales Report",
            "View name\tOrder Log",
            "View type\ttable",
            "Position\tleft",
            "For this data\tOrder History",
            "Format Rules",
            "some rule",
            "Behavior",
        ]
        sections = find_sections(lines)
        views = parse_views(lines, sections)
        assert len(views) == 2
        assert views[0]["name"] == "Sales Chart"
        assert views[0]["type"] == "chart"
        assert views[0]["table"] == "Sales Report"
        assert views[1]["name"] == "Order Log"

    def test_parses_line_separated_views(self):
        lines = [
            "UX",
            "View name",
            "My View",
            "View type",
            "deck",
            "Position",
            "center",
            "For this data",
            "Employees",
            "Format Rules",
            "Behavior",
        ]
        sections = find_sections(lines)
        views = parse_views(lines, sections)
        assert len(views) == 1
        assert views[0]["name"] == "My View"
        assert views[0]["type"] == "deck"
        assert views[0]["table"] == "Employees"

    def test_empty_when_no_ux_section(self):
        lines = [
            "Schema Name Test_Schema",
            "content",
            "Behavior",
            "action content",
        ]
        sections = find_sections(lines)
        views = parse_views(lines, sections)
        assert views == []

    def test_stops_at_format_rules(self):
        lines = [
            "UX",
            "View name\tView1",
            "View type\ttable",
            "Format Rules",
            "View name\tNotAView",
            "Behavior",
        ]
        sections = find_sections(lines)
        views = parse_views(lines, sections)
        assert len(views) == 1
        assert views[0]["name"] == "View1"
