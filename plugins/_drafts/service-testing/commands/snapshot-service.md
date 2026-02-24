---
description: Save or compare a snapshot of a BPA service for regression testing
argument-hint: <service-id> [instance] [--compare | --diff]
allowed-tools: [Read, Write, Bash]
---

# Service Snapshot

Snapshot BPA service `$ARGUMENTS` for regression testing.

## Arguments

- First token: service ID (required)
- Second token: instance profile name (optional)
- `--compare`: compare current state against last saved snapshot
- `--diff`: show detailed diff between current and snapshot

## Default behavior (no flags)

Save a snapshot of the current service state:
1. Export full service via `service_to_yaml`
2. Save to `./output/snapshots/<instance>/<service-id>-<timestamp>.yaml`
3. Update `./output/snapshots/<instance>/<service-id>-latest.yaml`
4. Report: timestamp, field count, determinant count, role count

## With `--compare`

Compare current state against the latest snapshot:
1. Export current state via `service_to_yaml`
2. Load `./output/snapshots/<instance>/<service-id>-latest.yaml`
3. Run structural diff (fields added/removed, determinants changed, roles modified)
4. Report summary: N added, N removed, N modified, N unchanged

## With `--diff`

Same as `--compare` but show full unified diff of the YAML.

## Use case

Run `/snapshot-service <id>` before making changes, then `/snapshot-service <id> --compare` after, to verify only intended changes were made.

## Usage

```
/snapshot-service 42 jamaica
/snapshot-service 42 jamaica --compare
/snapshot-service 42 --diff
```
