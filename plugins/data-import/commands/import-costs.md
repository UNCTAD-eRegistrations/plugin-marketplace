---
description: Bulk-import cost structures into a BPA service from a structured file
argument-hint: <file-path> <service-id> [mcp-server]
allowed-tools: [Read, Write, Bash]
---

# Cost Structure Importer

Import costs for service `$ARGUMENTS`.

## Arguments

- First: path to CSV or Excel file (required)
- Second: service ID (required)
- Third: MCP server (optional)

## Expected File Format

**CSV:**
```
registration_name,cost_name,type,amount,currency,formula
New Registration,Application Fee,fixed,50,USD,
New Registration,Processing Fee,formula,,,fee_base * applicant_category_multiplier
Renewal,Renewal Fee,fixed,25,USD,
```

- `type`: `fixed` or `formula`
- `amount` + `currency`: required for `fixed`
- `formula`: required for `formula` type

## Flow

1. Read and validate file
2. For each row:
   - Match registration_name to existing registrations
   - If `type=fixed`: `cost_create_fixed` (registration_id, name, amount, currency)
   - If `type=formula`: `cost_create_formula` (registration_id, name, formula)
3. Report: N costs created, N errors

## Usage

```
/import-costs ./data/fees.csv 42 BPA-jamaica
```
