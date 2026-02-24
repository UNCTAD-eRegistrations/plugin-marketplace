---
description: Install the BPA MCP server and register instance profiles
argument-hint: [instance-name]
allowed-tools: [Bash]
---

# BPA Install

Install the BPA MCP server and register instance profiles so they can be used via `instance="<name>"`.

Arguments: `$ARGUMENTS`

## Instructions

### Step 1 — Ensure the MCP server binary is installed

Run `command -v mcp-eregistrations-bpa` via Bash.

- If it succeeds, continue to Step 2.
- If the command is not found, install it:

  1. Run:
     ```
     uv tool install mcp-eregistrations-bpa
     ```

  2. Verify with `command -v mcp-eregistrations-bpa`. If not found, tell the user to restart their terminal or Claude and run `/bpa-install` again — the PATH may need to refresh after install.

Do not proceed past this point until the binary is confirmed.

### Step 2 — Confirm the BPA MCP server is loaded

Attempt to call `mcp__BPA__instance_list()`.

- If it succeeds (even returning an empty list), continue to Step 3.
- If the tool is unavailable or the call fails with a server/connection error, stop and tell the user:

  > The BPA MCP server is not loaded yet. This happens after a fresh install — Claude needs to restart to pick up the new MCP server.
  >
  > Please restart Claude, then run `/bpa-install` again.

Do not proceed past this point until the BPA tools are confirmed available.

### Step 2.5 — Migrate old server entries (upgrade path)

Run the migration detector via Bash:

```
mcp-eregistrations-bpa migrate
```

- If the output says **"Nothing to migrate"** → continue to Step 3.
- If it shows a migration plan (old `BPA-*` entries detected) → apply it:

  ```
  mcp-eregistrations-bpa migrate --apply
  ```

  Report the migration results to the user (profiles created, entries removed, backup details). If the output mentions restarting Claude Desktop, relay that to the user. Then continue to Step 3.

### Step 3 — Register instance profiles

If an instance name was provided (e.g. `/bpa-install lesotho2`), register **only that instance** from the registry below.
If no arguments, register **all instances**. Skip any profile that already exists (check with `instance_list` first).

If a name was provided but does not match any entry below, tell the user:
> Unknown instance "\<name\>". Run `/bpa-install` with no arguments to see all available profiles, or check the spelling.

#### Keycloak instances

| Name | BPA URL | Keycloak URL | Realm |
|------|---------|-------------|-------|
| `nigeria` | `https://bpa.gateway.nipc.gov.ng` | `https://login.gateway.nipc.gov.ng` | `NG` |
| `elsalvador-dev` | `https://bpa.dev.els.eregistrations.org` | `https://login.dev.els.eregistrations.org` | `SV` |
| `kenya-test` | `https://bpa.test.kenya.eregistrations.org` | `https://login.test.kenya.eregistrations.org` | `KE` |
| `investkenya` | `https://bpa.investkenya.go.ke` | `https://login.investkenya.go.ke` | `ke` |
| `jamaica` | `https://bpa.jamaica.eregistrations.org` | `https://login.jamaica.eregistrations.org` | `JM` |
| `lesotho2` | `https://bpa.businessregistrations.gov.ls` | `https://login.businessregistrations.gov.ls` | `LS` |
| `colombia-test` | `https://bpa.test.colombia.eregistrations.org` | `https://login.test.colombia.eregistrations.org` | `CO` |
| `gambia` | `https://bpa.easybusiness.gov.gm` | `https://login.easybusiness.gov.gm` | `GM` |
| `bhutan-staging` | `https://bpa.stagingibls.moea.gov.bt` | `https://login.stagingibls.moea.gov.bt` | `BT` |

Call `instance_add` with the corresponding `name`, `bpa_instance_url`, `keycloak_url`, and `keycloak_realm`.

**Auto-login (optional):** After registering Keycloak instances, ask the user:

> Would you like to set up auto-login for any instances? This stores your BPA credentials securely in the OS keyring so authentication happens transparently — no browser interaction needed.

If yes, for each instance the user wants auto-login on, call `instance_add` again with the same profile params plus `username` and `password`. The server will store the credentials in the system keyring (marked with a `__keyring__` sentinel — never stored in plain text).

#### CAS instances (Cuba)

For Cuba instances, ask the user for the CAS client secret before registering:

| Name | BPA URL | CAS URL | Client ID |
|------|---------|---------|-----------|
| `cuba-test` | `https://bpa.test.cuba.eregistrations.org` | `https://eid.test.cuba.eregistrations.org/cback/v1.0` | `mcp-bpa` |
| `cuba` | `https://bpa.cuba.eregistrations.org` | `https://bpa.cuba.eregistrations.org/cback/v1.0` | `mcp-bpa` |

If the user doesn't have Cuba credentials, skip those profiles.

## After install

Call `mcp__BPA__instance_list()` and show the registered profiles.
Then suggest: "Run `/bpa-login <instance>` to authenticate."

## Usage

```
/bpa-install              # register all instances
/bpa-install lesotho2     # register only lesotho2
/bpa-install jamaica      # register only jamaica
```
