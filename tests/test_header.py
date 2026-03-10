"""Tests for extract/header.py — summary count extraction."""

from appsheet_export_parser.extract.header import (
    HeaderCounts,
    extract_app_metadata,
    extract_header_counts,
)


class TestExtractHeaderCounts:
    def test_single_line_format(self):
        text = (
            "Some preamble\n"
            "Data Summary: 55 Tables, 3044 Columns, 36 Slices\n"
            "UX Summary: 153 Views, 33 Format Rules\n"
            "Behavior Summary: 293 Actions, 0 Workflow Rules\n"
            "More content\n"
        )
        counts = extract_header_counts(text)
        assert counts.tables == 55
        assert counts.columns == 3044
        assert counts.slices == 36
        assert counts.views == 153
        assert counts.format_rules == 33
        assert counts.actions == 293
        assert counts.workflow_rules == 0

    def test_multiline_format(self):
        text = (
            "Short Name\n\nMyApp\n\n"
            "Data Summary\n\n"
            "53 Tables\n"
            "2151 Columns\n"
            "32 Slices\n\n"
            "UX Summary\n\n"
            "120 Views\n"
            "15 Format Rules\n\n"
            "Behavior Summary\n\n"
            "200 Actions\n"
            "5 Workflow Rules\n"
        )
        counts = extract_header_counts(text)
        assert counts.tables == 53
        assert counts.columns == 2151
        assert counts.slices == 32
        assert counts.views == 120
        assert counts.format_rules == 15
        assert counts.actions == 200
        assert counts.workflow_rules == 5

    def test_has_data_property(self):
        empty = HeaderCounts()
        assert not empty.has_data

        with_data = HeaderCounts(tables=5, columns=100)
        assert with_data.has_data

    def test_no_header_returns_empty(self):
        text = "Just some random text\nno summary here\n"
        counts = extract_header_counts(text)
        assert counts.tables == 0
        assert counts.columns == 0
        assert not counts.has_data


class TestExtractAppMetadata:
    def test_extracts_app_name_and_version(self):
        text = (
            "Short Name\n\n"
            "My App v2.0\n\n"
            "Version\n\n"
            "5.001266\n\n"
            "Stable Version\n\n"
            "5.001045\n"
        )
        meta = extract_app_metadata(text)
        assert meta["app_name"] == "My App v2.0"
        assert meta["version"] == "5.001266"
        assert meta["stable_version"] == "5.001045"

    def test_handles_missing_fields(self):
        text = "Some random content\nno metadata here\n"
        meta = extract_app_metadata(text)
        assert "app_name" not in meta
        assert "version" not in meta
