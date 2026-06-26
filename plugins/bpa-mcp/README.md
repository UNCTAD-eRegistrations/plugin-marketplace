# bpa-mcp

Install the BPA MCP server and register eRegistrations instance profiles.

**Install this plugin first** — all other UNCTAD plugins require an active BPA MCP connection.

## What this installs

A single `BPA` MCP server. Instance profiles are managed via `/bpa-mcp:install` after install.

## Commands

| Command | Description |
|---------|-------------|
| `/bpa-mcp:install [instance]` | Install the MCP server and register instance profiles (all or one) |
| `/bpa-mcp:status [instance]` | Check connection status for all or one instance |
| `/bpa-mcp:login <instance> [...]` | Authenticate to one or more instances |
| `/bpa-mcp:doctor` | Diagnose and fix common MCP server issues |
| `/bpa-mcp:issue [description]` | Report a tool issue or unexpected behavior |
| `/bpa-mcp:ereg-issue [description]` | Report an eRegistrations runtime/deployment issue — standardized & pre-qualified into a qualified-ticket (sibling of `mcp-issue`) |

## Prerequisites

### 1. Install `uv` (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The MCP server is auto-downloaded via `uvx` when the plugin starts — no manual `uv tool install` needed.

### 2. Install this plugin and register instances

```
/bpa-mcp:install              # register all known profiles
/bpa-mcp:install lesotho2     # register only lesotho2
```

This registers deployments as named profiles. Run once — profiles persist across sessions.

### 3. Authenticate

Provide credentials on first login. Auto-login on all subsequent sessions:

```
/bpa-mcp:login jamaica
```

**Auto-login:** Credentials stored locally for silent password grant. No browser, no keychain. Shared across BPA, GDB, DS.

CAS instances (Cuba) require providing client credentials during `/bpa-mcp:install`.

## Instance profiles

After running `/bpa-mcp:install`, the following profiles are available:

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

Or run `/bpa-mcp:install` — it automatically detects old entries and offers to migrate them (Step 2.5).

This removes all `BPA-*` entries, adds the single `BPA` entry, and creates named instance profiles. Restart Claude after migration to pick up the new config.

## Adding or removing instances

```
/bpa-mcp:install                     # register all known profiles (slash command)
mcp__BPA__instance_add           # add a custom profile
mcp__BPA__instance_remove        # remove a profile
mcp__BPA__instance_list          # list all registered profiles
```
