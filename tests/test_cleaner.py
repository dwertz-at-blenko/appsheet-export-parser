"""Tests for extract/cleaner.py — page noise removal."""

from appsheet_export_parser.extract.cleaner import clean_lines, clean_text


class TestCleanLines:
    def test_removes_page_numbers(self):
        lines = [
            "Some content",
            "42/2718",
            "More content",
            "100/2718",
        ]
        result = clean_lines(lines, page_count=2718)
        assert result == ["Some content", "More content"]

    def test_removes_date_headers(self):
        lines = [
            "Content before",
            "3/8/2026, 10:30 AM",
            "Content after",
        ]
        result = clean_lines(lines)
        assert result == ["Content before", "Content after"]

    def test_removes_form_feed_lines(self):
        lines = [
            "Content",
            "\x0cSome page header",
            "More content",
        ]
        result = clean_lines(lines)
        assert result == ["Content", "More content"]

    def test_removes_application_documentation(self):
        lines = [
            "Content",
            "Application Documentation",
            "More content",
        ]
        result = clean_lines(lines)
        assert result == ["Content", "More content"]

    def test_removes_appsheet_urls(self):
        lines = [
            "Content",
            "https://www.appsheet.com/template/appdoc?appId=abc123",
            "More content",
        ]
        result = clean_lines(lines)
        assert result == ["Content", "More content"]

    def test_auto_detects_page_count(self):
        lines = [
            "Header",
            "1/105",
            "Content",
            "2/105",
            "More content",
        ]
        result = clean_lines(lines, page_count=None)
        assert "1/105" not in [l.strip() for l in result]
        assert "2/105" not in [l.strip() for l in result]

    def test_preserves_normal_content(self):
        lines = [
            "Column 1: Name",
            "Type",
            "Text",
            "Ref",
            "Employee",
        ]
        result = clean_lines(lines)
        assert result == lines

    def test_handles_various_page_counts(self):
        for total in [42, 105, 2718]:
            lines = [f"1/{total}", "content", f"10/{total}"]
            result = clean_lines(lines, page_count=total)
            assert len(result) == 1
            assert result[0] == "content"


class TestCleanText:
    def test_full_clean(self):
        text = "Content\n42/100\nMore content\n3/8/2026, 10:30 AM\nFinal"
        result = clean_text(text, page_count=100)
        assert "42/100" not in result
        assert "Content" in result
        assert "More content" in result
        assert "Final" in result
