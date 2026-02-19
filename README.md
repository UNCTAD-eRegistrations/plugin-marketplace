# UNCTAD eRegistrations Plugin Marketplace

Official Claude Code plugins for UNCTAD's eRegistrations platform, supporting BPA service development across all types of government services: business registration, permits, social protection, health, environment, tax, and more.

> **Note:** Only install plugins from trusted sources. Verify each plugin before installation.

## Structure

- **`/plugins`** — Claude Code plugins maintained by UNCTAD
- **`/scripts`** — Utility scripts (`migrate-to-multi-instance.py`, `sync-skills.sh`)

## Installing Plugins

First, register this marketplace in your Claude Code settings:

```json
{
  "pluginMarketplaces": [
    "https://raw.githubusercontent.com/UNCTAD-eRegistrations/plugin-marketplace/main/.claude-plugin/marketplace.json"
  ]
}
```

Then install plugins by name:

```bash
/plugin install bpa-instances@unctad-digital-government
/plugin install service-builder@unctad-digital-government
```

Or browse via `/plugin > Discover`.

## Available Plugins

| Plugin | Category | Description |
|--------|----------|-------------|
| `bpa-instances` | integration | MCP connections for all BPA instances (install first) |
| `service-documentation` | documentation | Citizen-facing HTML manuals and Excel exports |
| `service-testing` | development | 4-suite validation and quality scoring (0–100) |
| `service-builder` | development | Design and build new eRegistrations services |
| `service-migration` | development | Copy services between instances with diff and dry-run |
| `bpa-debug` | debugging | Scan, investigate, and fix BPA service issues |
| `role-configurator` | development | Design multi-agency role and workflow structures |
| `institution-setup` | administration | Configure institutions and deployment wizard |
| `bot-mappings` | integration | AI-powered bot field mapping and validation |
| `workflow-manager` | workflow | Execute and monitor BPA workflow orchestrations |
| `notification-designer` | development | Email, SMS, and push notification templates |
| `classification-manager` | data | Manage classification catalogs and country codes |
| `data-import` | data | Bulk CSV/Excel import for classifications, costs, requirements |
| `print-document-builder` | development | Design certificates, licenses, and permits |

## Plugin Structure

Each plugin follows this convention:

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json       # Plugin metadata (required)
├── commands/             # Slash commands (optional)
├── agents/               # Agent definitions (optional)
├── skills/               # Skill definitions (optional)
└── README.md             # Documentation
```

## Getting Started

All plugins require the `bpa-instances` plugin and an authenticated BPA connection:

```bash
# 1. Install the BPA MCP server binary first
uv tool install ./MCP_eRegistrations_BPA

# 2. Register all known country instances (run once)
/bpa-setup

# 3. Authenticate to the instance(s) you need
/bpa-login jamaica
/bpa-login lesotho2
```

See the [`bpa-instances` plugin README](./plugins/bpa-instances/README.md) for full setup instructions and a list of all available instance profiles.

## Upgrading from the multi-server setup

If you have `BPA-jamaica`, `BPA-lesotho2`, etc. in your MCP config, run the migration script:

```bash
# Dry run first
uv run scripts/migrate-to-multi-instance.py

# Apply when ready
uv run scripts/migrate-to-multi-instance.py --apply
```

## Contributing

See [CLAUDE.md](./CLAUDE.md) for conventions and contribution guidelines.
