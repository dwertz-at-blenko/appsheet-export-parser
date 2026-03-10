"""Cron-based sync service for AppSheet documentation.

Periodically fetches live AppSheet app documentation via URL, parses it,
and writes updated JSON output if changes are detected.

Config file: ~/.appsheet-parser/sync-config.yaml
Usage: python -m appsheet_export_parser.sync [--dry-run] [--config PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path.home() / ".appsheet-parser" / "sync-config.yaml"
DEFAULT_LOG_DIR = Path.home() / ".appsheet-parser" / "logs"


def load_sync_config(config_path: Path) -> dict[str, Any]:
    """Load sync configuration from YAML."""
    if not config_path.exists():
        raise FileNotFoundError(
            f"Sync config not found: {config_path}\n"
            f"Create it with apps, chrome_profile, and log_dir settings."
        )
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def file_hash(path: Path) -> str | None:
    """Get SHA-256 hash of a file, or None if it doesn't exist."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sync_app(
    app_name: str,
    app_id: str,
    output_path: Path,
    chrome_profile: str,
    app_config_path: str | None,
    dry_run: bool,
    logger: logging.Logger,
    alert_dir: Path | None = None,
) -> bool:
    """Sync a single app. Returns True if output was updated."""
    from .parser import parse_url

    logger.info(f"Syncing {app_name} (app_id={app_id})...")

    old_hash = file_hash(output_path)

    try:
        export = parse_url(
            app_id=app_id,
            output_path=None if dry_run else output_path,
            app_config_path=app_config_path,
            chrome_profile=chrome_profile,
            verbose=False,
        )
    except RuntimeError as e:
        error_msg = str(e)
        logger.error(f"  Failed to sync {app_name}: {error_msg}")

        # Check for auth failure
        if "auth" in error_msg.lower() or "cookie" in error_msg.lower() or "too short" in error_msg.lower():
            _alert_auth_expired(app_name, error_msg, logger, alert_dir)

        return False

    # Check summary
    meta = export.get("metadata", {})
    summary = meta.get("summary", {})
    logger.info(
        f"  Parsed: {summary.get('total_tables', 0)} tables, "
        f"{summary.get('total_columns', 0)} columns, "
        f"{summary.get('total_actions', 0)} actions, "
        f"{len(export.get('views', []))} views, "
        f"{len(export.get('format_rules', []))} format rules"
    )

    if dry_run:
        logger.info(f"  [DRY RUN] Would write to {output_path}")
        return False

    new_hash = file_hash(output_path)
    if old_hash == new_hash:
        logger.info(f"  No changes detected for {app_name}")
        return False

    logger.info(f"  Updated {output_path}")
    return True


def _alert_auth_expired(
    app_name: str,
    error_msg: str,
    logger: logging.Logger,
    alert_dir: Path | None = None,
) -> None:
    """Write auth expiry alert to alert directory (if configured)."""
    if alert_dir is None:
        logger.warning(f"  Auth may have expired for {app_name}: {error_msg}")
        return
    alert_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    alert_path = alert_dir / f"appsheet-auth-expired-{ts}.json"
    alert = {
        "type": "alert",
        "from": "appsheet-sync",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": "warning",
        "summary": f"AppSheet auth expired for {app_name}",
        "details": error_msg,
        "action_required": "Re-authenticate: navigate to appsheet.com and sign in with Google.",
    }
    alert_path.write_text(json.dumps(alert, indent=2))
    (alert_dir / "UNREAD").touch()
    logger.warning(f"  Auth alert written to {alert_path}")


def main() -> None:
    """Main entry point for sync service."""
    parser = argparse.ArgumentParser(description="AppSheet documentation sync service")
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH,
        help=f"Config file path (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse but don't write output files",
    )
    parser.add_argument(
        "--app", type=str, default=None,
        help="Sync only this app (by config key name)",
    )
    args = parser.parse_args()

    # Load config
    config = load_sync_config(args.config)
    apps = config.get("apps", {})
    chrome_profile = config.get("chrome_profile", "/tmp/chrome-appsheet")
    alert_dir_str = config.get("alert_dir")
    alert_dir = Path(alert_dir_str) if alert_dir_str else None
    log_dir = Path(config.get("log_dir", str(DEFAULT_LOG_DIR)))

    # Setup logging
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "sync.log"),
        ],
    )
    logger = logging.getLogger("appsheet-sync")

    if not apps:
        logger.error("No apps configured in sync config")
        sys.exit(1)

    # Filter to single app if requested
    if args.app:
        if args.app not in apps:
            logger.error(f"App '{args.app}' not found in config. Available: {list(apps.keys())}")
            sys.exit(1)
        apps = {args.app: apps[args.app]}

    logger.info(f"Starting sync for {len(apps)} app(s)...")
    updated = 0
    failed = 0

    for app_name, app_cfg in apps.items():
        app_id = app_cfg.get("app_id")
        output = Path(app_cfg.get("output", f"{app_name}-parsed.json"))
        app_config = app_cfg.get("config")

        if not app_id:
            logger.warning(f"  Skipping {app_name}: no app_id configured")
            continue

        try:
            if sync_app(app_name, app_id, output, chrome_profile, app_config, args.dry_run, logger, alert_dir):
                updated += 1
        except Exception as e:
            logger.error(f"  Unexpected error syncing {app_name}: {e}")
            failed += 1

    logger.info(f"Sync complete: {updated} updated, {failed} failed, {len(apps) - updated - failed} unchanged")


if __name__ == "__main__":
    main()
