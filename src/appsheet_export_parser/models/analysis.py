"""Analysis models — Relationships, Computed Fields, Enums."""

from __future__ import annotations

from pydantic import BaseModel


class Relationship(BaseModel):
    """A foreign key (Ref) relationship between tables."""

    from_table: str
    from_column: str
    to_table: str
    referenced_type: str | None = None


class ComputedField(BaseModel):
    """A column with a formula or computed value."""

    table: str
    column: str
    type: str = "Unknown"
    app_formula: str | None = None
    initial_value: str | None = None
    spreadsheet_formula: str | None = None
    valid_if: str | None = None
    show_if: str | None = None
    required_if: str | None = None
    editable_if: str | None = None


class EnumField(BaseModel):
    """A column with enumerated values."""

    table: str
    column: str
    type: str  # "Enum" or "EnumList"
    values: list[str] | str
