# Graylog MCP — Log Search & Monitoring

MCP tools for searching and monitoring Graylog logs across eRegistrations instances.

## Prerequisites

Install the **bpa-mcp** plugin first — it provides instance management that Graylog depends on.

## Important: Authentication

Graylog uses its **own auth system** (Basic Auth or API tokens), **NOT Keycloak**. BPA/DS/GDB credentials will not work. You need separate Graylog admin credentials or an API token for each instance.

## Tools (6)

### System & Auth
- `graylog_connection_status` — Test connectivity and show Graylog version
- `graylog_system_info` — Detailed system info (version, cluster, status)
- `graylog_auth_login` — Authenticate with Graylog credentials

### Streams
- `graylog_stream_list` — List all log streams
- `graylog_stream_get` — Get detailed stream info

### Search
- `graylog_search_logs` — Search logs with Elasticsearch syntax

## Commands

| Command | Description |
|---------|-------------|
| `/graylog-mcp:status [instance]` | Check Graylog connectivity and version |
| `/graylog-mcp:issue [description]` | Report a tool issue or unexpected behavior |

## Quick Start

```
# 1. Authenticate (Graylog credentials, NOT Keycloak)
graylog_auth_login(username="admin", password="...", instance="cuba")

# 2. Search recent logs
graylog_search_logs(query="*", time_range="15m", instance="cuba")

# 3. Search for errors
graylog_search_logs(query="level:3", time_range="1h", instance="cuba")

# 4. Search bot execution logs
graylog_search_logs(query="app_name:Mule AND serviceName:\"Bitacora\"", time_range="24h", instance="cuba")
```

## Common Queries

| Query | Description |
|-------|-------------|
| `*` | All logs |
| `level:3` | Errors only (syslog: 3=error, 4=warning, 6=info) |
| `app_name:Mule` | Mule/bot execution logs |
| `app_name:GDB` | GDB backend logs |
| `app_name:DataWeave` | DataWeave transformation logs |
| `app_name:Mule AND serviceId:"<id>"` | Logs for a specific service |
| `app_name:Mule AND actionName:"<name>"` | Logs for a specific bot action |
| `user:"<username>"` | Logs for a specific user |

## Key Log Fields

`message`, `level`, `app_name`, `serviceName`, `serviceId`, `actionId`, `actionName`, `user`, `inputData`, `outputData`, `source`, `timestamp`.

## Instances with Graylog

Not all eRegistrations instances have Graylog configured. Known instances:

| Instance | Graylog URL |
|----------|-------------|
| nigeria | `graylog.gateway.nipc.gov.ng` |
| cuba-dev | `graylog.dev.cuba.eregistrations.org` |
| cuba | `graylog.cuba.eregistrations.org` |
| kenya-test | `graylog.test.kenya.eregistrations.org` |
| investkenya | `graylog.investkenya.go.ke` |
| colombia-test | `graylog.test.colombia.eregistrations.org` |
| bhutan-staging | `graylog.stagingibls.moea.gov.bt` |

If your instance doesn't have a Graylog URL, add one:

```
graylog_instance_add(name="jamaica", graylog_url="https://graylog.jamaica.eregistrations.org")
```

## Auth Methods

### Admin credentials
```
graylog_auth_login(username="admin", password="secret", instance="cuba")
```

### API token (recommended for automation)
```
graylog_auth_login(username="<token-value>", password="token", instance="cuba")
```

API tokens can be created in Graylog UI under System > Users > Edit user > Tokens.
