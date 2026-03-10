"""Extract computed/formula fields from parsed schemas."""

from __future__ import annotations

from typing import Any

from ..models.analysis import ComputedField


# Formula field keys to check
_FORMULA_KEYS = (
    "app_formula",
    "initial_value",
    "spreadsheet_formula",
    "valid_if",
    "show_if",
    "required_if",
    "editable_if",
)


def extract_computed_fields(
    schemas: dict[str, list[dict[str, Any]]],
) -> list[ComputedField]:
    """Extract all columns that have formulas or computed values.

    A field is "computed" if it has any of: app_formula, initial_value,
    spreadsheet_formula, valid_if, show_if, required_if, editable_if.
    """
    computed: list[ComputedField] = []

    for table, cols in schemas.items():
        for col in cols:
            formulas: dict[str, str] = {}
            for key in _FORMULA_KEYS:
                val = col.get(key)
                if val:
                    formulas[key] = val

            if formulas:
                computed.append(ComputedField(
                    table=table,
                    column=col.get("name", ""),
                    type=col.get("type", "Unknown"),
                    **formulas,
                ))

    return computed
