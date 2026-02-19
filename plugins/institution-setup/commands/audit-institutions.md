---
description: Audit institution assignments across all services on a BPA instance
argument-hint: [mcp-server]
allowed-tools: [Read, Write, Bash]
---

# Institution Audit

Audit institution coverage for `$ARGUMENTS`.

## Instructions

1. List all services with `service_list`
2. For each service, list registrations and check institution assignments
3. For each service, list roles and check role-institution assignments
4. Report:

```
Service: Business Registration (ID: 42)
  Registration "New Registration"     ← ✅ Ministry of Trade assigned
  Registration "Renewal"              ← ❌ No institution assigned
  Role "Reviewer"                     ← ✅ Ministry of Trade
  Role "Approver"                     ← ❌ No institution assigned

SUMMARY: 3 of 8 registrations missing institution | 2 of 6 roles missing institution
```

Unassigned items prevent citizens from submitting applications — treat as CRITICAL.

## Usage

```
/audit-institutions BPA-jamaica
```
