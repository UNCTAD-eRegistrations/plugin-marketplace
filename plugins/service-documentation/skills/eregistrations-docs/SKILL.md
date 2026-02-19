---
name: eregistrations-docs
description: >
  Analyzes a BPA service JSON export and generates structured Excel reports covering
  fields, determinants, roles, bots, and costs. Use when the user wants to document,
  analyze, audit, or export a BPA service configuration.
license: UNCTAD-Internal
compatibility: Requires an authenticated BPA MCP server connection. Python 3.x and openpyxl must be installed (pip install openpyxl).
allowed-tools: Bash(python3 *), Read, Write
metadata:
  version: "1.4.0"
  version-date: "2026-02-19"
  author: "Frank Grozel (gfrankgva)"
  disable-model-invocation: "true"
---

# eRegistrations Service Documenter

## When to Use
- User wants to analyze a BPA service configuration
- User needs an Excel/report of a service's forms, fields, determinants, roles
- User says "document service", "analyze service", "export service"

## Resources
- `scripts/service_analyzer.py` -- Python script (17KB) that parses BPA service JSON exports
- `resources/` -- Place reference files and templates here

## Procedure

### Step 1: Get the Service Export
Use BPA MCP tools to export the service:
```
service_export_raw(service_id=...)
```
Or the user may provide a JSON file directly.

### Step 2: Analyze
Run the service analyzer script on the export:
```bash
python3 scripts/service_analyzer.py <export.json> --output report.xlsx
```

The script extracts:
- Service metadata (name, description, status)
- Form components and field inventory
- Determinants and their conditions
- Roles and workflow transitions
- Bots and integrations
- Document requirements
- Costs

### Step 3: Deliver
- Provide the Excel report to the user
- Summarize key findings (field count, complexity, issues found)
- Optionally generate a YAML representation via `service_to_yaml()`

## Discovering Available BPA Instances

If you don't know which BPA MCP server to use:

1. Look at your available tools for any namespace that has a `server_info` tool.
   Pattern to match: `mcp__{name}__server_info`
2. Call `server_info` on each — no authentication required.
3. Present the list to the user and ask which instance to use.

## Notes
- Refer to the `rosetta-stone.md` in your workspace AI guides for BPA terminology

## Changelog

- 1.4.0 (2026-02-19) gfrankgva — Discovery via server_info tool; dropped ! injection and config file parsing
- 1.3.0 (2026-02-19) gfrankgva — Generic BPA MCP discovery via ! injection; removed hardcoded server names
- 1.2.0 (2026-02-19) gfrankgva — disable-model-invocation true; added allowed-tools; fixed MCP server names; removed stale path reference
- 1.1.0 (2026-02-19) gfrankgva — Added version metadata
- 1.0.0 (2026-01-15) gfrankgva — Initial skill with service_analyzer.py
