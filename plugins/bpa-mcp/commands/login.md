---
description: Authenticate to one or more eRegistrations instances
argument-hint: <instance-name> [instance-name ...]
effort: low
allowed-tools: [Bash]
---

# Login

Authenticate to eRegistrations instance(s): `$ARGUMENTS`

## Instructions

Parse arguments as a list of instance names (e.g., `jamaica lesotho2`).
If no arguments, call `instance_list` and prompt the user to choose.

For each instance, call `mcp__BPA__auth_login(instance="<name>")`.

- **Stored credentials** (default): If the user has previously logged in, credentials are stored in `~/.config/mcp-eregistrations-bpa/auth.json` and used automatically via password grant. No browser, no prompts.
- **First-time login**: Ask the user for username and password, then call `auth_login(instance="<name>", username="...", password="...")`. Credentials are stored for future auto-login.
- **Browser login**: Falls back to OIDC browser login only if no credentials are available and no password is provided.

Credentials are shared across all eRegistrations MCP servers (BPA, GDB, DS). Login once, everything works.

After each login attempt, call `connection_status(instance="<name>")` to confirm success.

Report result:
```
jamaica   Authenticated as user@example.com (token expires in 2h)
lesotho2  Login failed: no credentials
```

## Usage

```
/bpa-mcp:login jamaica
/bpa-mcp:login jamaica lesotho2 nigeria
```
