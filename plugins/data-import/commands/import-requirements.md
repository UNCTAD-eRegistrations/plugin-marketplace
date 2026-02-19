---
description: Bulk-import document requirements into a BPA service from a structured file
argument-hint: <file-path> <service-id> [mcp-server]
allowed-tools: [Read, Write, Bash]
---

# Document Requirements Importer

Import document requirements from `$ARGUMENTS`.

## Arguments

- First: path to CSV or Excel file (required)
- Second: service ID (required)
- Third: MCP server (optional)

## Expected File Format

**CSV:**
```
registration_name,document_name,description,mandatory,original_required
New Registration,National ID,Government-issued photo ID,true,false
New Registration,Proof of Address,Utility bill or bank statement,true,false
Renewal,Previous Certificate,Copy of current certificate,true,true
```

## Flow

1. Read and validate the file
2. List existing registrations for the service: `registration_list`
3. Match `registration_name` column to existing registrations (fuzzy match, ask to confirm)
4. For each row: create `documentrequirement_create` (registration_id, requirement_name, mandatory, original_required)
5. Report: N requirements created, N skipped (already exist), N errors

## Deduplication

Before creating, check `documentrequirement_list` for the registration.
Skip if a requirement with the same name already exists (warn the user).

## Usage

```
/import-requirements ./data/requirements.csv 42 BPA-jamaica
/import-requirements ./requirements.xlsx 17 BPA-lesotho2
```
