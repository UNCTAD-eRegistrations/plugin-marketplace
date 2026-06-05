# eregulations

Deployment and operations skills for **eRegulations / TradePortal** instances — the
UNCTAD procedure-**documentation** portal.

> ⚠️ This is a different product from **eRegistrations** (the BPA transactional
> platform). eRegistrations deployment lives in the `devops` plugin; the MCP servers
> (`bpa-mcp`, `ds-mcp`, `gdb-mcp`, …) target eRegistrations too. Don't mix them up.

## Skills

| Skill | Status | Description |
|-------|--------|-------------|
| `deploy-eregulations-instance` | 🚧 draft (0.1.0) | Runbook for deploying an eRegulations instance — server prep, admin back-office, public front-end, cleanup, and running multiple instances on shared databases. |

## Status

This plugin starts from the **`admin.pilot.tradeportal.org`** reference deployment.
The `deploy-eregulations-instance` skill is a scaffold being filled in from that
experience — see the FILL markers inside its `SKILL.md`. It reaches `1.0.0` once the
admin + public + multi-instance phases are captured and tested.

## Contributing

- Bump `metadata.version` in `SKILL.md` (and `version` in `plugin.json`) on every
  meaningful change, and add a Changelog entry.
- Keep secrets out of the repo — reference where they live, never the values.
- New skills here must also be registered in the root `.claude-plugin/marketplace.json`.
