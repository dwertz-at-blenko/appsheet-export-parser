"""Tests for parse/action_parser.py — action parsing with orphan recovery."""

from appsheet_export_parser.parse.action_parser import _parse_single_action


class TestOrphanRecoveryProperties:
    def test_orphan_prepended_to_properties(self):
        """Page-break orphan before 'With these properties' is recovered."""
        cleaned = [
            "Action name",
            "Split Job",
            "Do this",
            "Data: set the values of some columns in this row",
            "Action order",
            "207",
            '{"Actions":[{"ActionName":"Split Job',  # orphan first half
            "With these properties",
            'View"}]}',  # second half after the label
        ]
        action = _parse_single_action(cleaned, "Split Job")
        assert "properties" in action
        # Space-join reconstructs the full value across page break
        assert action["properties"]["Actions"][0]["ActionName"] == "Split Job View"

    def test_no_orphans_when_clean(self):
        """Normal case: no orphans, properties parsed from after the label."""
        cleaned = [
            "Action name",
            "Test",
            "With these properties",
            '{"Actions": [{"ActionName": "Test"}]}',
        ]
        action = _parse_single_action(cleaned, "Test")
        assert "properties" in action
        assert action["properties"]["Actions"][0]["ActionName"] == "Test"


class TestOrphanRecoveryCondition:
    def test_orphan_prepended_to_condition(self):
        """Page-break orphan before 'Only if this condition is true' is recovered."""
        cleaned = [
            "Action name",
            "Check Admin",
            "Do this",
            "Data: set the values of some columns in this row",
            "Prominence",
            "Do not display",
            "=IF( OR( ANY(SELECT(",  # orphan formula start
            "Only if this condition is true 'Admin',",
            "'QA' ), TRUE, FALSE )",
        ]
        action = _parse_single_action(cleaned, "Check Admin")
        assert "condition" in action
        assert "=IF( OR( ANY(SELECT(" in action["condition"]
        assert "'QA' ), TRUE, FALSE )" in action["condition"]


class TestMultiLineCondition:
    def test_condition_spans_multiple_lines(self):
        """Condition formula split across lines is fully captured."""
        cleaned = [
            "Action name",
            "Validate",
            "Only if this condition is true =IF(",
            "[Status] = 'Active',",
            "TRUE, FALSE)",
            "Prominence",
            "Do not display",
        ]
        action = _parse_single_action(cleaned, "Validate")
        assert "condition" in action
        assert "=IF(" in action["condition"]
        assert "TRUE, FALSE)" in action["condition"]
        # Prominence should be parsed as its own field, not part of condition
        assert action["prominence"] == "Do not display"

    def test_single_line_condition_still_works(self):
        """Simple inline condition works as before."""
        cleaned = [
            "Action name",
            "Simple",
            "Only if this condition is true [Status] = 'Active'",
            "Prominence",
            "Display prominently",
        ]
        action = _parse_single_action(cleaned, "Simple")
        assert action["condition"] == "[Status] = 'Active'"


class TestOrphanClearing:
    def test_orphans_cleared_at_recognized_fields(self):
        """Orphans are cleared when hitting a non-consumer recognized field."""
        cleaned = [
            "Action name",
            "Test",
            "some garbage line",  # would be orphan
            "Bulk action?",       # recognized field clears orphans
            "No",
            "With these properties",
            '{"Actions": []}',
        ]
        action = _parse_single_action(cleaned, "Test")
        # The orphan should NOT appear in properties
        assert action.get("properties") == {"Actions": []}
        assert action["bulk"] is False
