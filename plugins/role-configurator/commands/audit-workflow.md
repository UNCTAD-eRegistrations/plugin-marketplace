---
description: Audit the role and workflow completeness of all services on a BPA instance
argument-hint: [instance]
allowed-tools: [Read, Write, Bash]
---

# Workflow Audit

Audit workflow completeness for `$ARGUMENTS`.

## Instructions

For each service, check:
- Has at least one applicant role (UserRole)
- Has at least one processing role
- Every processing role has at least 2 status transitions (in + terminal)
- No dead-end statuses (non-terminal with no outgoing transitions)
- Every processing role has an institution assigned
- Submitted status exists (or equivalent starting status for processing)

Report:

```
Business Registration (42)  ✅ Workflow complete (3 roles, 7 transitions)
Import Permit (17)          ⚠️  Role "Director" has no institution
Mining License (8)          ❌ Dead-end status "Under Review" — no transitions out
```

## Usage

```
/audit-workflow jamaica
```
