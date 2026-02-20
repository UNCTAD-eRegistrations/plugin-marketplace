# bpa-mcp

Install the BPA MCP server and register eRegistrations instance profiles.

**Install this plugin first** — all other UNCTAD plugins require an active BPA MCP connection.

## What this installs

A single `BPA` MCP server. Instance profiles are managed via `/bpa-install` after install.

## Commands

| Command | Description |
|---------|-------------|
| `/bpa-install [instance]` | Install the MCP server and register instance profiles (all or one) |
| `/bpa-status [instance]` | Check connection status for all or one instance |
| `/bpa-login <instance> [...]` | Authenticate to one or more instances |

## Prerequisites

### 1. Install the MCP server

```bash
uv tool install mcp-eregistrations-bpa
```

Verify: `command -v mcp-eregistrations-bpa`

### 2. Install this plugin and register instances

```
/bpa-install              # register all known profiles
/bpa-install lesotho2     # register only lesotho2
```

This registers deployments as named profiles. Run once — profiles persist across sessions.

### 3. Authenticate

Keycloak instances (most countries) use browser-based PKCE — no password needed:

```
/bpa-login jamaica
```

CAS instances (Cuba) require providing client credentials during `/bpa-install`.

## Instance profiles

After running `/bpa-install`, the following profiles are available:

| Profile name | Country | URL |
|--------------|---------|-----|
| `nigeria` | Nigeria | `bpa.gateway.nipc.gov.ng` |
| `elsalvador-dev` | El Salvador (Dev) | `bpa.dev.els.eregistrations.org` |
| `kenya-test` | Kenya (Test) | `bpa.test.kenya.eregistrations.org` |
| `investkenya` | Kenya (InvestKenya) | `bpa.investkenya.go.ke` |
| `cuba-test` | Cuba (Test) | `bpa.test.cuba.eregistrations.org` |
| `cuba` | Cuba | `bpa.cuba.eregistrations.org` |
| `jamaica` | Jamaica | `bpa.jamaica.eregistrations.org` |
| `lesotho2` | Lesotho | `bpa.businessregistrations.gov.ls` |
| `colombia-test` | Colombia (Test) | `bpa.test.colombia.eregistrations.org` |
| `gambia` | Gambia | `bpa.easybusiness.gov.gm` |
| `bhutan-staging` | Bhutan (Staging) | `bpa.stagingibls.moea.gov.bt` |

## Upgrading from the old multi-server setup

If you previously installed this plugin and have `BPA-nigeria`, `BPA-jamaica`, etc. in your config, run the migration script from the marketplace repo root:

```bash
# Dry run first (shows what will change)
uv run scripts/migrate-to-multi-instance.py

# Apply when ready
uv run scripts/migrate-to-multi-instance.py --apply
```

This removes all `BPA-*` entries and adds the single `BPA` entry in both your project `.mcp.json` and Claude Desktop config. Then run `/bpa-install` to re-register all instance profiles.

## Adding or removing instances

```
/bpa-install                     # register all known profiles (slash command)
mcp__BPA__instance_add           # add a custom profile
mcp__BPA__instance_remove        # remove a profile
mcp__BPA__instance_list          # list all registered profiles
```
