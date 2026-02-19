---
description: Register all known BPA instance profiles (run once after installing bpa-instances)
argument-hint: []
allowed-tools: [Bash]
---

# BPA Setup

Register all known BPA deployment profiles so they can be used by any BPA tool via `instance="<name>"`.

## Instructions

### Step 1 — Check the MCP server binary

Run `mcp-eregistrations-bpa --version` via Bash.

- If it succeeds, continue to Step 2.
- If the command is not found, stop and tell the user:

  > The BPA MCP server is not installed. Run the following from the plugin marketplace repository root, then restart Claude:
  > ```
  > uv tool install ./MCP_eRegistrations_BPA
  > ```
  > Once installed, run `/bpa-setup` again.

Do not proceed past this point until the binary is confirmed.

### Step 2 — Register instance profiles

Call `mcp__BPA__instance_add` for each deployment below. Skip any profile that already exists
(check with `instance_list` first to avoid duplicates).

### Keycloak instances

```
instance_add(name="nigeria",        bpa_instance_url="https://bpa.gateway.nipc.gov.ng",         keycloak_url="https://login.gateway.nipc.gov.ng",             keycloak_realm="NG")
instance_add(name="elsalvador-dev", bpa_instance_url="https://bpa.dev.els.eregistrations.org",   keycloak_url="https://login.dev.els.eregistrations.org",       keycloak_realm="SV")
instance_add(name="kenya-test",     bpa_instance_url="https://bpa.test.kenya.eregistrations.org",keycloak_url="https://login.test.kenya.eregistrations.org",    keycloak_realm="KE")
instance_add(name="investkenya",    bpa_instance_url="https://bpa.investkenya.go.ke",             keycloak_url="https://login.investkenya.go.ke",                keycloak_realm="ke")
instance_add(name="jamaica",        bpa_instance_url="https://bpa.jamaica.eregistrations.org",   keycloak_url="https://login.jamaica.eregistrations.org",       keycloak_realm="JM")
instance_add(name="lesotho2",       bpa_instance_url="https://bpa.businessregistrations.gov.ls", keycloak_url="https://login.businessregistrations.gov.ls",     keycloak_realm="LS")
instance_add(name="colombia-test",  bpa_instance_url="https://bpa.test.colombia.eregistrations.org", keycloak_url="https://login.test.colombia.eregistrations.org", keycloak_realm="CO")
instance_add(name="gambia",         bpa_instance_url="https://bpa.easybusiness.gov.gm",           keycloak_url="https://login.easybusiness.gov.gm",              keycloak_realm="GM")
instance_add(name="bhutan-staging", bpa_instance_url="https://bpa.stagingibls.moea.gov.bt",       keycloak_url="https://login.stagingibls.moea.gov.bt",          keycloak_realm="BT")
```

### CAS instances (Cuba)

For Cuba instances, ask the user for the CAS client secret before registering:

```
instance_add(name="cuba-test", bpa_instance_url="https://bpa.test.cuba.eregistrations.org",
  cas_url="https://eid.test.cuba.eregistrations.org/cback/v1.0",
  cas_client_id="mcp-bpa", cas_client_secret="<ask user>")

instance_add(name="cuba", bpa_instance_url="https://bpa.cuba.eregistrations.org",
  cas_url="https://bpa.cuba.eregistrations.org/cback/v1.0",
  cas_client_id="mcp-bpa", cas_client_secret="<ask user>")
```

If the user doesn't have Cuba credentials, skip those profiles.

## After setup

Confirm with `instance_list` and show the registered profiles.
Then suggest: "Run `/bpa-login <instance>` to authenticate."

## Upgrading note

If the user seems to be upgrading (they mention old server names like `BPA-jamaica`, or tools from the old servers still appear), tell them:

> You may still have old BPA-* server entries in your config. Run this from the marketplace repo root to clean them up:
> ```
> uv run scripts/migrate-to-multi-instance.py --apply
> ```
> Then restart Claude Desktop if open.

## Usage

```
/bpa-setup
```
