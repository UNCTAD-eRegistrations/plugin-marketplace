#!/usr/bin/env python3
"""
Validate plugin file quality before commit.

Checks:
  - plugin.json     : valid JSON, required fields, name matches directory
  - marketplace.json: valid JSON
  - .kimi-plugin/plugin.json: valid JSON, name matches directory, declared
    skills/commands/mcpServers paths stay inside the plugin
  - kimi-marketplace*.json: valid JSON, every local source exists
  - SKILL.md        : frontmatter has name, description, allowed-tools, metadata.version/version-date
  - commands/*.md   : frontmatter has description, allowed-tools

Usage:
  python3 scripts/validate-plugins.py                  # validate all plugin files
  python3 scripts/validate-plugins.py file1 file2 ...  # validate specific files
"""

import json
import re
import sys
from pathlib import Path


# ── Frontmatter parser ────────────────────────────────────────────────────────

def parse_frontmatter(path: Path) -> tuple[dict | None, str | None]:
    """Return (fields_dict, error_string). fields_dict is None on read error."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, str(e)

    if not text.startswith("---"):
        return {}, None

    end = text.find("\n---", 3)
    if end == -1:
        return {}, "no closing --- in frontmatter"

    fields: dict = {}
    current_key: str | None = None
    block_scalar_key: str | None = None   # key collecting a > or | block
    block_scalar_lines: list[str] = []

    def flush_block():
        nonlocal block_scalar_key, block_scalar_lines
        if block_scalar_key is not None:
            fields[block_scalar_key] = " ".join(block_scalar_lines).strip()
        block_scalar_key = None
        block_scalar_lines = []

    for line in text[3:end].splitlines():
        # Top-level key
        m = re.match(r'^([\w-]+):\s*(.*)', line)
        if m:
            flush_block()
            current_key = m.group(1)
            raw_val = m.group(2).strip()
            if raw_val in (">", "|", ">-", "|-"):
                # Block scalar — value on following indented lines
                block_scalar_key = current_key
                block_scalar_lines = []
                fields[current_key] = {}  # placeholder
            else:
                val = raw_val.strip("\"'")
                fields[current_key] = val if val else {}
            continue

        # Block scalar continuation (indented line)
        if block_scalar_key is not None:
            if line.startswith((" ", "\t")):
                block_scalar_lines.append(line.strip())
                continue
            else:
                flush_block()

        # Nested key (2-space or 4-space indent)
        if current_key:
            m = re.match(r'^\s+([\w-]+):\s*(.*)', line)
            if m:
                nested_val = m.group(2).strip().strip("\"'")
                if isinstance(fields.get(current_key), dict):
                    fields[current_key][m.group(1)] = nested_val

    flush_block()
    return fields, None


# ── Validators ────────────────────────────────────────────────────────────────

def validate_plugin_json(path: Path) -> list[str]:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]

    for field in ("name", "description"):
        if not data.get(field):
            errors.append(f"missing '{field}'")

    author = data.get("author")
    if not isinstance(author, dict):
        errors.append("missing 'author' object")
    else:
        if not author.get("name"):
            errors.append("missing 'author.name'")

    # name must match the plugin directory
    plugin_dir = path.parent.parent.name
    if data.get("name") and data["name"] != plugin_dir:
        errors.append(f"name '{data['name']}' doesn't match directory '{plugin_dir}'")

    return errors


def validate_marketplace_json(path: Path) -> list[str]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return []
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]


def validate_kimi_plugin_json(path: Path) -> list[str]:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]

    for field in ("name", "version", "description"):
        if not data.get(field):
            errors.append(f"missing '{field}'")

    plugin_dir = path.parent.parent
    if data.get("name") and data["name"] != plugin_dir.name:
        errors.append(f"name '{data['name']}' doesn't match directory '{plugin_dir.name}'")

    # declared paths must exist and stay inside the plugin root
    for field in ("skills", "commands"):
        for rel in ([data[field]] if isinstance(data.get(field), str)
                    else data.get(field) or []):
            target = (plugin_dir / rel).resolve()
            if not str(target).startswith(str(plugin_dir.resolve())):
                errors.append(f"'{field}' path '{rel}' escapes the plugin root")
            elif not target.exists():
                errors.append(f"'{field}' path '{rel}' does not exist")

    mcp_servers = data.get("mcpServers")
    if mcp_servers is not None and not isinstance(mcp_servers, dict):
        errors.append("'mcpServers' must be an object")

    return errors


def validate_kimi_marketplace_json(path: Path) -> list[str]:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]

    root = path.parent
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        return ["missing 'plugins' array"]
    for entry in plugins:
        if not entry.get("id") or not entry.get("source"):
            errors.append(f"entry missing 'id' or 'source': {entry}")
            continue
        source = entry["source"]
        # Remote sources (zip URLs) can't be checked locally; only local paths.
        if not source.startswith(("http://", "https://")) and not (root / source).is_dir():
            errors.append(f"source '{source}' for '{entry['id']}' does not exist")
    return errors


def validate_skill_md(path: Path) -> list[str]:
    fields, err = parse_frontmatter(path)
    if fields is None:
        return [err]
    if err:
        return [err]

    errors = []
    for field in ("name", "description", "allowed-tools"):
        if not fields.get(field):
            errors.append(f"missing frontmatter field '{field}'")

    metadata = fields.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("missing 'metadata' block")
    else:
        for mf in ("version", "version-date"):
            if not metadata.get(mf):
                errors.append(f"missing 'metadata.{mf}'")

    return errors


def validate_command_md(path: Path) -> list[str]:
    fields, err = parse_frontmatter(path)
    if fields is None:
        return [err]
    if err:
        return [err]

    errors = []
    for field in ("description", "allowed-tools"):
        if not fields.get(field):
            errors.append(f"missing frontmatter field '{field}'")

    return errors


# ── Dispatch ──────────────────────────────────────────────────────────────────

def validate_file(path: Path) -> list[str]:
    name = path.name
    parts = path.parts

    if name == "plugin.json" and ".claude-plugin" in parts:
        # root marketplace.json vs individual plugin.json
        if "plugins" in parts:
            return validate_plugin_json(path)
        return validate_marketplace_json(path)

    if name == "plugin.json" and ".kimi-plugin" in parts:
        return validate_kimi_plugin_json(path)

    if name.startswith("kimi-marketplace") and name.endswith(".json"):
        return validate_kimi_marketplace_json(path)

    if name == "marketplace.json" and ".claude-plugin" in parts:
        return validate_marketplace_json(path)

    if name == "SKILL.md":
        return validate_skill_md(path)

    if name.endswith(".md") and "commands" in parts and name != "README.md":
        return validate_command_md(path)

    return []  # not a file we validate


# ── Main ──────────────────────────────────────────────────────────────────────

def collect_plugin_files(root: Path) -> list[Path]:
    patterns = [
        "plugins/*/.claude-plugin/plugin.json",
        "plugins/_drafts/*/.claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        "plugins/*/.kimi-plugin/plugin.json",
        "kimi-marketplace.json",
        "kimi-marketplace.local.json",
        "plugins/*/skills/*/SKILL.md",
        "plugins/_drafts/*/skills/*/SKILL.md",
        "plugins/*/commands/*.md",
        "plugins/_drafts/*/commands/*.md",
    ]
    files = []
    for pattern in patterns:
        files.extend(root.glob(pattern))
    return sorted(set(files))


def main() -> int:
    root = Path(__file__).parent.parent

    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:] if f]
    else:
        files = collect_plugin_files(root)

    # Only keep files we know how to validate
    relevant = [f for f in files if validate_file.__code__]  # always true; filter in validate_file

    total = 0
    failed = 0

    for path in relevant:
        errors = validate_file(path)
        if errors is None:
            continue
        display = path.relative_to(root) if path.is_absolute() else path
        for err in errors:
            print(f"  \033[31m✗\033[0m {display}: {err}")
            failed += 1
        total += 1

    checked = len(relevant)
    if failed:
        print(f"\n\033[31m{failed} error(s) in {checked} file(s)\033[0m")
        return 1

    print(f"  \033[32m✓\033[0m {checked} file(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
