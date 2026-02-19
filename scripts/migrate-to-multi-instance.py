#!/usr/bin/env python3
"""Migrate BPA MCP configs from multi-server to single-server multi-instance.

Old setup: one MCP server entry per country (BPA-nigeria, BPA-jamaica, ...)
New setup: one BPA server, instances registered via /bpa-setup command

What this script does:
  1. Finds all config files containing BPA-* server entries
  2. Shows a dry-run diff of what would be removed / added
  3. On confirmation: backs up each file, then applies the changes
  4. Prints next steps (reinstall plugin + run /bpa-setup)

Targets:
  - ./mcp.json (project-level, flat format)
  - ~/Library/Application Support/Claude/claude_desktop_config.json (macOS Claude Desktop)
  - ~/.config/Claude/claude_desktop_config.json (Linux Claude Desktop)

Usage:
    uv run scripts/migrate-to-multi-instance.py            # dry run
    uv run scripts/migrate-to-multi-instance.py --apply    # apply changes
    uv run scripts/migrate-to-multi-instance.py --project-only  # skip Claude Desktop
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# The single new server entry that replaces all BPA-* entries
NEW_SERVER_NAME = "BPA"
NEW_SERVER_ENTRY = {
    "type": "stdio",
    "command": "mcp-eregistrations-bpa",
}


def find_config_files(project_only: bool = False) -> list[Path]:
    """Return all existing config files to inspect."""
    candidates = []

    # Project-level flat .mcp.json
    project_mcp = Path(".mcp.json")
    if project_mcp.exists():
        candidates.append(project_mcp)

    if not project_only:
        # Claude Desktop — macOS
        macos_config = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        if macos_config.exists():
            candidates.append(macos_config)

        # Claude Desktop — Linux
        linux_config = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        if linux_config.exists():
            candidates.append(linux_config)

    return candidates


def is_flat_mcp_json(data: dict) -> bool:
    """Detect flat .mcp.json format (server_name → config at top level)."""
    return any(
        isinstance(v, dict) and "type" in v
        for v in data.values()
    )


def get_servers(data: dict) -> dict:
    """Extract the servers dict regardless of format."""
    if "mcpServers" in data:
        return data["mcpServers"]
    if is_flat_mcp_json(data):
        return data
    return {}


def set_servers(data: dict, servers: dict) -> dict:
    """Write back the servers dict, preserving format."""
    if "mcpServers" in data:
        data["mcpServers"] = servers
        return data
    # flat format: the data IS the servers dict
    return servers


def analyze(path: Path) -> tuple[list[str], bool]:
    """Return (list_of_bpa_star_keys, has_new_BPA_already)."""
    data = json.loads(path.read_text())
    servers = get_servers(data)
    old_keys = [k for k in servers if k.startswith("BPA-")]
    has_new = NEW_SERVER_NAME in servers
    return old_keys, has_new


def apply_migration(path: Path, dry_run: bool) -> None:
    """Remove BPA-* entries and add the single BPA entry."""
    data = json.loads(path.read_text())
    servers = get_servers(data)

    old_keys = [k for k in servers if k.startswith("BPA-")]
    has_new = NEW_SERVER_NAME in servers

    if not old_keys and has_new:
        print(f"  {path}: already migrated, nothing to do")
        return

    if not old_keys:
        print(f"  {path}: no BPA-* entries found, skipping")
        return

    print(f"\n  {path}")
    print(f"    Removing {len(old_keys)} old entries:")
    for k in sorted(old_keys):
        print(f"      - {k}")

    if not has_new:
        print(f"    Adding: + {NEW_SERVER_NAME}")
    else:
        print(f"    {NEW_SERVER_NAME} entry already present, skipping add")

    if dry_run:
        return

    # Backup
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".json.backup.{ts}")
    shutil.copy2(path, backup)
    print(f"    Backed up to: {backup.name}")

    # Apply
    for k in old_keys:
        del servers[k]
    if not has_new:
        servers[NEW_SERVER_NAME] = NEW_SERVER_ENTRY

    updated = set_servers(data, servers)
    path.write_text(json.dumps(updated, indent=2) + "\n")
    print(f"    Written: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry run)")
    parser.add_argument("--project-only", action="store_true", help="Only migrate ./mcp.json, skip Claude Desktop")
    args = parser.parse_args()

    dry_run = not args.apply

    if dry_run:
        print("=== DRY RUN — pass --apply to make changes ===\n")

    configs = find_config_files(project_only=args.project_only)

    if not configs:
        print("No config files found. Nothing to migrate.")
        sys.exit(0)

    # Scan phase
    needs_migration = []
    already_done = []
    for path in configs:
        old_keys, has_new = analyze(path)
        if old_keys:
            needs_migration.append((path, old_keys, has_new))
        elif has_new:
            already_done.append(path)

    if not needs_migration:
        if already_done:
            print("All configs already migrated.")
        else:
            print("No BPA-* entries found in any config file.")
        sys.exit(0)

    print(f"Found BPA-* entries in {len(needs_migration)} file(s):\n")
    for path, old_keys, has_new in needs_migration:
        apply_migration(path, dry_run=dry_run)

    print()

    if dry_run:
        print("Run with --apply to apply these changes.")
    else:
        print("Migration complete.\n")
        print("Next steps:")
        print("  1. Restart Claude Desktop (if it was open)")
        print("  2. In Claude Code, run: /bpa-setup")
        print("     (registers all instance profiles)")
        print("  3. Authenticate: /bpa-login <instance>")
        print("     e.g. /bpa-login jamaica nigeria lesotho2")


if __name__ == "__main__":
    main()
