> **DRAFT** — This plugin was AI-generated and has not been verified against a live BPA instance. Tool names, parameters, and workflows may be outdated or incorrect.

# institution-setup

Configure institutions and their assignments for BPA deployments.

## Commands

| Command | Description |
|---------|-------------|
| `/setup-institutions [instance] [--service <id>]` | Interactive wizard for institution configuration |
| `/audit-institutions [instance]` | Audit institution coverage across all services |

## Agents

| Agent | Description |
|-------|-------------|
| `deployment-configurator` | Configures all institutions for a fresh country deployment |

## Typical use case

After running `/migrate-service`, institutions from the source country don't apply to the target. This plugin helps re-assign the correct local institutions.
