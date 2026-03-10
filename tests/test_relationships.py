"""Tests for analyze/relationships.py — Ref extraction and inference."""

from appsheet_export_parser.analyze.relationships import (
    _generate_candidates,
    _infer_ref_target,
    extract_relationships,
)


class TestExtractRelationships:
    def test_extracts_ref_with_target(self):
        schemas = {
            "Work_Card": [
                {"name": "Employee", "type": "Ref", "referenced_table": "Employee"},
            ],
            "Employee": [
                {"name": "Name", "type": "Text"},
            ],
        }
        rels = extract_relationships(schemas)
        assert len(rels) == 1
        assert rels[0].from_table == "Work_Card"
        assert rels[0].from_column == "Employee"
        assert rels[0].to_table == "Employee"

    def test_infers_missing_target(self):
        schemas = {
            "Work_Card": [
                {"name": "Employee", "type": "Ref"},  # no referenced_table
            ],
            "Employee": [
                {"name": "Name", "type": "Text"},
            ],
        }
        rels = extract_relationships(schemas)
        assert len(rels) == 1
        assert rels[0].to_table == "Employee"

    def test_skips_non_ref_columns(self):
        schemas = {
            "Work_Card": [
                {"name": "Name", "type": "Text"},
                {"name": "Count", "type": "Number"},
            ],
        }
        rels = extract_relationships(schemas)
        assert len(rels) == 0

    def test_handles_broken_target(self):
        schemas = {
            "Work_Card": [
                {"name": "Shop_ID", "type": "Ref", "referenced_table": "NonExistent"},
            ],
            "Shops": [
                {"name": "Name", "type": "Text"},
            ],
        }
        rels = extract_relationships(schemas)
        # Should infer "Shops" from "Shop_ID" via _ID stripping + plural
        assert len(rels) == 1
        assert rels[0].to_table == "Shops"


class TestInferRefTarget:
    def test_direct_match(self):
        tables = {"Employee", "Work_Card", "Shops"}
        assert _infer_ref_target("Employee", tables) == "Employee"

    def test_strip_related_prefix(self):
        tables = {"Work_Card", "Employee"}
        assert _infer_ref_target("Related Work_Card", tables) == "Work_Card"

    def test_strip_id_suffix(self):
        tables = {"Shop", "Employee"}
        assert _infer_ref_target("Shop_ID", tables) == "Shop"

    def test_plural_match(self):
        tables = {"Shops", "Employee"}
        assert _infer_ref_target("Shop", tables) == "Shops"

    def test_singular_match(self):
        tables = {"Employee", "Work_Card"}
        assert _infer_ref_target("Employees", tables) == "Employee"

    def test_underscore_normalization(self):
        tables = {"Work_Card", "Employee"}
        assert _infer_ref_target("Work Card", tables) == "Work_Card"

    def test_space_normalization(self):
        tables = {"Work Card", "Employee"}
        assert _infer_ref_target("Work_Card", tables) == "Work Card"

    def test_partial_match(self):
        tables = {"Employee", "Work_Card", "Shops"}
        result = _infer_ref_target("EmployeeFilter", tables)
        assert result == "Employee"

    def test_no_match_returns_none(self):
        tables = {"Employee", "Work_Card"}
        assert _infer_ref_target("xyz", tables) is None

    def test_disambiguates_multiple_partial_matches(self):
        """P2: When 'Batch' matches both 'Batch_Recipes' and 'Batch_Requests',
        should pick shortest (most specific) or prefix match."""
        tables = {"Batch_Recipes", "Batch_Requests", "Employee"}
        result = _infer_ref_target("Batch ID", tables)
        # Should return something, not None
        assert result is not None
        assert result in ("Batch_Recipes", "Batch_Requests")

    def test_case_insensitive_with_normalization(self):
        tables = {"batch_requests", "batch_recipes"}
        result = _infer_ref_target("Batch ID", tables)
        assert result is not None

    def test_avoids_self_reference(self):
        tables = {"Employee", "Work_Card"}
        result = _infer_ref_target("Employee", tables, source_table="Employee")
        # Should not return "Employee" as that would be self-ref
        assert result != "Employee" or result is None


class TestGenerateCandidates:
    def test_basic_name(self):
        candidates = _generate_candidates("Employee")
        assert "Employee" in candidates

    def test_strip_related(self):
        candidates = _generate_candidates("Related Work_Card")
        assert "Work_Card" in candidates

    def test_strip_id_suffix(self):
        candidates = _generate_candidates("Shop_ID")
        assert "Shop" in candidates

    def test_strip_fk_prefix(self):
        candidates = _generate_candidates("FK_Employee")
        assert "Employee" in candidates
