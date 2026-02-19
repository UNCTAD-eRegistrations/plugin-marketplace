# UNCTAD Digital Government — Software Factory

Official plugin marketplace and tools for UNCTAD's digital government platform, supporting eRegistrations deployments across all types of government services: business registration, permits, social protection, health, environment, tax, and more.

> **Note:** Only install plugins from trusted sources. Verify each plugin before installation.

## Structure

- **`/plugins`** — Claude Code plugins maintained by UNCTAD
- **`/skills`** — Claude Code skills (Agent Skills spec, for direct installation)
- **`/scripts`** — Utility scripts (MCP config generation, skills sync)

## Installing Plugins

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

## BPA MCP Servers

Plugins require an authenticated BPA MCP server. Install `bpa-instances` first, then authenticate:

```bash
/bpa-login BPA-jamaica
/bpa-login BPA-lesotho2
```

## Contributing

For the skills spec, see [skills/CLAUDE.md](./skills/CLAUDE.md).
