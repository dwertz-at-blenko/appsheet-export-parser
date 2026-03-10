"""Behavior models — Actions, Slices, Workflow Rules."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Action(BaseModel):
    """An AppSheet action definition."""

    name: str
    table: str | None = None
    action_type: str | None = None  # "Do this" field value
    bulk: bool = False
    modifies_data: bool = False
    needs_confirmation: bool = False
    prominence: str | None = None
    condition: str | None = None
    visible: str | None = None
    order: int | None = None
    attach_to_column: str | None = None
    to_value: str | None = None
    set_columns: str | None = None
    confirmation_message: str | None = None
    properties: dict[str, Any] | None = None
    properties_raw: str | None = None


class Slice(BaseModel):
    """An AppSheet slice definition."""

    name: str
    source_table: str | None = None
    filter: str | None = None
    columns: str | None = None


class WorkflowRule(BaseModel):
    """An AppSheet workflow rule (legacy — most apps have 0)."""

    name: str
    table: str | None = None
    condition: str | None = None
    action: str | None = None
