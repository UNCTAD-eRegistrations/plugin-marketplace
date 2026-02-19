# service-migration

Copy BPA services between instances and audit cross-instance configuration drift.

## Commands

| Command | Description |
|---------|-------------|
| `/migrate-service <id> <source> <target> [--dry-run]` | Full service migration with validation |
| `/diff-instances <id> <server-a> <server-b>` | Compare the same service across two instances |

## Agents

| Agent | Description |
|-------|-------------|
| `migration-coordinator` | Orchestrates safe cross-instance migrations with pre/post validation |

## What migrates

Form structure · Determinants · Roles · Registrations · Costs · Requirements · Print documents · Referenced classifications

## What needs manual follow-up

- Institution assignments (country-specific → run `/setup-institutions`)
- Bot configurations (external service URLs differ → run `/bot-mappings`)
- Translations (language-specific → re-do manually)

## Requires

`bpa-instances` plugin installed with both source and target servers configured.
