"""UX models — Views and Format Rules."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class View(BaseModel):
    """An AppSheet view definition."""

    name: str
    type: str | None = None
    table: str | None = None
    config: dict[str, Any] | None = None


class FormatRule(BaseModel):
    """An AppSheet format rule."""

    name: str
    table: str | None = None
    condition: str | None = None
    style: dict[str, Any] | None = None
