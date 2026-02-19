---
description: Import classification catalog entries from a CSV or Excel file
argument-hint: <file-path> [mcp-server] [--catalog-id <id> | --create <name>]
allowed-tools: [Read, Write, Bash]
---

# Classification Importer

Import classification data from `$ARGUMENTS`.

## Arguments

- First: path to CSV or Excel file (required)
- Second: MCP server (optional)
- `--catalog-id <id>`: import into an existing catalog
- `--create <name>`: create a new catalog with this name and import into it

## Expected File Format

**CSV:**
```
code,label,description
JM,Jamaica,
LS,Lesotho,Kingdom of Lesotho
NG,Nigeria,Federal Republic of Nigeria
```

**Excel:** same columns, first row is header. Supports `.xlsx` and `.xls`.

## Flow

1. Read and validate the file (check for required columns `code` and `label`)
2. Preview: show first 5 rows, total count, any validation errors
3. Confirm before writing
4. If `--create`: call `classification_create` to make the catalog first
5. For each row: call `classification_update` or equivalent to add entries
6. After import: call `classification_get` to verify entry count matches

## Error Handling

- Duplicate codes: skip with warning
- Missing labels: skip with error
- Invalid characters: sanitize and warn

## Usage

```
/import-classifications ./data/countries.csv BPA-jamaica --create "Country Codes"
/import-classifications ./data/sectors.xlsx BPA-lesotho2 --catalog-id 12
```
