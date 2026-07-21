#!/usr/bin/env python3
"""
Bulk-install UNCTAD eRegistrations plugins into Kimi Code, without the TUI.

Kimi Code's `/plugins install` accepts a single source at a time, which makes
rolling out the full marketplace tedious. This script provisions plugins the
same way the installer does:

  1. downloads each plugin zip from the rolling `kimi-latest` release
  2. extracts it into $KIMI_CODE_HOME/plugins/managed/<id>/
  3. upserts the entry in $KIMI_CODE_HOME/plugins/installed.json

Afterwards, run `/plugins reload` in Kimi Code (or restart it) to activate.

Usage:
  python3 scripts/kimi-install.py                  # install every catalog plugin
  python3 scripts/kimi-install.py bpa-mcp handoff  # install specific plugins
  python3 scripts/kimi-install.py --no-bpa-install # skip the BPA instance setup

After provisioning, the script runs `/bpa-mcp:install` headlessly
(`kimi -p "/bpa-mcp:install" --yolo`) to register the eRegistrations instance
profiles, unless --no-bpa-install is given or the `kimi` binary is not on PATH.
Requires `uv`/`uvx` on PATH (the MCP servers run via uvx).

Works standalone — the catalog is fetched from GitHub, so users can also run:
  curl -sL https://raw.githubusercontent.com/UNCTAD-eRegistrations/plugin-marketplace/main/scripts/kimi-install.py | python3 -

Note: this writes to Kimi Code's internal plugin store (installed.json format
version 1). If a future Kimi Code release changes that format, re-check this
script. Plugins installed this way can still be managed from `/plugins`.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

CATALOG_URL = ("https://raw.githubusercontent.com/UNCTAD-eRegistrations/"
               "plugin-marketplace/main/kimi-marketplace.json")


def kimi_home() -> Path:
    return Path(os.environ.get("KIMI_CODE_HOME", Path.home() / ".kimi-code"))


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def main() -> int:
    wanted = [a for a in sys.argv[1:] if not a.startswith("--")]
    no_bpa_install = "--no-bpa-install" in sys.argv[1:]
    catalog = fetch_json(CATALOG_URL)
    entries = {p["id"]: p for p in catalog["plugins"]}

    unknown = [w for w in wanted if w not in entries]
    if unknown:
        print(f"Unknown plugin(s): {', '.join(unknown)}")
        print(f"Available: {', '.join(entries)}")
        return 1

    to_install = wanted or list(entries)
    home = kimi_home()
    managed = home / "plugins" / "managed"
    managed.mkdir(parents=True, exist_ok=True)
    installed_path = home / "plugins" / "installed.json"

    if installed_path.exists():
        installed = json.loads(installed_path.read_text(encoding="utf-8"))
    else:
        installed = {"version": 1, "plugins": []}

    stamp = now_iso()
    for plugin_id in to_install:
        source = entries[plugin_id]["source"]
        root = managed / plugin_id
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / f"{plugin_id}.zip"
            print(f"  downloading {plugin_id} ...")
            urllib.request.urlretrieve(source, str(zip_path))
            if root.exists():
                shutil.rmtree(root)
            root.mkdir(parents=True)
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(root)
        if not (root / ".kimi-plugin" / "plugin.json").is_file():
            print(f"  \033[31m✗\033[0m {plugin_id}: zip has no .kimi-plugin/plugin.json — skipped")
            shutil.rmtree(root, ignore_errors=True)
            continue

        record = next((p for p in installed["plugins"] if p.get("id") == plugin_id), None)
        if record is None:
            record = {"id": plugin_id, "installedAt": stamp}
            installed["plugins"].append(record)
        record.update({
            "root": str(root),
            "source": "zip-url",
            "enabled": True,
            "updatedAt": stamp,
            "originalSource": source,
        })
        print(f"  \033[32m✓\033[0m {plugin_id}")

    tmp_out = installed_path.with_suffix(".json.tmp")
    tmp_out.write_text(json.dumps(installed, indent=2) + "\n", encoding="utf-8")
    tmp_out.replace(installed_path)

    print(f"\nInstalled {len(to_install)} plugin(s) into {managed}")

    installed_ids = {p.get("id") for p in installed["plugins"]}
    if no_bpa_install or "bpa-mcp" not in installed_ids:
        print("Run `/plugins reload` in Kimi Code (or restart it) to activate.")
        return 0

    # Register the eRegistrations instance profiles by running the plugin's own
    # install command in a headless Kimi session (a new session picks up the
    # freshly provisioned plugins and starts the BPA MCP server by itself).
    kimi = shutil.which("kimi")
    if not kimi:
        print("`kimi` not on PATH — run `/bpa-mcp:install` inside Kimi Code to "
              "register instance profiles.")
        return 0
    if not (shutil.which("uvx") or shutil.which("uv")):
        print("\033[33m!\033[0m `uv` is required by the BPA MCP server but was not found.")
        print("  Install it first: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return 1
    print("\nRegistering BPA instance profiles (headless `kimi -p /bpa-mcp:install`)...")
    rc = subprocess.run([kimi, "-p", "/bpa-mcp:install"]).returncode
    if rc != 0:
        print("\033[33m!\033[0m Headless install failed — run `/bpa-mcp:install` inside "
              "Kimi Code instead.")
        return rc
    print("\nDone. Open Kimi Code and run `/bpa-mcp:login <instance>` to authenticate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
