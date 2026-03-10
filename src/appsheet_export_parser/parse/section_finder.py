"""Auto-detect section boundaries in AppSheet documentation text.

Replaces hardcoded line numbers (e.g., i > 270000) with dynamic section detection.
AppSheet docs follow a consistent structure:
    1. Header / App info
    2. Schema sections (Table definitions with columns)
    3. Slices
    4. UX (Views, Format Rules)
    5. Behavior (Actions, Workflow Rules)
    6. Automation (Processes)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Section:
    """A detected section in the document."""

    name: str
    start_line: int
    end_line: int = -1

    @property
    def line_count(self) -> int:
        if self.end_line < 0:
            return 0
        return self.end_line - self.start_line


@dataclass
class DocumentSections:
    """All detected sections in the document."""

    header: Section | None = None
    schemas: Section | None = None
    slices: Section | None = None
    ux: Section | None = None
    behavior: Section | None = None
    automation: Section | None = None

    schema_blocks: list[tuple[int, str]] = field(default_factory=list)
    """(line_index, schema_name) for each Schema Name marker."""


# Major section markers — these are standalone lines in the AppSheet doc.
# Primary markers come first; alternates map to the same section.
# Some apps use "Actions" instead of "Behavior" and "Views" instead of "UX".
_SECTION_MARKERS = {
    "Slices": "slices",
    "UX": "ux",
    "Views": "ux",            # Alternate for UX section
    "Behavior": "behavior",
    "Actions": "behavior",    # Alternate for Behavior section
    "Automation": "automation",
}


def find_sections(lines: list[str]) -> DocumentSections:
    """Scan lines to find all major section boundaries.

    Uses the document's own structure markers rather than hardcoded positions.
    Handles three schema name formats from PDF extraction:

    1. Inline:  Schema Name Employee_Schema
    2. Bare:    Schema Name (alone), then Employee_Schema on next line
    3. Split:   Schema Name Process for Something (partial), then Table_Schema on next line
    """
    sections = DocumentSections()
    total = len(lines)

    # Track positions of major section markers
    marker_positions: list[tuple[int, str]] = []

    # Track seen schema names to deduplicate (same schema appears in multiple formats)
    seen_schemas: set[str] = set()

    i = 0
    while i < total:
        s = lines[i].strip()

        # Format 1: Inline — "Schema Name XXX_Schema" all on one line
        m = re.match(r"^Schema Name (\S.+_Schema)$", s)
        if m:
            schema_name = m.group(1)
            if schema_name not in seen_schemas:
                seen_schemas.add(schema_name)
                sections.schema_blocks.append((i, schema_name))
            i += 1
            continue

        # Format 2 & 3: Bare or partial "Schema Name" line
        if s == "Schema Name" or (
            s.startswith("Schema Name ") and not s.endswith("_Schema")
        ):
            partial = s[len("Schema Name"):].strip()  # empty for bare, partial for split
            schema_name = _resolve_schema_name(lines, i, partial, total)
            if schema_name and schema_name not in seen_schemas:
                seen_schemas.add(schema_name)
                sections.schema_blocks.append((i, schema_name))
            i += 1
            continue

        # Major section markers (only match standalone section headers)
        if s in _SECTION_MARKERS:
            if not lines[i].startswith(" ") and not lines[i].startswith("\t"):
                section_name = _SECTION_MARKERS[s]
                # Skip if we already have a marker for this section
                # (e.g., "Behavior" already found, skip "Actions")
                already_found = any(
                    name == section_name for _, name in marker_positions
                )
                if not already_found:
                    marker_positions.append((i, section_name))

        i += 1

    # Build schema section from first/last schema block
    if sections.schema_blocks:
        first_schema_line = sections.schema_blocks[0][0]
        sections.schemas = Section("schemas", first_schema_line)

    # Assign section boundaries from markers
    # Sort markers by position
    marker_positions.sort(key=lambda x: x[0])

    for i, (line_idx, section_name) in enumerate(marker_positions):
        section = Section(section_name, line_idx)

        # Set end of previous section
        if section_name == "slices" and sections.schemas:
            sections.schemas.end_line = line_idx
        elif i > 0:
            prev_name = marker_positions[i - 1][1]
            prev_section = getattr(sections, prev_name, None)
            if prev_section and prev_section.end_line < 0:
                prev_section.end_line = line_idx

        setattr(sections, section_name, section)

    # Set end_line for the last section
    if marker_positions:
        last_name = marker_positions[-1][1]
        last_section = getattr(sections, last_name, None)
        if last_section and last_section.end_line < 0:
            last_section.end_line = total

    # If schemas section has no end, use first marker or total
    if sections.schemas and sections.schemas.end_line < 0:
        if marker_positions:
            sections.schemas.end_line = marker_positions[0][0]
        else:
            sections.schemas.end_line = total

    return sections


def _resolve_schema_name(
    lines: list[str], start: int, partial: str, total: int,
) -> str | None:
    """Resolve a schema name from bare or split format.

    For bare format ("Schema Name" alone), the name is on the next non-blank line.
    For split format ("Schema Name Process for Something"), the rest is on the next line.

    Returns the full schema name (e.g., "Employee_Schema") or None if not found.
    """
    for j in range(start + 1, min(start + 5, total)):
        val = lines[j].strip()
        if not val:
            continue

        # Skip if we hit another marker
        if val in _SECTION_MARKERS or val == "Schema Name":
            break

        # Skip false positives (field names that appear right after Schema Name)
        if val in ("Visible?", "Column name", "Type", "Description"):
            break

        if partial:
            # Split format: combine partial + continuation
            full = f"{partial} {val}"
            if full.endswith("_Schema"):
                return full
            # Check if the continuation itself ends with _Schema
            if val.endswith("_Schema"):
                return f"{partial} {val}"
        else:
            # Bare format: the value IS the schema name
            if val.endswith("_Schema"):
                return val

        break

    return None
