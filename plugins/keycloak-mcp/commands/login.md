---
description: Authenticate to a Keycloak instance with admin credentials
argument-hint: <instance-name>
allowed-tools: []
---

# Keycloak Login

Authenticate to a Keycloak instance with admin-level credentials: `$ARGUMENTS`

## Instructions

Parse arguments as an instance name. If no arguments, ask the user which instance to authenticate to.

**Important:** Keycloak Admin API requires credentials for a user with `realm-management` roles (manage-users, manage-realm, view-realm). This is typically a Keycloak admin account, not a regular BPA user.

### Step 1 — Collect credentials

Ask the user for their Keycloak admin credentials:

> Please provide your Keycloak admin credentials for `<instance>`:
> - **Username:** (Keycloak admin username)
> - **Password:** (Keycloak admin password)
>
> These must belong to a user with realm-management roles.

Also ask about the grant type:

> **Authentication method:**
> - `password` (default) — username + password for an admin user
> - `client_credentials` — client_id + client_secret for a service account

### Step 2 — Authenticate

Call `mcp__Keycloak__kc_auth_login(username="...", password="...", instance="<name>")`.

For `client_credentials` grant, pass `grant_type="client_credentials"`.

### Step 3 — Verify

Call `mcp__Keycloak__kc_connection_status(instance="<name>")` to confirm success.

Report result:
```
<instance>  ✅ Authenticated (token expires in <time>)
```

Or on failure:
```
<instance>  ❌ Login failed: <error message>
```

If authentication fails with "invalid credentials", suggest:
> Make sure you're using a Keycloak admin account (not a regular BPA user). The account needs realm-management roles.

## Usage

```
/keycloak-mcp:login jamaica
/keycloak-mcp:login nigeria
```
