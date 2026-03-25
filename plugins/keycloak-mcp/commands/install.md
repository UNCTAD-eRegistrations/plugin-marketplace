---
description: Verify the Keycloak MCP server is loaded and ready
allowed-tools: [Bash]
---

# Keycloak Install

Verify the Keycloak MCP server is loaded and instance profiles are available.

## Instructions

### Step 0 — Check prerequisites

Run `command -v uvx` via Bash.

- **If found**, continue to Step 1.
- **If not found**, check `command -v uv`:
  - **If `uv` found** → `uvx` is available as `uv tool run`. Continue to Step 1.
  - **If neither found** → stop and tell the user:

    > `uv` is required but not installed. Install it with:
    >
    > ```
    > curl -LsSf https://astral.sh/uv/install.sh | sh
    > ```
    >
    > Then restart your terminal and run `/keycloak-mcp:install` again.

Do not proceed past this point until `uv`/`uvx` is confirmed.

### Step 1 — Confirm the Keycloak MCP server is loaded

> The plugin's `.mcp.json` uses `uvx mcp-eregistrations-keycloak@latest`, which auto-downloads the latest version on every startup. No manual install or upgrade is needed.

Attempt to call `mcp__Keycloak__kc_connection_status(instance="jamaica")`.

- If it succeeds (even with an auth error), the server is loaded. Continue to Step 2.
- If the tool is unavailable or the call fails with a server/connection error, stop and tell the user:

  > The Keycloak MCP server is not loaded yet. This happens after a fresh install — Claude needs to restart to pick up the new MCP server.
  >
  > Please restart Claude, then run `/keycloak-mcp:install` again.

Do not proceed past this point until the Keycloak tools are confirmed available.

### Step 2 — Check instance profiles

The Keycloak MCP reuses instance profiles from the BPA MCP. Call `mcp__BPA__instance_list()` to check if profiles exist.

- **If profiles exist** → list them and continue to Step 3.
- **If no profiles or BPA tools unavailable** → tell the user:

  > No instance profiles found. The Keycloak MCP shares profiles with the BPA MCP.
  > Run `/bpa-mcp:install` first to register your eRegistrations instances.

### Step 3 — Report

Show a summary:

```
Keycloak MCP Server — Ready
═══════════════════════════
  Server:    loaded (51 tools)
  Instances: <count> profiles available (shared with BPA)

Next step: Run `/keycloak-mcp:login <instance>` to authenticate with admin credentials.

Note: Keycloak Admin API requires a user with realm-management roles
(manage-users, manage-realm, view-realm). Regular BPA credentials won't work.
```

## Usage

```
/keycloak-mcp:install
```
