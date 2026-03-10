"""Parse format rules from the UX section of AppSheet documentation.

Format rules appear after a "Format Rules" header within the UX section.
Each rule is marked by "Rule name <name>" (inline) or "Rule name" (bare,
name on next line). The PDF often includes both formats for the same rule.

Structure in text:
    Rule name Older than 1 hour
    Rule name
    Older than 1 hour
    Format these columns and actions
    <column list>
    For this data    <table>
    If this condition is true    <formula>
    Rule order    <N>
    Is this format rule disabled?    <Yes/No>
    <JSON style blob>
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..extract.cleaner import clean_lines
from .section_finder import DocumentSections


_FORMAT_RULE_FIELDS = frozenset({
    "For this data",
    "If this condition is true",
    "Rule order",
    "Is this format rule disabled?",
    "Like this",
    "Format these columns and",
    "Visible?",
    "Rule name",
})


def parse_format_rules(
    lines: list[str],
    sections: DocumentSections,
) -> list[dict[str, Any]]:
    """Parse all format rules from the UX section."""
    rules: list[dict[str, Any]] = []

    if not sections.ux:
        return rules

    start = sections.ux.start_line
    end = sections.ux.end_line

    block = lines[start:end]
    cleaned = clean_lines(block)
    clean = [line.strip() for line in cleaned if line.strip()]

    # Find the "Format Rules" header
    fr_start = None
    for i, line in enumerate(clean):
        if line == "Format Rules":
            fr_start = i + 1
            break

    if fr_start is None:
        return rules

    fr_lines = clean[fr_start:]

    # Find all rule starts by "Rule name" markers, deduplicating
    rule_starts: list[tuple[int, str]] = []
    seen_names: set[str] = set()
    i = 0
    while i < len(fr_lines):
        line = fr_lines[i]

        # Inline: "Rule name Older than 1 hour"
        m = re.match(r"^Rule name (.+)$", line)
        if m:
            name = m.group(1).strip()
            if name and name not in seen_names:
                seen_names.add(name)
                rule_starts.append((i, name))
            i += 1
            continue

        # Bare: "Rule name" alone, name on next line
        if line == "Rule name" and i + 1 < len(fr_lines):
            name = fr_lines[i + 1].strip()
            if name and name not in _FORMAT_RULE_FIELDS and name not in seen_names:
                seen_names.add(name)
                rule_starts.append((i, name))
            i += 1
            continue

        i += 1

    # Parse each rule block
    for idx, (start_i, name) in enumerate(rule_starts):
        if idx + 1 < len(rule_starts):
            end_i = rule_starts[idx + 1][0]
        else:
            end_i = len(fr_lines)

        rule_block = fr_lines[start_i:end_i]
        rule = _parse_single_format_rule(rule_block, name)
        rules.append(rule)

    return rules


def _parse_single_format_rule(
    cleaned_lines: list[str],
    rule_name: str,
) -> dict[str, Any]:
    """Parse a single format rule block."""
    rule: dict[str, Any] = {"name": rule_name}

    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]

        # Skip "Rule name" header lines (already parsed)
        if line.startswith("Rule name"):
            i += 1
            # Skip the bare name line that follows
            if i < len(cleaned_lines) and cleaned_lines[i] == rule_name:
                i += 1
            continue

        # Tab-delimited fields
        if "\t" in line:
            key, _, val = line.partition("\t")
            key = key.strip()
            val = val.strip()
            if key == "For this data":
                rule["table"] = val
            elif key == "If this condition is true":
                rule["condition"] = val
            elif key == "Rule order":
                try:
                    rule["order"] = int(val)
                except ValueError:
                    pass
            elif key == "Is this format rule disabled?":
                rule["disabled"] = val.strip().lower() in ("yes", "true")
            i += 1
            continue

        # Line-separated fields
        if line == "For this data" and i + 1 < len(cleaned_lines):
            rule["table"] = cleaned_lines[i + 1]
            i += 2
        elif line == "If this condition is true" and i + 1 < len(cleaned_lines):
            # Collect multi-line condition
            parts: list[str] = []
            j = i + 1
            while j < len(cleaned_lines) and cleaned_lines[j] not in _FORMAT_RULE_FIELDS:
                parts.append(cleaned_lines[j])
                j += 1
            rule["condition"] = " ".join(parts)
            i = j
        elif line == "Rule order" and i + 1 < len(cleaned_lines):
            try:
                rule["order"] = int(cleaned_lines[i + 1])
            except ValueError:
                pass
            i += 2
        elif line == "Is this format rule disabled?" and i + 1 < len(cleaned_lines):
            rule["disabled"] = cleaned_lines[i + 1].strip().lower() in ("yes", "true")
            i += 2
        elif line == "Format these columns and" or line == "actions":
            i += 1
        elif line.startswith("{") and "textColor" in line:
            # JSON style blob — may span multiple lines
            json_parts: list[str] = [line]
            j = i + 1
            while j < len(cleaned_lines):
                next_line = cleaned_lines[j]
                if next_line in _FORMAT_RULE_FIELDS or next_line.startswith("Rule name"):
                    break
                json_parts.append(next_line)
                j += 1
            raw = "".join(json_parts)
            try:
                rule["style"] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                rule["style_raw"] = raw
            i = j
        else:
            i += 1

    return rule
