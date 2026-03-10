"""Automation models — AppSheet automation processes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AutomationProcess(BaseModel):
    """An AppSheet automation process definition."""

    name: str
    table: str | None = None
    trigger: str | None = None
    steps: list[dict[str, Any]] | None = None
