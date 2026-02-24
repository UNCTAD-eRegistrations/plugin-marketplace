---
description: Check connection status for all configured BPA instances
argument-hint: [instance-name]
allowed-tools: [Bash]
---

# BPA Instance Status

Check connectivity and auth status for BPA instances. `$ARGUMENTS`

## Instructions

If an instance name is given, check only that instance.
Otherwise call `instance_list` first to discover all registered profiles, then check each in parallel.

For each instance, call `mcp__BPA__connection_status(instance="<name>")`.

Report a table:

```
Instance       | URL                                        | Auth   | Status
jamaica        | https://bpa.jamaica.eregistrations.org     | OIDC   | ✅ Authenticated (expires 2h)
lesotho2       | https://bpa.businessregistrations.gov.ls   | OIDC   | ❌ Not authenticated
nigeria        | https://bpa.gateway.nipc.gov.ng            | OIDC   | 🔑 Auto-login ready (stored credentials)
cuba           | https://bpa.cuba.eregistrations.org        | CAS    | ❌ Not authenticated
```

- If `auto_login_available` is true and not currently authenticated, show "Auto-login ready" — credentials exist and will activate on first tool call.
- For unauthenticated instances without auto-login, show: "Run `/bpa-login <name>` to authenticate."

## Usage

```
/bpa-status
/bpa-status jamaica
```
