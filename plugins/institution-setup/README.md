# institution-setup

Configure institutions and their assignments for BPA deployments.

## Commands

| Command | Description |
|---------|-------------|
| `/setup-institutions [server] [--service <id>]` | Interactive wizard for institution configuration |
| `/audit-institutions [server]` | Audit institution coverage across all services |

## Agents

| Agent | Description |
|-------|-------------|
| `deployment-configurator` | Configures all institutions for a fresh country deployment |

## Typical use case

After running `/migrate-service`, institutions from the source country don't apply to the target. This plugin helps re-assign the correct local institutions.
