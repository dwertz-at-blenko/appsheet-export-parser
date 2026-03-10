"""Top-level app export models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .analysis import ComputedField, EnumField, Relationship
from .behavior import Action, Slice, WorkflowRule
from .schema import Column, Table
from .ux import FormatRule, View


SCHEMA_VERSION = "1.0.0"


class OfficialCounts(BaseModel):
    """Official summary counts from the AppSheet doc header."""

    tables: int = 0
    columns: int = 0
    slices: int = 0
    actions: int = 0
    views: int = 0
    format_rules: int = 0
    workflow_rules: int = 0


class AppSummary(BaseModel):
    """Computed summary statistics from parsed data."""

    total_tables: int = 0
    core_tables: int = 0
    process_tables: int = 0
    total_columns: int = 0
    total_actions: int = 0
    total_slices: int = 0
    total_relationships: int = 0
    total_computed_fields: int = 0
    total_enum_fields: int = 0


class AppMetadata(BaseModel):
    """Metadata about the parsed AppSheet export."""

    app_name: str = ""
    version: str = ""
    stable_version: str = ""
    generated: str = ""
    parser_version: str = ""
    source_file: str = ""
    source_pages: int = 0
    summary: AppSummary = Field(default_factory=AppSummary)
    official_counts: OfficialCounts | None = None
    sections_captured: list[str] = Field(default_factory=list)


class AppExport(BaseModel):
    """Complete parsed AppSheet export — the top-level output model."""

    schema_version: str = SCHEMA_VERSION
    metadata: AppMetadata = Field(default_factory=AppMetadata)
    tables: list[Table] = Field(default_factory=list)
    schemas: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    relationships: list[Relationship] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    slices: list[Slice] = Field(default_factory=list)
    views: list[View] = Field(default_factory=list)
    format_rules: list[FormatRule] = Field(default_factory=list)
    computed_fields: list[ComputedField] = Field(default_factory=list)
    enum_fields: list[EnumField] = Field(default_factory=list)
    core_table_names: list[str] = Field(default_factory=list)
    process_table_names: list[str] = Field(default_factory=list)
