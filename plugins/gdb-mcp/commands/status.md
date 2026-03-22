---
description: Check GDB connection status and list available databases
effort: low
allowed-tools: [mcp__GDB__gdb_status, mcp__GDB__gdb_instance_list, mcp__GDB__gdb_catalog_list, mcp__GDB__gdb_auth_login]
---

# GDB Status

Check GDB server connectivity and list available databases.

Arguments: `$ARGUMENTS`

## Instructions

1. Call `gdb_instance_list()` to show configured instances with GDB URLs.

2. If an instance was specified (e.g. `/gdb-mcp:status jamaica`), check that instance. Otherwise check all instances with gdb_url.

3. For each instance, call `gdb_status(instance="<name>")`.
   - If it succeeds, show version and status.
   - If auth fails, call `gdb_auth_login(instance="<name>")` to authenticate, then retry.
   - If connection fails, report the error.

4. Call `gdb_catalog_list(instance="<name>")` to show database count.

5. Present results as a table:

| Instance | Status | Version | Databases |
|----------|--------|---------|-----------|

## Usage

```
/gdb-mcp:status              # check all instances
/gdb-mcp:status jamaica      # check specific instance
```
