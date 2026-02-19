# workflow-manager

Discover, execute, monitor, and manage BPA workflow orchestrations.

## Commands

| Command | Description |
|---------|-------------|
| `/workflow [id/name] [instance] [--dry-run]` | Execute or list workflows |

## Features

- List all available workflows with required inputs
- Dry-run validation before execution
- Step-by-step interactive workflow support
- Retry from failure point
- Full rollback of completed steps

## Requirements

- Authenticated BPA MCP server
