---
description: Discover, execute, and manage BPA workflow orchestrations
argument-hint: [workflow-id-or-name] [mcp-server] [--dry-run]
allowed-tools: [Read, Write, Bash]
---

# Workflow Manager

Manage BPA workflows from `$ARGUMENTS`.

## Instructions

Parse arguments:
- First token: workflow ID or name (if omitted, list available workflows)
- Second token: MCP server name (optional)
- `--dry-run`: validate inputs without executing

### If no workflow specified
List all available workflows with `workflow_list`, display names, descriptions, and required inputs.

### If workflow specified
1. Get full spec with `workflow_describe`
2. Validate required inputs are provided
3. If `--dry-run`: call `workflow_validate` and report
4. Otherwise: execute with `workflow_execute`, monitor with `workflow_status`
5. On failure: offer `workflow_retry` or `workflow_rollback`

### Interactive workflows
For workflows requiring step-by-step confirmation, use `workflow_start_interactive`, then `workflow_continue` / `workflow_confirm`.

## Usage

```
/workflow
/workflow setup-service BPA-jamaica
/workflow 15 BPA-lesotho2 --dry-run
```
