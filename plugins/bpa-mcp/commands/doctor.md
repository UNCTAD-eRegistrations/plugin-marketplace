---
description: Diagnose and fix common BPA MCP server issues
allowed-tools: [Bash]
---

# BPA Doctor

Diagnose the BPA MCP server installation and fix common issues. Produces a checklist like `brew doctor` or `flutter doctor`.

## Instructions

Run each check below **in order**. Collect all results, then print a summary at the end.

Use these status markers:
- `[ok]` — check passed
- `[warn]` — non-blocking issue, include fix suggestion
- `[FAIL]` — blocking issue, include fix instructions
- `[fix]` — issue was auto-fixed

### Check 1 — uv / uvx available

Run `command -v uvx` via Bash.

- **Found** → `[ok] uvx found at <path>`
- **Not found** → check `command -v uv`:
  - **Found** → `[ok] uv found at <path> (uvx available as uv tool run)`
  - **Not found** → `[FAIL] uv/uvx not found — install with: curl -LsSf https://astral.sh/uv/install.sh | sh`

If FAIL, continue checking (don't stop) — report all issues at once.

### Check 2 — Server version and updates

Run these two commands **in parallel** via Bash:

1. `uv tool list 2>/dev/null | grep mcp-eregistrations-bpa | head -1 | awk '{print $2}' | tr -d 'v'`
2. `curl -sf https://pypi.org/pypi/mcp-eregistrations-bpa/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"`

- **Installed and up to date** → `[ok] mcp-eregistrations-bpa v<version> (latest)`
- **Installed but outdated** → `[warn] mcp-eregistrations-bpa v<installed> → v<latest> available — run: uv tool upgrade mcp-eregistrations-bpa`
- **Not installed via uv tool** → `[ok] not installed locally (uvx will download on demand)`
- **PyPI check failed** → `[warn] could not check latest version (network issue?)`

### Check 3 — BPA MCP server loaded

Attempt to call `mcp__BPA__instance_list()`.

- **Succeeds** → `[ok] BPA MCP server loaded and responding`
- **Fails or tool not found** → `[FAIL] BPA MCP server not loaded — restart Claude and run /bpa-mcp:install`

If FAIL, skip checks 4–6 (they depend on the server) but still report all issues collected so far.

### Check 4 — Legacy BPA-* entries

Run via Bash:

```
mcp-eregistrations-bpa migrate 2>/dev/null || uvx mcp-eregistrations-bpa migrate 2>/dev/null
```

- **"Nothing to migrate"** → `[ok] no legacy BPA-* entries`
- **Migration plan shown** → `[warn] legacy BPA-* entries found — run /bpa-mcp:install to migrate (Step 2.5)`

### Check 5 — Instance profiles

Use the result from `instance_list` in Check 3.

- **1+ profiles registered** → `[ok] <count> instance profiles registered`
- **Empty list** → `[warn] no instance profiles — run /bpa-mcp:install to register`

### Check 6 — Auth status per instance

For each registered instance, call `mcp__BPA__connection_status(instance="<name>")`.

Run these in parallel (batch all instances at once).

For each instance:
- **Authenticated** → `[ok] <name>: authenticated`
- **Auto-login ready (not yet authenticated)** → `[ok] <name>: auto-login ready`
- **Not authenticated, no auto-login** → `[warn] <name>: not authenticated — run /bpa-mcp:login <name>`
- **Connection error** → `[FAIL] <name>: unreachable — check network or instance URL`

### Check 7 — Server logs (errors only)

Run via Bash:

```
find ~/.config/mcp-eregistrations-bpa/instances -name 'server.log' -exec grep -l 'ERROR\|CRITICAL' {} \; 2>/dev/null
```

- **No error logs found** → `[ok] no errors in server logs`
- **Error logs found** → `[warn] errors found in server logs: <paths>`. Show the last 5 error lines from each log:
  ```
  grep -E 'ERROR|CRITICAL' <path> | tail -5
  ```

## Summary

After all checks, print a summary block:

```
BPA Doctor Summary
══════════════════
  <N> checks passed
  <N> warnings
  <N> failures

<If warnings or failures, list the fix commands:>
Suggested fixes:
  1. <fix command or instruction>
  2. <fix command or instruction>
```

## Usage

```
/bpa-mcp:doctor
```
