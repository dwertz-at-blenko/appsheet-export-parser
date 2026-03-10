"""Tests for analyze/relationships.py — Ref extraction and inference."""

from appsheet_export_parser.analyze.relationships import (
    _generate_candidates,
    _infer_ref_target,
    extract_relationships,
)


class TestExtractRelationships:
    def test_extracts_ref_with_target(self):
        schemas = {
            "Order": [
                {"name": "Customer", "type": "Ref", "referenced_table": "Customer"},
            ],
            "Customer": [
                {"name": "Name", "type": "Text"},
            ],
        }
        rels = extract_relationships(schemas)
        assert len(rels) == 1
        assert rels[0].from_table == "Order"
        assert rels[0].from_column == "Customer"
        assert rels[0].to_table == "Customer"

    def test_infers_missing_target(self):
        schemas = {
            "Order": [
                {"name": "Customer", "type": "Ref"},  # no referenced_table
            ],
            "Customer": [
                {"name": "Name", "type": "Text"},
            ],
        }
        rels = extract_relationships(schemas)
        assert len(rels) == 1
        assert rels[0].to_table == "Customer"

    def test_skips_non_ref_columns(self):
        schemas = {
            "Order": [
                {"name": "Name", "type": "Text"},
                {"name": "Count", "type": "Number"},
            ],
        }
        rels = extract_relationships(schemas)
        assert len(rels) == 0

    def test_handles_broken_target(self):
        schemas = {
            "Order": [
                {"name": "Store_ID", "type": "Ref", "referenced_table": "NonExistent"},
            ],
            "Stores": [
                {"name": "Name", "type": "Text"},
            ],
        }
        rels = extract_relationships(schemas)
        # Should infer "Stores" from "Store_ID" via _ID stripping + plural
        assert len(rels) == 1
        assert rels[0].to_table == "Stores"


class TestInferRefTarget:
    def test_direct_match(self):
        tables = {"Employee", "Order", "Stores"}
        assert _infer_ref_target("Employee", tables) == "Employee"

    def test_strip_related_prefix(self):
        tables = {"Order", "Employee"}
        assert _infer_ref_target("Related Order", tables) == "Order"

    def test_strip_id_suffix(self):
        tables = {"Store", "Employee"}
        assert _infer_ref_target("Store_ID", tables) == "Store"

    def test_plural_match(self):
        tables = {"Stores", "Employee"}
        assert _infer_ref_target("Store", tables) == "Stores"

    def test_singular_match(self):
        tables = {"Employee", "Order"}
        assert _infer_ref_target("Employees", tables) == "Employee"

    def test_underscore_normalization(self):
        tables = {"Line_Item", "Employee"}
        assert _infer_ref_target("Line Item", tables) == "Line_Item"

    def test_space_normalization(self):
        tables = {"Line Item", "Employee"}
        assert _infer_ref_target("Line_Item", tables) == "Line Item"

    def test_partial_match(self):
        tables = {"Employee", "Order", "Stores"}
        result = _infer_ref_target("EmployeeFilter", tables)
        assert result == "Employee"

    def test_no_match_returns_none(self):
        tables = {"Employee", "Order"}
        assert _infer_ref_target("xyz", tables) is None

    def test_disambiguates_multiple_partial_matches(self):
        """When 'Item' matches both 'Item_Details' and 'Item_History',
        should pick shortest (most specific) or prefix match."""
        tables = {"Item_Details", "Item_History", "Employee"}
        result = _infer_ref_target("Item ID", tables)
        # Should return something, not None
        assert result is not None
        assert result in ("Item_Details", "Item_History")

    def test_case_insensitive_with_normalization(self):
        tables = {"item_details", "item_history"}
        result = _infer_ref_target("Item ID", tables)
        assert result is not None

    def test_avoids_self_reference(self):
        tables = {"Employee", "Order"}
        result = _infer_ref_target("Employee", tables, source_table="Employee")
        # Should not return "Employee" as that would be self-ref
        assert result != "Employee" or result is None


class TestGenerateCandidates:
    def test_basic_name(self):
        candidates = _generate_candidates("Employee")
        assert "Employee" in candidates

    def test_strip_related(self):
        candidates = _generate_candidates("Related Order")
        assert "Order" in candidates

    def test_strip_id_suffix(self):
        candidates = _generate_candidates("Store_ID")
        assert "Store" in candidates

    def test_strip_fk_prefix(self):
        candidates = _generate_candidates("FK_Employee")
        assert "Employee" in candidates
