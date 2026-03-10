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


# Major section markers — these are standalone lines in the AppSheet doc
_SECTION_MARKERS = {
    "Slices": "slices",
    "UX": "ux",
    "Behavior": "behavior",
    "Automation": "automation",
}


def find_sections(lines: list[str]) -> DocumentSections:
    """Scan lines to find all major section boundaries.

    Uses the document's own structure markers rather than hardcoded positions.
    """
    sections = DocumentSections()
    total = len(lines)

    # Track positions of major section markers
    marker_positions: list[tuple[int, str]] = []

    for i, line in enumerate(lines):
        s = line.strip()

        # Schema block markers: "Schema Name XXX_Schema"
        m = re.match(r"^Schema Name (\S.+_Schema)$", s)
        if m:
            sections.schema_blocks.append((i, m.group(1)))
            continue

        # Major section markers (only match standalone section headers)
        # These are typically on their own line, sometimes after schemas
        if s in _SECTION_MARKERS:
            # Verify it's a real section header, not content
            # Section headers are usually preceded by blank lines
            # and not indented
            if not line.startswith(" ") and not line.startswith("\t"):
                marker_positions.append((i, _SECTION_MARKERS[s]))

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
