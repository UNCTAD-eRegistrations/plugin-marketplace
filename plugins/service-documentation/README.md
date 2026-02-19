# service-documentation

All documentation generation tools for eRegistrations BPA services.

## Commands

| Command | Description |
|---------|-------------|
| `/service-manual <id> [instance]` | Generate citizen-facing HTML manual for one service |
| `/service-manual-all [instance]` | Batch-generate manuals for all services + catalog index |
| `/eregistrations-docs [id] [instance]` | Export service data to Excel workbook |

## Bundled Skills

| Skill | Mirrors |
|-------|---------|
| `service-manual` | `skills/service-manual` |
| `service-manual-all` | `skills/service-manual-all` |
| `eregistrations-docs` | `skills/eregistrations-docs` |

> Skills in this plugin are kept in sync with `skills/` via `scripts/sync-skills.sh`.

## Excel Report Sheets

The `/eregistrations-docs` command produces `service-{id}-docs.xlsx` with:
- **Fields** — all form fields with types, labels, validation
- **Determinants** — conditional logic rules
- **Roles** — processing roles and status transitions
- **Bots** — automation bots and mapping coverage
- **Costs** — fixed and formula-based fees
- **Document Requirements** — required documents per registration

## Requirements

- `mcp-eregistrations-bpa` installed (see repo root README)
- `python3` + `openpyxl` for `/eregistrations-docs`
