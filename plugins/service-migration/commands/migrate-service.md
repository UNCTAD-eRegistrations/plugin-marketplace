---
description: Copy a BPA service from one instance to another
argument-hint: <service-id> <source-instance> <target-instance> [--dry-run]
allowed-tools: [Read, Write, Bash]
---

# Service Migrator

Migrate BPA service `$ARGUMENTS` between instances.

## Arguments

- First: service ID on the source instance
- Second: source instance profile name (e.g., `jamaica`)
- Third: target instance profile name (e.g., `lesotho2`)
- `--dry-run`: validate and report what would happen without writing anything

## What gets migrated

The full service definition including:
- Service metadata (name, description, short_name)
- Form structure (all sections, fields, grids)
- Determinants and conditional logic
- Roles and status transitions
- Registrations (structure only — institutions must be re-assigned per country)
- Document requirements
- Costs
- Print documents
- Classifications referenced by the service (catalog data)

## What does NOT migrate automatically

- **Institution assignments** — institutions differ per country; run `/setup-institutions` after migration
- **Bot configurations** — external service URLs differ per country; reconfigure with `/bot-mappings`
- **Translations** — must be re-done if target uses a different language
- **Active users/applications** — production data stays on source

## Migration flow

1. **Export** full service from source: `mcp__BPA__service_export_raw(instance="<source>")`
2. **Validate** export is complete and parseable
3. **Pre-flight check on target**: verify target is reachable, user is authenticated
4. **Dry-run report** (always shown): list components to be created, flag potential conflicts
5. **Confirm** before writing (skip with `--force`)
6. **Create** service on target via `mcp__BPA__service_copy(instance="<target>")` or component-by-component
7. **Verify** by running `mcp__BPA__debug_scan(instance="<target>")` on the new service
8. **Report**: new service ID on target, list of components that need manual follow-up

## Usage

```
/migrate-service 42 jamaica lesotho2 --dry-run
/migrate-service 42 jamaica lesotho2
/migrate-service 17 elsalvador-dev investkenya
```
