---
description: Interactive wizard for configuring institutions and assigning them to services
argument-hint: [mcp-server] [--service <id>]
allowed-tools: [Read, Write, Bash]
---

# Institution Setup Wizard

Configure institutions for `$ARGUMENTS`.

## Arguments

- First token: MCP server name (optional)
- `--service <id>`: scope setup to one service's registrations

## What this does

Government services require institutions (agencies, ministries, departments) assigned to:
1. **Registrations** — which institution processes each track
2. **Roles** — which institution owns each processing role
3. **Role Units** — sub-units within an institution (desks, divisions)

## Flow

### Step 1: Discover existing institutions
Run `institution_discover` to find already-configured institutions.
Show as a table: ID, Name, Type.

### Step 2: Create missing institutions
For each institution not yet present:
- Ask for: name, type, description
- Create with `institution_create`

### Step 3: Assign to registrations
If `--service` flag:
- List registrations for that service
- For each registration, show current institution assignments
- Prompt to add/remove assignments via `registrationinstitution_create` / `registrationinstitution_delete`

### Step 4: Assign to roles
- List roles for the service
- For each processing role, show current institution
- Prompt to set institution via `roleinstitution_create`

### Step 5: Configure units (optional)
Ask if units (sub-departments) should be configured per role.
If yes, create via `roleunit_create`.

## Usage

```
/setup-institutions BPA-lesotho2
/setup-institutions BPA-jamaica --service 42
```
