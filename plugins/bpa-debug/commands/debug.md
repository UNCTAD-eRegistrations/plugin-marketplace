---
description: Scan, investigate, and fix configuration issues in a BPA service
argument-hint: <service-id> [mcp-server] [--fix]
allowed-tools: [Read, Write, Bash]
---

# BPA Debug

Debug BPA service `$ARGUMENTS`.

## Instructions

Parse arguments:
- First token: service ID (required)
- Second token: MCP server name (optional, use active server if omitted)
- `--fix` flag: automatically apply fixes after scanning

### Execution flow

1. **Scan**: Run `debug_scan` to identify all configuration issues
2. **Group**: Run `debug_group_issues` to organize by severity and type
3. **Plan**: Run `debug_plan` to generate a dependency-ordered fix plan
4. **Report**: Present issues grouped by severity (critical → warning → info)
5. **Fix** (if `--fix`): Execute fixes via `debug_fix_batch`, then verify with `debug_verify`

### Issue categories to check
- Missing or broken determinants
- Unmapped bot fields
- Invalid role/status transitions
- Missing document requirements
- Broken form component references
- Orphaned registrations

## Usage

```
/debug 42 BPA-jamaica
/debug 17 --fix
/debug 42 BPA-lesotho2 --fix
```
