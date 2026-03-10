"""Config loading for domain classification and app-specific settings.

Looks for config files in this order:
1. Explicit path (passed by CLI or skill)
2. Working directory: ./configs/*.yaml
3. No config: fully generic mode
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def find_config(
    explicit_path: str | Path | None = None,
    config_name: str = "",
    search_dir: str | Path | None = None,
) -> Path | None:
    """Find a config file using the standard search order.

    Args:
        explicit_path: Direct path to config file.
        config_name: Config filename to search for (e.g., "domains.yaml").
        search_dir: Directory to search in (defaults to cwd).
    """
    # 1. Explicit path
    if explicit_path:
        path = Path(explicit_path)
        if path.exists():
            return path

    if not config_name:
        return None

    # 2. Working directory configs/
    search = Path(search_dir) if search_dir else Path.cwd()
    candidates = [
        search / "configs" / config_name,
        search / config_name,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}
