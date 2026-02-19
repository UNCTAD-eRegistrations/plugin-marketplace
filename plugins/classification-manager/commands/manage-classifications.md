---
description: Create, manage, and export BPA classification catalogs
argument-hint: [action] [classification-id] [instance]
allowed-tools: [Read, Write, Bash]
---

# Classification Manager

Manage BPA classification catalogs. `$ARGUMENTS`

## Instructions

Parse arguments:
- First token: action (`list`, `get`, `create`, `export`, `country-codes`) — default: `list`
- Second token: classification ID (for `get`, `export`)
- Third token: instance profile name (optional)

### Actions

**`list`** — Show all catalogs with entry counts and last modified dates

**`get <id>`** — Display catalog entries in a readable table

**`create`** — Interactive: prompt for name, description, and initial entries, then create via `classification_create`

**`export <id>`** — Export catalog as CSV via `classification_export_csv`, save to `./output/classifications/`

**`country-codes`** — Apply ISO 3166-1 country codes to all applicable catalogs via `classification_apply_country_codes`

## Usage

```
/manage-classifications list jamaica
/manage-classifications get 5 lesotho2
/manage-classifications export 12
/manage-classifications country-codes jamaica
```
