---
description: Check connection status for all configured BPA instances
argument-hint: [instance-name]
allowed-tools: []
---

# BPA Instance Status

Check connectivity and auth status for BPA instances. `$ARGUMENTS`

## Instructions

### Step 1 — Instance connectivity

If an instance name is given, check only that instance.
Otherwise call `instance_list` first to discover all registered profiles, then check each in parallel.

For each instance, call `mcp__BPA__connection_status(instance="<name>")`.

### Step 2 — Report

#### Version header

Use the `version`, `latest_version`, and `update_available` fields from the first `connection_status` response:

- **Up to date:** `BPA MCP Server v0.22.0 (latest)`
- **Update available:** `BPA MCP Server v0.21.0 → v0.22.0 available. Restart Claude Code to pick up the latest version.`

#### Instance table

```
Instance       | URL                                        | Auth   | Status
jamaica        | https://bpa.jamaica.eregistrations.org     | OIDC   | ✅ Authenticated (expires 2h)
lesotho2       | https://bpa.businessregistrations.gov.ls   | OIDC   | ❌ Not authenticated
nigeria        | https://bpa.gateway.nipc.gov.ng            | OIDC   | 🔑 Auto-login ready (stored credentials)
cuba           | https://bpa.cuba.eregistrations.org        | CAS    | ❌ Not authenticated
```

- If `auto_login_available` is true and not currently authenticated, show "Auto-login ready" — credentials exist and will activate on first tool call.
- For unauthenticated instances without auto-login, show: "Run `/bpa-mcp:login <name>` to authenticate."

## Usage

```
/bpa-mcp:status
/bpa-mcp:status jamaica
```
