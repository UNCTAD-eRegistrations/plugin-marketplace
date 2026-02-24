> **DRAFT** — This plugin was AI-generated and has not been verified against a live BPA instance. Tool names, parameters, and workflows may be outdated or incorrect.

# data-import

Import bulk data into BPA from CSV or Excel files.

## Commands

| Command | Description |
|---------|-------------|
| `/import-classifications <file> [--catalog-id <id> \| --create <name>]` | Import catalog entries |
| `/import-requirements <file> <service-id>` | Bulk-import document requirements |
| `/import-costs <file> <service-id>` | Bulk-import cost structures |

## Skills

| Skill | Description |
|-------|-------------|
| `data-import-patterns` | File reading patterns, validation rules, idempotency, templates |

## File templates

Download blank templates to fill in:

| Template | Columns |
|----------|---------|
| `classifications-template.csv` | `code, label, description` |
| `requirements-template.csv` | `registration_name, document_name, description, mandatory, original_required` |
| `costs-template.csv` | `registration_name, cost_name, type, amount, currency, formula` |

## Requirements

- `python3` + `openpyxl` for Excel files (`.xlsx`)
- CSV files work with no extra dependencies
