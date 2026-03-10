"""Optional domain grouping and table classification from YAML config."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DomainInfo:
    """A domain group for ERD color-coding."""

    name: str
    color: str
    fill: str
    tables: list[str]


@dataclass
class TableClassification:
    """Classification of tables into core, process, and skip groups."""

    core: list[str]
    process: list[str]
    skip: list[str]


def load_domains(config_path: str | Path) -> list[DomainInfo]:
    """Load domain groupings from a YAML config file.

    See configs/example-domains.yaml for the expected format.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        return []

    with open(config_path) as f:
        data = yaml.safe_load(f)

    domains: list[DomainInfo] = []
    for name, info in data.get("domains", {}).items():
        domains.append(DomainInfo(
            name=name,
            color=info.get("color", "#888888"),
            fill=info.get("fill", "#FAFAFA"),
            tables=info.get("tables", []),
        ))

    return domains


def load_table_classification(
    config_path: str | Path,
    all_table_names: list[str],
) -> TableClassification:
    """Load table classification from a YAML config file.

    Supports wildcard patterns (e.g., "Process for *", "* Output").
    Tables not matching any pattern default to 'core'.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        return TableClassification(core=list(all_table_names), process=[], skip=[])

    with open(config_path) as f:
        data = yaml.safe_load(f)

    classification = data.get("table_classification", {})

    core_patterns = classification.get("core", [])
    process_patterns = classification.get("process", [])
    skip_patterns = classification.get("skip", [])

    core: list[str] = []
    process: list[str] = []
    skip: list[str] = []

    for table in all_table_names:
        if _matches_any(table, skip_patterns):
            skip.append(table)
        elif _matches_any(table, process_patterns):
            process.append(table)
        elif _matches_any(table, core_patterns) or not core_patterns:
            core.append(table)
        else:
            core.append(table)  # Default to core

    return TableClassification(core=core, process=process, skip=skip)


def classify_tables_auto(
    table_names: list[str],
) -> TableClassification:
    """Auto-classify tables without a config file.

    Uses heuristic rules:
    - Tables with "Process" or "Output" in the name → process
    - Tables named "Home", "Buttons" → skip
    - Everything else → core
    """
    core: list[str] = []
    process: list[str] = []
    skip: list[str] = []

    for name in table_names:
        if "Process" in name or name.endswith("Output") or name.endswith("Output 2"):
            process.append(name)
        elif name in ("Home", "Buttons"):
            skip.append(name)
        else:
            core.append(name)

    return TableClassification(core=core, process=process, skip=skip)


def _matches_any(name: str, patterns: list[str]) -> bool:
    """Check if a table name matches any of the given patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        if name == pattern:
            return True
    return False
