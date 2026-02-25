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

### 1. Install `uv` (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The MCP server is auto-downloaded via `uvx` when the plugin starts — no manual `uv tool install` needed.

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

**Auto-login (optional):** During `/bpa-install`, you can provide credentials to enable transparent auto-login — no browser interaction or explicit `/bpa-login` needed. Credentials are stored securely in the OS keyring. Refresh tokens also persist across sessions automatically.

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

If you previously had per-country `BPA-nigeria`, `BPA-jamaica`, etc. entries, the migration is built into the server:

```bash
# Dry run first (shows what will change)
mcp-eregistrations-bpa migrate

# Apply when ready
mcp-eregistrations-bpa migrate --apply
```

Or run `/bpa-install` — it automatically detects old entries and offers to migrate them (Step 2.5).

This removes all `BPA-*` entries, adds the single `BPA` entry, and creates named instance profiles. Restart Claude after migration to pick up the new config.

## Adding or removing instances

```
/bpa-install                     # register all known profiles (slash command)
mcp__BPA__instance_add           # add a custom profile
mcp__BPA__instance_remove        # remove a profile
mcp__BPA__instance_list          # list all registered profiles
```
