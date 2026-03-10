"""Tests for parse/section_finder.py — document section detection."""

from appsheet_export_parser.parse.section_finder import DocumentSections, find_sections


class TestFindSections:
    def test_finds_schema_blocks(self):
        lines = [
            "Header content",
            "",
            "Schema Name Employee_Schema",
            "Column 1: Name",
            "Type",
            "Text",
            "",
            "Schema Name Work_Card_Schema",
            "Column 1: ID",
            "Type",
            "Number",
            "",
            "Slices",
        ]
        sections = find_sections(lines)
        assert len(sections.schema_blocks) == 2
        assert sections.schema_blocks[0] == (2, "Employee_Schema")
        assert sections.schema_blocks[1] == (7, "Work_Card_Schema")

    def test_finds_major_sections(self):
        lines = [
            "Header",
            "Schema Name Test_Schema",
            "content",
            "Slices",
            "slice content",
            "UX",
            "ux content",
            "Behavior",
            "behavior content",
            "Automation",
            "automation content",
        ]
        sections = find_sections(lines)

        assert sections.slices is not None
        assert sections.slices.start_line == 3

        assert sections.ux is not None
        assert sections.ux.start_line == 5

        assert sections.behavior is not None
        assert sections.behavior.start_line == 7

        assert sections.automation is not None
        assert sections.automation.start_line == 9

    def test_sets_section_end_lines(self):
        lines = [
            "Schema Name Test_Schema",
            "content",
            "Slices",
            "slice content",
            "UX",
            "ux content",
            "Behavior",
            "behavior content",
        ]
        sections = find_sections(lines)

        assert sections.schemas is not None
        assert sections.schemas.end_line == 2  # ends at Slices

        assert sections.slices is not None
        assert sections.slices.end_line == 4  # ends at UX

        assert sections.ux is not None
        assert sections.ux.end_line == 6  # ends at Behavior

    def test_handles_no_sections(self):
        lines = ["Just", "some", "content"]
        sections = find_sections(lines)
        assert sections.schemas is None
        assert sections.slices is None
        assert sections.ux is None
        assert sections.behavior is None
        assert len(sections.schema_blocks) == 0

    def test_schema_section_covers_all_schemas(self):
        lines = [
            "Header",
            "Schema Name TableA_Schema",
            "col A stuff",
            "Schema Name TableB_Schema",
            "col B stuff",
            "Schema Name TableC_Schema",
            "col C stuff",
            "Slices",
        ]
        sections = find_sections(lines)
        assert sections.schemas is not None
        assert sections.schemas.start_line == 1
        assert sections.schemas.end_line == 7
        assert len(sections.schema_blocks) == 3

    def test_ignores_indented_section_markers(self):
        """Section markers that are indented are content, not headers."""
        lines = [
            "Schema Name Test_Schema",
            "  Slices",  # indented — not a section header
            "content",
            "Slices",  # not indented — real header
        ]
        sections = find_sections(lines)
        assert sections.slices is not None
        assert sections.slices.start_line == 3
