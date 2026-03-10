"""Extract Enum and EnumList fields from parsed schemas."""

from __future__ import annotations

from typing import Any

from ..models.analysis import EnumField


def extract_enum_fields(
    schemas: dict[str, list[dict[str, Any]]],
) -> list[EnumField]:
    """Extract all Enum/EnumList fields with their allowed values."""
    enums: list[EnumField] = []

    for table, cols in schemas.items():
        for col in cols:
            if col.get("type") in ("Enum", "EnumList") and col.get("enum_values"):
                enums.append(EnumField(
                    table=table,
                    column=col.get("name", ""),
                    type=col["type"],
                    values=col["enum_values"],
                ))

    return enums
