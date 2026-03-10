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

    # Find all action markers within the behavior section.
    # Each "Action name X" line is a separate action instance — the same
    # action name appears once per table it's attached to. We keep all of them.
    action_starts: list[tuple[int, str]] = []
    for i in range(start, end):
        m = re.match(r"^Action name (.+)$", lines[i].strip())
        if m:
            action_starts.append((i, m.group(1).strip()))

    # Parse each action block (no deduplication — cross-table instances are distinct)
    for idx, (start_i, name) in enumerate(action_starts):
        if idx + 1 < len(action_starts):
            end_i = action_starts[idx + 1][0]
        else:
            end_i = min(start_i + 200, end)

        block = lines[start_i:end_i]
        cleaned = clean_lines(block)
        action = _parse_single_action(cleaned, name)
        actions.append(action)

    return actions


# Prefixes handled via startswith() in the main loop but absent from ACTION_FIELDS.
_EXTRA_PREFIXES = ("Only if this condition is true",)


def _is_field_boundary(line: str) -> bool:
    """Return True if line is a recognized action field boundary.

    Checks exact match first, then startswith for fields whose PDF
    extraction may merge the label and value on a single line
    (e.g. ``"Disable automatic updates? No"``).
    """
    if line in ACTION_FIELDS:
        return True
    # Some fields appear merged with their value on one line in the PDF.
    # Check startswith for every known field plus extra prefixes that the
    # main loop handles via startswith but that aren't in ACTION_FIELDS.
    return any(line.startswith(f) for f in ACTION_FIELDS) or any(
        line.startswith(p) for p in _EXTRA_PREFIXES
    )


def _parse_single_action(
    cleaned_lines: list[str],
    action_name: str,
) -> dict[str, Any]:
    """Parse a single action block."""
    action: dict[str, Any] = {"name": action_name}
    clean = [line.strip() for line in cleaned_lines if line.strip()]

    orphan_lines: list[str] = []

    i = 0
    while i < len(clean):
        field = clean[i]

        # Clear orphans when hitting a recognized field that won't consume them
        is_orphan_consumer = (
            field == "With these properties"
            or field.startswith("Only if this condition is true")
        )
        if not is_orphan_consumer and (_is_field_boundary(field) or field == "Action name"):
            orphan_lines.clear()

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
            val_parts: list[str] = []
            j = i + 1
            while j < len(clean) and not _is_field_boundary(clean[j]):
                val_parts.append(clean[j])
                j += 1
            action["action_type"] = " ".join(val_parts)
            i = j
        elif field == "For a record of this table" and i + 1 < len(clean):
            j = i + 1
            table_name = None
            while j < len(clean) and not _is_field_boundary(clean[j]):
                line = clean[j]
                # Skip question fragments: "Does this action apply to all rows?"
                # may span multiple lines in the PDF
                if not (line.endswith("?") or "Does this" in line or "action apply" in line):
                    table_name = line
                    j += 1
                    break
                j += 1
            if table_name:
                action["table"] = table_name
            i = j
        elif field.startswith("Only if this condition is true"):
            cond_parts: list[str] = list(orphan_lines)  # Prepend page-break fragments
            orphan_lines.clear()
            inline = field.replace("Only if this condition is true", "").strip()
            if inline:
                cond_parts.append(inline)
            # Collect continuation lines
            j = i + 1
            while j < len(clean) and not _is_field_boundary(clean[j]):
                cond_parts.append(clean[j])
                j += 1
            if cond_parts:
                action["condition"] = " ".join(cond_parts)
            i = j
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
            while j < len(clean) and not _is_field_boundary(clean[j]):
                val_parts.append(clean[j])
                j += 1
            action["to_value"] = " ".join(val_parts)
            i = j
        elif field == "With these properties" and i + 1 < len(clean):
            json_parts: list[str] = list(orphan_lines)  # Prepend page-break fragments
            orphan_lines.clear()
            j = i + 1
            while j < len(clean) and not _is_field_boundary(clean[j]):
                json_parts.append(clean[j])
                j += 1
            tq = parse_type_qualifier(json_parts)
            if tq:
                action["properties"] = tq
            else:
                action["properties_raw"] = " ".join(json_parts)
            i = j
        elif field.startswith("Set these columns"):
            val_parts = []
            j = i + 1
            while j < len(clean) and not _is_field_boundary(clean[j]):
                val_parts.append(clean[j])
                j += 1
            if val_parts:
                action["set_columns"] = " ".join(val_parts)
            i = j
        elif field == "Confirmation message" and i + 1 < len(clean):
            action["confirmation_message"] = clean[i + 1]
            i += 2
        else:
            orphan_lines.append(field)
            i += 1

    return action
