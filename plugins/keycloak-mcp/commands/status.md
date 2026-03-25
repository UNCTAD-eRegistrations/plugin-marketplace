---
description: Check connection status for Keycloak instances
argument-hint: [instance-name]
allowed-tools: []
---

# Keycloak Instance Status

Check connectivity and auth status for Keycloak instances. `$ARGUMENTS`

## Instructions

### Step 1 — Instance connectivity

If an instance name is given, check only that instance.
Otherwise call `mcp__BPA__instance_list()` first to discover all registered profiles, then check each.

For each instance, call `mcp__Keycloak__kc_connection_status(instance="<name>")`.

### Step 2 — Report

#### Version header

Use the `version` field from the connection_status response if available:

- `Keycloak MCP Server v<version>`

#### Instance table

```
Instance       | Keycloak URL                                   | Status
jamaica        | https://login.jamaica.eregistrations.org       | ✅ Authenticated (expires 2h)
lesotho2       | https://login.businessregistrations.gov.ls     | ❌ Not authenticated
nigeria        | https://login.gateway.nipc.gov.ng              | ✅ Authenticated (expires 1h)
```

For unauthenticated instances, show: "Run `/keycloak-mcp:login <name>` to authenticate."

## Usage

```
/keycloak-mcp:status
/keycloak-mcp:status jamaica
```
