# bpa-debug

Scan, investigate, and fix configuration issues in BPA services.

## Commands

| Command | Description |
|---------|-------------|
| `/debug <id> [server] [--fix]` | Scan and optionally auto-fix issues |

## Agents

| Agent | Description |
|-------|-------------|
| `bpa-debugger` | Autonomous diagnostic agent for systematic issue resolution |

## Workflow

1. Scans service for all issues
2. Groups by severity (CRITICAL → WARNING)
3. Generates dependency-ordered fix plan
4. Applies fixes with verification and rollback on failure

## Requirements

- Authenticated BPA MCP server
