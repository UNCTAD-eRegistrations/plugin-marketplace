---
description: Authenticate to one or more BPA instances
argument-hint: <instance-name> [instance-name ...]
allowed-tools: [Bash]
---

# BPA Login

Authenticate to BPA instance(s): `$ARGUMENTS`

## Instructions

Parse arguments as a list of instance names (e.g., `jamaica lesotho2`).
If no arguments, prompt the user to choose from the configured instances.

For each instance, call `auth_login` via `mcp__BPA-<name>__auth_login`.

- **Keycloak instances**: opens a browser for PKCE login — no password needed
- **CAS instances**: requires `BPA_<NAME>_CLIENT_SECRET` env var to be set

After each login attempt, call `connection_status` to confirm success.

Report result:
```
BPA-jamaica  ✅ Authenticated as user@example.com (token expires in 2h)
BPA-lesotho2 ❌ Login failed: browser timeout
```

## Usage

```
/bpa-login jamaica
/bpa-login jamaica lesotho2 nigeria
```
