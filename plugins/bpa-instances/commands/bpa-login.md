---
description: Authenticate to one or more BPA instances
argument-hint: <instance-name> [instance-name ...]
allowed-tools: [Bash]
---

# BPA Login

Authenticate to BPA instance(s): `$ARGUMENTS`

## Instructions

Parse arguments as a list of instance names (e.g., `jamaica lesotho2`).
If no arguments, call `instance_list` and prompt the user to choose.

For each instance, call `mcp__BPA__auth_login(instance="<name>")`.

- **Keycloak instances**: opens a browser for PKCE login — no password needed
- **CAS instances**: credentials were stored in the profile during `/bpa-setup`

After each login attempt, call `mcp__BPA__connection_status(instance="<name>")` to confirm success.

Report result:
```
jamaica  ✅ Authenticated as user@example.com (token expires in 2h)
lesotho2 ❌ Login failed: browser timeout
```

## Usage

```
/bpa-login jamaica
/bpa-login jamaica lesotho2 nigeria
```
