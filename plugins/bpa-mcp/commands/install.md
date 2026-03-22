---
description: Install the BPA MCP server and register instance profiles
argument-hint: [instance-name]
effort: low
allowed-tools: [Bash]
---

# BPA Install

Install the BPA MCP server and register instance profiles so they can be used via `instance="<name>"`.

Arguments: `$ARGUMENTS`

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
    > Then restart your terminal and run `/bpa-mcp:install` again.

Do not proceed past this point until `uv`/`uvx` is confirmed.

### Step 1 — Confirm the BPA MCP server is loaded

> The plugin's `.mcp.json` uses `uvx --from mcp-eregistrations@latest mcp-eregistrations-bpa`, which auto-downloads the latest version on every startup. No manual install or upgrade is needed.

Attempt to call `mcp__BPA__instance_list()`.

- If it succeeds (even returning an empty list), continue to Step 2.
- If the tool is unavailable or the call fails with a server/connection error, stop and tell the user:

  > The BPA MCP server is not loaded yet. This happens after a fresh install — Claude needs to restart to pick up the new MCP server.
  >
  > Please restart Claude, then run `/bpa-mcp:install` again.

Do not proceed past this point until the BPA tools are confirmed available.

### Step 2 — Migrate old server entries (upgrade path)

Run the migration detector via Bash:

```
uvx --from mcp-eregistrations@latest mcp-eregistrations-bpa migrate 2>/dev/null
```

- If the output says **"Nothing to migrate"** → continue to Step 3.
- If it shows a migration plan (old `BPA-*` entries detected) → apply it:

  ```
  uvx --from mcp-eregistrations@latest mcp-eregistrations-bpa migrate --apply
  ```

  Report the migration results to the user (profiles created, entries removed, backup details). If the output mentions restarting Claude Desktop, relay that to the user. Then continue to Step 3.

### Step 3 — Register instance profiles

If an instance name was provided (e.g. `/bpa-mcp:install lesotho2`), register **only that instance** from the registry below.
If no arguments, register **all instances**. Skip any profile that already exists (check with `instance_list` first).

If a name was provided but does not match any entry below, tell the user:
> Unknown instance "\<name\>". Run `/bpa-mcp:install` with no arguments to see all available profiles, or check the spelling.

#### Keycloak instances

| Name | BPA URL | GDB URL | Keycloak URL | Realm |
|------|---------|---------|-------------|-------|
| `guatemala-dev` | `https://bpa.dev.gt.eregistrations.org` | `https://gdb.dev.gt.eregistrations.org` | `https://login.dev.gt.eregistrations.org` | `GT` |
| `nigeria` | `https://bpa.gateway.nipc.gov.ng` | `https://gdb.gateway.nipc.gov.ng` | `https://login.gateway.nipc.gov.ng` | `NG` |
| `elsalvador-dev` | `https://bpa.dev.els.eregistrations.org` | `https://gdb.dev.els.eregistrations.org` | `https://login.dev.els.eregistrations.org` | `SV` |
| `kenya-test` | `https://bpa.test.kenya.eregistrations.org` | `https://gdb.test.kenya.eregistrations.org` | `https://login.test.kenya.eregistrations.org` | `KE` |
| `investkenya` | `https://bpa.investkenya.go.ke` | `https://gdb.investkenya.go.ke` | `https://login.investkenya.go.ke` | `ke` |
| `jamaica` | `https://bpa.jamaica.eregistrations.org` | `https://gdb.jamaica.eregistrations.org` | `https://login.jamaica.eregistrations.org` | `JM` |
| `lesotho2` | `https://bpa.businessregistrations.gov.ls` | `https://gdb.businessregistrations.gov.ls` | `https://login.businessregistrations.gov.ls` | `LS` |
| `colombia-test` | `https://bpa.test.colombia.eregistrations.org` | `https://gdb.test.colombia.eregistrations.org` | `https://login.test.colombia.eregistrations.org` | `CO` |
| `gambia` | `https://bpa.easybusiness.gov.gm` | `https://gdb.easybusiness.gov.gm` | `https://login.easybusiness.gov.gm` | `GM` |
| `bhutan-staging` | `https://bpa.stagingibls.moea.gov.bt` | `https://gdb.stagingibls.moea.gov.bt` | `https://login.stagingibls.moea.gov.bt` | `BT` |

Call `instance_add` with `name`, `bpa_instance_url`, `gdb_url`, `keycloak_url`, and `keycloak_realm`.

**Auto-login (optional):** After registering Keycloak instances, ask the user:

> Would you like to set up auto-login for any instances? This stores your credentials locally for silent auto-login on future sessions.

If yes, for each instance the user wants auto-login on, call `instance_add` again with the same profile params plus `username` and `password`. The server stores credentials in `~/.config/mcp-eregistrations-bpa/auth.json` for auto-login.

#### CAS instances (Cuba)

For Cuba instances, ask the user for the CAS client secret before registering:

| Name | BPA URL | GDB URL | CAS URL | Client ID |
|------|---------|---------|---------|-----------|
| `cuba-test` | `https://bpa.test.cuba.eregistrations.org` | `https://gdb.test.cuba.eregistrations.org` | `https://eid.test.cuba.eregistrations.org/cback/v1.0` | `mcp-bpa` |
| `cuba` | `https://bpa.cuba.eregistrations.org` | `https://gdb.cuba.eregistrations.org` | `https://bpa.cuba.eregistrations.org/cback/v1.0` | `mcp-bpa` |

If the user doesn't have Cuba credentials, skip those profiles.

## After install

Call `mcp__BPA__instance_list()` and show the registered profiles.
Then suggest: "Run `/bpa-mcp:login <instance>` to authenticate."

## Usage

```
/bpa-mcp:install              # register all instances
/bpa-mcp:install lesotho2     # register only lesotho2
/bpa-mcp:install jamaica      # register only jamaica
```
