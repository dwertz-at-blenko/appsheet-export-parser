"""Parse actions from the Behavior section of AppSheet documentation.

Refactored from parse_berp_v2.py — uses section_finder boundaries
instead of hardcoded `i > 270000`.
"""

from __future__ import annotations

import re
from typing import Any

from ..extract.cleaner import clean_lines
from .field_parser import ACTION_FIELDS, parse_type_qualifier
from .section_finder import DocumentSections


def parse_actions(
    lines: list[str],
    sections: DocumentSections,
) -> list[dict[str, Any]]:
    """Parse all actions from the Behavior section.

    Uses section boundaries from section_finder to locate the action region,
    replacing hardcoded line number thresholds.
    """
    actions: list[dict[str, Any]] = []

    if not sections.behavior:
        return actions

    start = sections.behavior.start_line
    end = sections.behavior.end_line

    # Find all action markers within the behavior section
    action_starts: list[tuple[int, str]] = []
    for i in range(start, end):
        m = re.match(r"^Action name (.+)$", lines[i].strip())
        if m:
            action_starts.append((i, m.group(1).strip()))

    # Deduplicate (AppSheet repeats "Action name X" then "Action name\n\nX")
    seen: dict[str, int] = {}
    for start_i, name in action_starts:
        if name not in seen:
            seen[name] = start_i

    # Parse each action block
    sorted_actions = sorted(seen.items(), key=lambda x: x[1])

    for idx, (name, start_i) in enumerate(sorted_actions):
        if idx + 1 < len(sorted_actions):
            end_i = sorted_actions[idx + 1][1]
        else:
            end_i = min(start_i + 200, end)

        block = lines[start_i:end_i]
        cleaned = clean_lines(block)
        action = _parse_single_action(cleaned, name)
        actions.append(action)

    return actions


def _parse_single_action(
    cleaned_lines: list[str],
    action_name: str,
) -> dict[str, Any]:
    """Parse a single action block."""
    action: dict[str, Any] = {"name": action_name}
    clean = [line.strip() for line in cleaned_lines if line.strip()]

    i = 0
    while i < len(clean):
        field = clean[i]

        if field == "Action name":
            i += 2
            continue

        if field == "Bulk action?" and i + 1 < len(clean):
            action["bulk"] = clean[i + 1] == "Yes"
            i += 2
        elif field == "Modifies data?" and i + 1 < len(clean):
            action["modifies_data"] = clean[i + 1] == "Yes"
            i += 2
        elif field == "Needs confirmation?" and i + 1 < len(clean):
            action["needs_confirmation"] = clean[i + 1] == "Yes"
            i += 2
        elif field == "Prominence" and i + 1 < len(clean):
            action["prominence"] = clean[i + 1]
            i += 2
        elif field == "Do this" and i + 1 < len(clean):
            action["action_type"] = clean[i + 1]
            i += 2
        elif field == "For a record of this table" and i + 1 < len(clean):
            j = i + 1
            while j < len(clean) and clean[j].endswith("?"):
                j += 1
            if j < len(clean):
                action["table"] = clean[j]
            i = j + 1
        elif field.startswith("Only if this condition is true"):
            cond = field.replace("Only if this condition is true", "").strip()
            if cond:
                action["condition"] = cond
            i += 1
        elif field == "Attach to column" and i + 1 < len(clean):
            action["attach_to_column"] = clean[i + 1]
            i += 2
        elif field == "Action order" and i + 1 < len(clean):
            try:
                action["order"] = int(clean[i + 1])
            except ValueError:
                pass
            i += 2
        elif field == "Visible?" and i + 1 < len(clean):
            action["visible"] = clean[i + 1]
            i += 2
        elif field == "To this value" and i + 1 < len(clean):
            val_parts: list[str] = []
            j = i + 1
            while j < len(clean) and clean[j] not in ACTION_FIELDS:
                val_parts.append(clean[j])
                j += 1
            action["to_value"] = " ".join(val_parts)
            i = j
        elif field == "With these properties" and i + 1 < len(clean):
            json_parts: list[str] = []
            j = i + 1
            while j < len(clean) and clean[j] not in ACTION_FIELDS:
                json_parts.append(clean[j])
                j += 1
            tq = parse_type_qualifier(json_parts)
            if tq:
                action["properties"] = tq
            else:
                action["properties_raw"] = "".join(json_parts)
            i = j
        elif field.startswith("Set these columns"):
            val_parts = []
            j = i + 1
            while j < len(clean) and clean[j] not in ACTION_FIELDS:
                val_parts.append(clean[j])
                j += 1
            if val_parts:
                action["set_columns"] = " ".join(val_parts)
            i = j
        elif field == "Confirmation message" and i + 1 < len(clean):
            action["confirmation_message"] = clean[i + 1]
            i += 2
        else:
            i += 1

    return action
