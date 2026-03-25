---
description: Diagnose and fix common Keycloak MCP server issues
allowed-tools: [Bash]
---

# Keycloak Doctor

Diagnose the Keycloak MCP server installation and fix common issues.

## Instructions

Run each check below **in order**. Collect all results, then print a summary at the end.

Use these status markers:
- `[ok]` — check passed
- `[warn]` — non-blocking issue, include fix suggestion
- `[FAIL]` — blocking issue, include fix instructions

### Check 1 — uv / uvx available

Run `command -v uvx` via Bash.

- **Found** → `[ok] uvx found at <path>`
- **Not found** → check `command -v uv`:
  - **Found** → `[ok] uv found at <path> (uvx available as uv tool run)`
  - **Not found** → `[FAIL] uv/uvx not found — install with: curl -LsSf https://astral.sh/uv/install.sh | sh`

If FAIL, continue checking (don't stop) — report all issues at once.

### Check 2 — Keycloak MCP server loaded

Attempt to call `mcp__Keycloak__kc_connection_status(instance="jamaica")`.

- **Succeeds (even with auth error)** → `[ok] Keycloak MCP server loaded and responding`
- **Fails or tool not found** → `[FAIL] Keycloak MCP server not loaded — restart Claude and run /keycloak-mcp:install`

If FAIL, skip checks 3–4 (they depend on the server) but still report all issues collected so far.

### Check 3 — Instance profiles (shared with BPA)

Call `mcp__BPA__instance_list()`.

- **1+ profiles registered** → `[ok] <count> instance profiles available (shared with BPA)`
- **Empty list** → `[warn] no instance profiles — run /bpa-mcp:install to register`
- **BPA tools unavailable** → `[warn] BPA MCP not loaded — install bpa-mcp plugin first for instance profiles`

### Check 4 — Auth status per instance

For each registered instance (from Check 3), call `mcp__Keycloak__kc_connection_status(instance="<name>")`.

For each instance:
- **Authenticated** → `[ok] <name>: authenticated`
- **Not authenticated** → `[warn] <name>: not authenticated — run /keycloak-mcp:login <name>`
- **Connection error** → `[FAIL] <name>: unreachable — check network or Keycloak URL`

## Summary

After all checks, print a summary block:

```
Keycloak Doctor Summary
═══════════════════════
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
/keycloak-mcp:doctor
```
