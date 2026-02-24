---
description: Check connection status for all configured BPA instances
argument-hint: [instance-name]
allowed-tools: [Bash]
---

# BPA Instance Status

Check connectivity and auth status for BPA instances. `$ARGUMENTS`

## Instructions

### Step 1 — Version check

Run these two Bash commands **in parallel**:

1. Get the installed version:
   ```
   uv tool list 2>/dev/null | grep mcp-eregistrations-bpa | head -1 | awk '{print $2}' | tr -d 'v'
   ```

2. Get the latest PyPI version:
   ```
   curl -sf https://pypi.org/pypi/mcp-eregistrations-bpa/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"
   ```

Compare the two versions. Show a header line before the instance table:

- **Up to date:** `BPA MCP Server v0.20.1 (latest)`
- **Update available:** `BPA MCP Server v0.17.4 → v0.20.1 available. Run: uv tool upgrade mcp-eregistrations-bpa`
- **PyPI check failed** (curl error, no internet): `BPA MCP Server v0.17.4 (update check failed)` — do not block on this, continue to Step 2.

### Step 2 — Instance connectivity

If an instance name is given, check only that instance.
Otherwise call `instance_list` first to discover all registered profiles, then check each in parallel.

For each instance, call `mcp__BPA__connection_status(instance="<name>")`.

Report a table:

```
Instance       | URL                                        | Auth   | Status
jamaica        | https://bpa.jamaica.eregistrations.org     | OIDC   | ✅ Authenticated (expires 2h)
lesotho2       | https://bpa.businessregistrations.gov.ls   | OIDC   | ❌ Not authenticated
nigeria        | https://bpa.gateway.nipc.gov.ng            | OIDC   | 🔑 Auto-login ready (stored credentials)
cuba           | https://bpa.cuba.eregistrations.org        | CAS    | ❌ Not authenticated
```

- If `auto_login_available` is true and not currently authenticated, show "Auto-login ready" — credentials exist and will activate on first tool call.
- For unauthenticated instances without auto-login, show: "Run `/bpa-login <name>` to authenticate."

## Usage

```
/bpa-status
/bpa-status jamaica
```
