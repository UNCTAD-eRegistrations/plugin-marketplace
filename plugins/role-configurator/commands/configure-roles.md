---
description: Design and configure the role and workflow structure for a BPA service
argument-hint: <service-id> [instance] [--wizard]
allowed-tools: [Read, Write, Bash]
---

# Role Configurator

Configure roles and workflow for BPA service `$ARGUMENTS`.

## Arguments

- First: service ID (required)
- Second: instance profile name (optional)
- `--wizard`: guided step-by-step creation (default if service has no roles yet)

## Current State Review

Start by reading what's already there:
1. `role_list` — show all roles with types and institution assignments
2. For each role, `role_get` — show status transitions embedded in role data
3. Visualize the workflow as ASCII:

```
[Applicant]
  Draft ──submit──→ Submitted
                       │
               [Ministry Reviewer]
               Under Review
               ├──request-info──→ Incomplete ──resubmit──→ Submitted
               └──forward──→ [Director Approver]
                              Under Approval
                              ├──approve──→ Approved ✅
                              └──reject──→  Rejected ❌
```

## Creation Mode (--wizard or empty service)

Ask the user:
1. How many agencies/roles are involved? (1 = simple, 2+ = multi-step)
2. For each agency: name, institution, allowed actions
3. For each action: target status, label, conditions

Then create using:
- `role_create` for each role
- `rolestatus_create` for each transition
- `roleinstitution_create` for each institution assignment
- `roleunit_create` for each sub-unit (if applicable)

## Edit Mode (existing service)

Show current workflow, then offer:
- Add a new role
- Add a status transition
- Change an institution assignment
- Add/remove a processing unit

## Usage

```
/configure-roles 42 jamaica
/configure-roles 17 lesotho2 --wizard
```
