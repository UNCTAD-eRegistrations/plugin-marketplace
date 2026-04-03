---
description: Check Graylog connectivity and version
argument-hint: [instance-name]
effort: low
allowed-tools: [mcp__Graylog__graylog_connection_status, mcp__Graylog__graylog_system_info, mcp__Graylog__graylog_auth_login, mcp__Graylog__instance_list, mcp__Graylog-local-dev__graylog_connection_status, mcp__Graylog-local-dev__graylog_system_info, mcp__Graylog-local-dev__graylog_auth_login, mcp__Graylog-local-dev__instance_list]
---

# Graylog Status

Check Graylog server connectivity and version. `$ARGUMENTS`

## Instructions

### Step 1 — Discover instances

Call `instance_list()` to find all registered profiles. Filter to instances that have a `graylog_url` configured.

If an instance name was given, check only that instance.

### Step 2 — Check connectivity

For each instance with a graylog_url, call `graylog_connection_status(instance="<name>")`.

- If connected: note the Graylog version.
- If not connected but credentials may be stored: note as "Not authenticated".
- If connection fails: report the error.

### Step 3 — Report

#### Version header

Use the `version` field from the first successful `connection_status` response:

- `Graylog MCP Server v1.9.0`

#### Instance table

```
Instance       | Graylog URL                                    | Version | Status
cuba           | https://graylog.cuba.eregistrations.org       | 7.0.2   | Connected
nigeria        | https://graylog.gateway.nipc.gov.ng           |         | Not authenticated
jamaica        | https://graylog.jamaica.eregistrations.org    |         | No graylog_url
```

For unauthenticated instances, show: "Run `graylog_auth_login(instance=\"<name>\")` to authenticate. Note: Graylog uses its own credentials, NOT Keycloak."

## Usage

```
/graylog-mcp:status
/graylog-mcp:status cuba
```
