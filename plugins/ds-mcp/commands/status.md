---
description: Check DS connection status and system health
effort: low
allowed-tools: [mcp__DS__ds_health, mcp__DS__instance_list, mcp__DS__ds_auth_login, mcp__DS__service_list]
---

# DS Status

Check DS server connectivity, health, and available services.

Arguments: `$ARGUMENTS`

## Instructions

1. Call `instance_list()` to show configured instances with DS URLs.

2. If an instance was specified (e.g. `/ds-mcp:status jamaica`), check that instance. Otherwise check all instances with ds_url.

3. For each instance, call `ds_health(instance="<name>")`.
   - If it succeeds, show version, database, redis, and minio status.
   - If auth fails, call `ds_auth_login(instance="<name>")` to authenticate, then retry.
   - If connection fails, report the error.

4. If health passes and auth is available, call `service_list(instance="<name>")` to show service count.

5. Present results as a table:

| Instance | Status | Version | Services | DB | Redis | MinIO |
|----------|--------|---------|----------|----|-------|-------|

## Usage

```
/ds-mcp:status              # check all instances
/ds-mcp:status jamaica      # check specific instance
```
