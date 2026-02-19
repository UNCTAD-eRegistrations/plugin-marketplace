---
description: Check connection status for all configured BPA instances
argument-hint: [instance-name]
allowed-tools: [Bash]
---

# BPA Instance Status

Check connectivity and auth status for BPA instances. `$ARGUMENTS`

## Instructions

If an instance name is given, check only that instance.
Otherwise check all configured instances in parallel.

For each instance, call `connection_status` via the corresponding MCP server (`BPA-<name>`).

Report a table:

```
Instance          | URL                                        | Auth   | Status
BPA-jamaica       | https://bpa.jamaica.eregistrations.org     | OIDC   | ✅ Authenticated (expires 2h)
BPA-lesotho2      | https://bpa.businessregistrations.gov.ls   | OIDC   | ❌ Not authenticated
BPA-nigeria       | https://bpa.gateway.nipc.gov.ng            | OIDC   | ✅ Authenticated (expires 45m)
BPA-cuba          | https://bpa.cuba.eregistrations.org        | CAS    | ⚠️  Secret not set
```

For unauthenticated instances, show: "Run `mcp__BPA-<name>__auth_login` to authenticate."

## Usage

```
/bpa-status
/bpa-status jamaica
```
