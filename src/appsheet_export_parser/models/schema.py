"""Schema models — Tables and Columns."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TypeQualifier(BaseModel):
    """Parsed Type Qualifier JSON from AppSheet column definitions."""

    referenced_table_name: str | None = Field(None, alias="ReferencedTableName")
    referenced_type: str | None = Field(None, alias="ReferencedType")
    valid_if: str | None = Field(None, alias="Valid_If")
    show_if: str | None = Field(None, alias="Show_If")
    required_if: str | None = Field(None, alias="Required_If")
    editable_if: str | None = Field(None, alias="Editable_If")
    enum_values: list[str] | str | None = Field(None, alias="EnumValues")
    items: list[str] | str | None = Field(None, alias="Items")
    max_value: float | str | None = Field(None, alias="MaxValue")
    min_value: float | str | None = Field(None, alias="MinValue")
    max_length: int | None = Field(None, alias="MaxLength")
    min_length: int | None = Field(None, alias="MinLength")

    model_config = {"populate_by_name": True}


class Column(BaseModel):
    """A single column in an AppSheet table schema."""

    name: str
    type: str = "Unknown"
    visible: str | None = None
    description: str | None = None
    display_name: str | None = None
    read_only: bool = False
    hidden: bool = False
    is_label: bool = False
    is_key: bool = False
    part_of_key: bool = False
    system_defined: bool = False
    virtual: bool = False
    searchable: bool = False
    scannable: bool = False
    sensitive: bool = False
    reset_on_edit: bool = False

    # Formulas
    app_formula: str | None = None
    initial_value: str | None = None
    spreadsheet_formula: str | None = None

    # Ref details (extracted from Type Qualifier)
    referenced_table: str | None = None
    referenced_type: str | None = None

    # Constraints (extracted from Type Qualifier)
    valid_if: str | None = None
    show_if: str | None = None
    required_if: str | None = None
    editable_if: str | None = None

    # Enum values
    enum_values: list[str] | str | None = None
    items: list[str] | str | None = None

    # Bounds
    max_value: float | str | None = None
    min_value: float | str | None = None
    max_length: int | None = None
    min_length: int | None = None


class Table(BaseModel):
    """An AppSheet table with its columns."""

    name: str
    columns: list[Column] = Field(default_factory=list)
    column_count: int = 0
    is_process_table: bool = False
    is_ui_only: bool = False
