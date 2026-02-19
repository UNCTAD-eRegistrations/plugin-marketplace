#!/usr/bin/env python3
"""Generate .mcp.json from instances.yaml.

Writes to two locations:
  - .mcp.json (repo root, for direct use after cloning)
  - plugins/bpa-instances/.mcp.json (the installable plugin)

All other plugins do NOT have .mcp.json — install bpa-instances once instead.

Usage:
    uv run --with pyyaml scripts/generate-mcp-json.py

CAS instances require a client secret at runtime via environment variables.
Keycloak instances use PKCE — no secret needed.
"""

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml required.  uv run --with pyyaml scripts/generate-mcp-json.py")
    sys.exit(1)

REPO_ROOT = Path(__file__).parent.parent
INSTANCES_FILE = REPO_ROOT / "MCP_eRegistrations_BPA" / "instances.yaml"
BPA_INSTANCES_PLUGIN = REPO_ROOT / "plugins" / "bpa-instances"


def build_server_entry(instance: dict) -> dict:
    entry: dict = {
        "type": "stdio",
        "command": "mcp-eregistrations-bpa",
        "env": {"BPA_INSTANCE_URL": instance["bpa_url"]},
    }
    auth = instance.get("auth", "keycloak")
    if auth == "keycloak":
        entry["env"]["KEYCLOAK_URL"] = instance["keycloak_url"]
        entry["env"]["KEYCLOAK_REALM"] = instance["keycloak_realm"]
    elif auth == "cas":
        entry["env"]["CAS_URL"] = instance["cas_url"]
        entry["env"]["CAS_CLIENT_ID"] = instance["cas_client_id"]
        var = f"BPA_{instance['name'].upper().replace('-', '_')}_CLIENT_SECRET"
        entry["env"]["CAS_CLIENT_SECRET"] = f"${{{var}}}"
    return entry


def main():
    with open(INSTANCES_FILE) as f:
        data = yaml.safe_load(f)
    instances = data["instances"]

    servers = {f"BPA-{i['name']}": build_server_entry(i) for i in instances}
    out = json.dumps(servers, indent=2) + "\n"

    targets = [
        REPO_ROOT / ".mcp.json",
        BPA_INSTANCES_PLUGIN / ".mcp.json",
    ]
    for path in targets:
        path.write_text(out)
        print(f"Written: {path}")

    print(f"\n{len(instances)} instances configured across {len(targets)} files.")

    cas = [i for i in instances if i.get("auth") == "cas"]
    if cas:
        print("\nCAS instances — set these env vars before running:")
        for i in cas:
            var = f"BPA_{i['name'].upper().replace('-', '_')}_CLIENT_SECRET"
            print(f"  export {var}=<secret>   # {i['display_name']}")

    print("\nInstall MCP server: uv tool install ./MCP_eRegistrations_BPA")


if __name__ == "__main__":
    main()
