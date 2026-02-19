# bpa-instances

Configure Claude Code MCP connections for all eRegistrations BPA deployments.

**Install this plugin first** — all other UNCTAD plugins require an active BPA MCP connection.

## What this installs

When installed, this plugin adds all BPA instance MCP servers to your Claude Code config:

| Server name | Country | URL |
|-------------|---------|-----|
| `BPA-nigeria` | Nigeria | `bpa.gateway.nipc.gov.ng` |
| `BPA-elsalvador-dev` | El Salvador (Dev) | `bpa.dev.els.eregistrations.org` |
| `BPA-kenya-test` | Kenya (Test) | `bpa.test.kenya.eregistrations.org` |
| `BPA-investkenya` | Kenya (InvestKenya) | `bpa.investkenya.go.ke` |
| `BPA-cuba-test` | Cuba (Test) | `bpa.test.cuba.eregistrations.org` |
| `BPA-cuba` | Cuba | `bpa.cuba.eregistrations.org` |
| `BPA-jamaica` | Jamaica | `bpa.jamaica.eregistrations.org` |
| `BPA-lesotho2` | Lesotho | `bpa.businessregistrations.gov.ls` |
| `BPA-colombia-test` | Colombia (Test) | `bpa.test.colombia.eregistrations.org` |
| `BPA-gambia` | Gambia | `bpa.easybusiness.gov.gm` |
| `BPA-bhutan-staging` | Bhutan (Staging) | `bpa.stagingibls.moea.gov.bt` |

## Commands

| Command | Description |
|---------|-------------|
| `/bpa-status [instance]` | Check connection status for all or one instance |
| `/bpa-login <instance> [...]` | Authenticate to one or more instances |

## Prerequisites

### 1. Install the MCP server

```bash
uv tool install ./MCP_eRegistrations_BPA
```

Verify: `mcp-eregistrations-bpa --version`

### 2. Set CAS secrets (Cuba only)

Cuba instances use CAS authentication and need a client secret:

```bash
# Add to ~/.zshrc or ~/.bashrc
export BPA_CUBA_TEST_CLIENT_SECRET=<secret>
export BPA_CUBA_CLIENT_SECRET=<secret>
```

### 3. Authenticate

Keycloak instances (all others) use browser-based PKCE — no password needed:

```
/bpa-login jamaica
```

## Regenerating .mcp.json

If instances are added or URLs change, regenerate:

```bash
uv run --with pyyaml scripts/generate-mcp-json.py
```

Then reinstall this plugin to pick up the changes.
