# UNCTAD eRegistrations Plugin Marketplace

AI plugins for eRegistrations service design. Each plugin bundles skills, agents, and slash commands that empower service designers to design and maintain digital government services through agentic AI — covering design, testing, debugging, and documentation.

## How it works

The **BPA MCP server** connects Claude directly to any eRegistrations instance — giving it real-time access to services, forms, roles, bots, determinants, and every other BPA resource. It is the professional kitchen: the tools, the ingredients, the live connection to the platform.

The **skills** are the recipes. They encode UNCTAD service design knowledge — workflows, quality standards, best practices — so Claude knows not just *what* it can do, but *how* to do it well.

The **agents** handle complex, multi-step tasks autonomously: designing a full service from scratch, running a 4-suite test battery, migrating a service between country instances. They orchestrate skills and MCP calls in the right order, with the right checks.

The **slash commands** are the entry points: a single `/service-test`, `/bpa-debug`, or `/service-doc` invocation hands control to the appropriate agent and delivers the result.

Together, they turn Claude into a specialist service designer — one that understands the BPA data model, speaks the eRegistrations vocabulary, and can execute the full service lifecycle without hand-holding.

## Installing Plugins

First, register this marketplace in your Claude Code settings:

```json
{
  "extraKnownMarketplaces": {
    "unctad-digital-government": {
      "source": {
        "source": "github",
        "repo": "UNCTAD-eRegistrations/plugin-marketplace"
      }
    }
  }
}
```

Or via the CLI:

```bash
/plugin marketplace add UNCTAD-eRegistrations/plugin-marketplace
```

Then install plugins by name:

```bash
/plugin install bpa-mcp@unctad-digital-government
/plugin install service-builder@unctad-digital-government
```

Or browse via `/plugin > Discover`.

## Available Plugins

| Plugin | Category | Description |
|--------|----------|-------------|
| `bpa-mcp` | integration | MCP connections for all BPA instances (install first) |
| `service-documentation` | documentation | Citizen-facing HTML manuals and Excel exports |
| `service-testing` | design | 4-suite validation and quality scoring (0–100) |
| `service-builder` | design | Design and build new eRegistrations services |
| `service-migration` | design | Copy services between instances with diff and dry-run |
| `bpa-debug` | debugging | Scan, investigate, and fix BPA service issues |
| `role-configurator` | design | Design multi-agency role and workflow structures |
| `institution-setup` | administration | Configure institutions and deployment wizard |
| `bot-mappings` | integration | AI-powered bot field mapping and validation |
| `workflow-manager` | workflow | Execute and monitor BPA workflow orchestrations |
| `notification-designer` | design | Email, SMS, and push notification templates |
| `classification-manager` | data | Manage classification catalogs and country codes |
| `data-import` | data | Bulk CSV/Excel import for classifications, costs, requirements |
| `print-document-builder` | design | Design certificates, licenses, and permits |

## Plugin Structure

Each plugin follows this convention:

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json       # Plugin metadata (required)
├── skills/               # Skill definitions (optional)
├── agents/               # Agent definitions (optional)
├── commands/             # Slash commands (optional)
└── README.md             # Documentation
```

## Getting Started

All plugins require the `bpa-mcp` plugin and an authenticated BPA connection:

```bash
# 1. Install the BPA MCP server binary first
uv tool install mcp-eregistrations-bpa

# 2. Register all known country instances (run once)
/bpa-install

# 3. Authenticate to the instance(s) you need
/bpa-login jamaica
/bpa-login lesotho2
```

See the [`bpa-mcp` plugin README](./plugins/bpa-mcp/README.md) for full setup instructions and a list of all available instance profiles.

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
