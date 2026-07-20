#!/usr/bin/env python3
"""
Generate Kimi Code plugin manifests (.kimi-plugin/plugin.json) and the Kimi
marketplace catalogs (kimi-marketplace.json, kimi-marketplace.local.json) from
the Claude plugin metadata.

The repository is dual-format:
  - .claude-plugin/plugin.json  — Claude Code manifest (source of truth)
  - .kimi-plugin/plugin.json    — Kimi Code manifest (GENERATED — do not edit by hand)

Catalogs:
  - kimi-marketplace.json       — distributable catalog; sources are per-plugin zip
                                  URLs on the rolling `kimi-latest` GitHub release
                                  (published by .github/workflows/publish-kimi-plugins.yml)
  - kimi-marketplace.local.json — same entries with relative ./plugins/<name> sources,
                                  for use from a local clone

Usage:
  python3 scripts/generate-kimi-manifests.py           # regenerate everything
  python3 scripts/generate-kimi-manifests.py --check   # verify files are up to date (CI)

Re-run this script whenever a plugin's .claude-plugin/plugin.json, .mcp.json,
skills/, or commands/ change.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_URL = "https://github.com/UNCTAD-eRegistrations/plugin-marketplace"
AUTHOR = {"name": "UNCTAD Trade Facilitation Section"}

# Rolling release tag whose assets are the per-plugin zips referenced by
# kimi-marketplace.json. Published by .github/workflows/publish-kimi-plugins.yml.
KIMI_RELEASE_TAG = "kimi-latest"


def zip_url(name: str) -> str:
    return f"{REPO_URL}/releases/download/{KIMI_RELEASE_TAG}/{name}.zip"


# keywords shown in the Kimi /plugins UI (fallback: the Claude marketplace category).
KEYWORDS = {
    "bpa-mcp": ["mcp", "bpa", "eregistrations"],
    "ds-mcp": ["mcp", "monitoring", "eregistrations"],
    "gdb-mcp": ["mcp", "database", "eregistrations"],
    "graylog-mcp": ["mcp", "logs", "monitoring"],
    "keycloak-mcp": ["mcp", "iam", "keycloak"],
    "translations-mcp": ["mcp", "translations", "i18n"],
    "service-documentation": ["documentation", "manuals", "excel"],
    "devops": ["devops", "deployment", "migration"],
    "deploy": ["devops", "deployment", "coolify"],
    "handoff": ["productivity", "session", "handoff"],
    "share-service": ["productivity", "sharing", "publishing"],
    "service-design": ["design", "bpa", "backend"],
    "leaflets": ["documentation", "design", "leaflets"],
    "screens-first-design": ["design", "ux", "mockups"],
    "team-bus": ["workflow", "jira", "collaboration"],
}

# Plugins that are published for Claude Code but intentionally NOT ported to Kimi Code.
KIMI_EXCLUDED = {
    "ds-frontend": "not listed in the Claude marketplace either (work in progress)",
    "terminal-stats": "Claude Code statusline plugin — Kimi Code has no statusline hook",
}

# displayName overrides for the Kimi /plugins UI (fallback: Title Case of the id).
DISPLAY_NAMES = {
    "bpa-mcp": "BPA MCP",
    "ds-mcp": "DS MCP",
    "gdb-mcp": "GDB MCP",
    "graylog-mcp": "Graylog MCP",
    "keycloak-mcp": "Keycloak MCP",
    "translations-mcp": "Translations MCP",
    "service-documentation": "Service Documentation",
    "devops": "DevOps",
    "deploy": "Deploy",
    "handoff": "Handoff",
    "share-service": "Share Service",
    "service-design": "Service Design",
    "leaflets": "Leaflets",
    "screens-first-design": "Screens-First Design",
    "team-bus": "Team Bus",
}

# Appended by Kimi Code whenever a Skill from one of these plugins is loaded.
# Maps the Claude Code idioms used inside SKILL.md / commands/*.md bodies to
# Kimi Code equivalents (same idea as the superpowers Kimi port).
SKILL_INSTRUCTIONS = """Kimi Code tool mapping for UNCTAD eRegistrations plugins:

- MCP tool names are identical in Kimi Code: call `mcp__BPA__*`, `mcp__DS__*`, `mcp__GDB__*`, `mcp__Keycloak__*`, `mcp__Graylog__*`, and `mcp__Translations__*` exactly as written in the skill.
- Slash commands keep their `<plugin>:<command>` names (e.g. `/bpa-mcp:install`, `/bpa-mcp:login`).
- When a skill or command says to "restart Claude" (e.g. after installing an MCP server), run `/reload` or start a new session instead.
- When a skill uses the Task tool (`subagent_type: "general-purpose"`) to delegate data fetching or other work, use Kimi Code's `Agent` tool: `subagent_type: "coder"` for fetching/implementation work, `subagent_type: "explore"` for read-only exploration, `subagent_type: "plan"` for read-only planning. Do not pass `general-purpose` as `subagent_type`.
- When a skill refers to `TodoWrite`, use Kimi Code's `TodoList` tool.
- When a skill refers to the `Skill` tool, use Kimi Code's native `Skill` tool.
- When a skill asks the user a multiple-choice question, use Kimi Code's `AskUserQuestion` tool unless the session is in auto permission mode.
- `allowed-tools` frontmatter is Claude Code-specific and ignored by Kimi Code; Kimi enforces permissions through its own approval system. Proceed with the tools available to you."""


def display_name(plugin_id: str) -> str:
    return DISPLAY_NAMES.get(plugin_id, plugin_id.replace("-", " ").title())


def convert_mcp_servers(mcp_json_path: Path) -> dict:
    """Convert a Claude .mcp.json to the Kimi manifest mcpServers shape.

    Kimi infers stdio from the presence of `command`, so the Claude-only
    `"type": "stdio"` field is dropped. `env` entries using Claude's
    `${VAR:-default}` expansion syntax are dropped as well — Kimi does not
    document expansion and the child process inherits the shell environment
    anyway, so an exported variable still reaches the server.
    """
    data = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    servers = data.get("mcpServers", data)
    converted = {}
    for name, cfg in servers.items():
        cfg = {k: v for k, v in cfg.items() if k != "type"}
        env = cfg.get("env")
        if env and any("${" in str(v) for v in env.values()):
            del cfg["env"]
        converted[name] = cfg
    return converted


def build_manifest(plugin_dir: Path) -> dict:
    claude_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if not claude_json.exists():
        raise FileNotFoundError(f"{plugin_dir.name}: missing .claude-plugin/plugin.json")
    claude = json.loads(claude_json.read_text(encoding="utf-8"))

    manifest = {
        "name": claude["name"],
        "version": claude["version"],
        "description": claude["description"],
        "author": claude.get("author", AUTHOR),
        "homepage": REPO_URL,
        "skillInstructions": SKILL_INSTRUCTIONS,
        "interface": {
            "displayName": display_name(claude["name"]),
            "shortDescription": claude["description"].split(". ")[0].rstrip(".") + ".",
            "developerName": claude.get("author", AUTHOR)["name"],
            "websiteURL": REPO_URL,
        },
    }

    if (plugin_dir / "skills").is_dir():
        manifest["skills"] = "./skills/"
    if (plugin_dir / "commands").is_dir():
        manifest["commands"] = "./commands/"

    mcp_json = plugin_dir / ".mcp.json"
    if mcp_json.exists():
        manifest["mcpServers"] = convert_mcp_servers(mcp_json)

    # Stable key order for readable diffs.
    order = ["name", "version", "description", "author", "homepage",
             "skills", "commands", "mcpServers", "skillInstructions", "interface"]
    return {k: manifest[k] for k in order if k in manifest}


def render(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_or_check(path: Path, content: str, check: bool, changed: list) -> None:
    if check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            changed.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="only verify generated files are up to date")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    marketplace = json.loads(
        (root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    published = {p["name"]: p for p in marketplace["plugins"]}

    changed: list[str] = []
    remote_plugins = []
    local_plugins = []

    for name, pub in published.items():
        if name in KIMI_EXCLUDED:
            print(f"  - {name}: skipped ({KIMI_EXCLUDED[name]})")
            continue
        plugin_dir = root / "plugins" / name
        manifest = build_manifest(plugin_dir)
        out = plugin_dir / ".kimi-plugin" / "plugin.json"
        write_or_check(out, render(manifest), args.check, changed)
        entry = {
            "id": name,
            "displayName": manifest["interface"]["displayName"],
            "version": manifest["version"],
            "description": manifest["interface"]["shortDescription"],
            "homepage": REPO_URL,
            "keywords": KEYWORDS.get(name) or ([pub["category"]] if pub.get("category") else []),
        }
        if not entry["keywords"]:
            del entry["keywords"]
        # Remote catalog: per-plugin zips published by the
        # publish-kimi-plugins.yml workflow to the rolling KIMI_RELEASE_TAG release.
        remote_plugins.append({**entry, "source": zip_url(name)})
        # Local catalog: relative paths for use from a clone.
        local_plugins.append({**entry, "source": f"./plugins/{name}"})
        print(f"  ✓ {name}: .kimi-plugin/plugin.json")

    catalog = {"version": "2", "plugins": remote_plugins}
    write_or_check(root / "kimi-marketplace.json", render(catalog), args.check, changed)
    print(f"  ✓ kimi-marketplace.json ({len(remote_plugins)} plugins, zip URLs)")

    local_catalog = {"version": "2", "plugins": local_plugins}
    write_or_check(root / "kimi-marketplace.local.json", render(local_catalog),
                   args.check, changed)
    print(f"  ✓ kimi-marketplace.local.json ({len(local_plugins)} plugins, local paths)")

    if args.check:
        if changed:
            print("\n\033[31mOut of date:\033[0m " + ", ".join(changed))
            print("Run: python3 scripts/generate-kimi-manifests.py")
            return 1
        print("\n  \033[32m✓ All Kimi manifests up to date\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
