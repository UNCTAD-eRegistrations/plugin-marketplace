---
description: Run the full test suite on a BPA service configuration
argument-hint: <service-id> [instance] [--quick | --full]
allowed-tools: [Read, Write, Bash]
---

# Service Test Runner

Run tests on BPA service `$ARGUMENTS`.

## Arguments

- First token: service ID (required)
- Second token: instance profile name (optional)
- `--quick`: run only critical checks (structural integrity, no orphans)
- `--full`: run all checks including quality scoring and scenario tracing (default)

## Test Suites

### Suite 1: Structural Integrity (always runs)
- All form components have labels and valid types
- All determinants reference existing fields/components
- All effects reference existing components
- No orphaned determinants (created but not linked to any effect)
- No orphaned effects (linked to non-existent components)

### Suite 2: Completeness (always runs)
- Service has at least one registration
- Every registration has at least one institution
- Service has an applicant role + at least one processing role
- Every processing role has at least one status transition
- Every role transition leads to a defined status
- Service has cost configured (0 is valid; absence is a flag)
- Service has at least one document requirement per registration (or explicitly marked "no docs required")

### Suite 3: Bot Coverage (--full)
- Every bot passes `bot_validate`
- Every bot has ≥ 70% input field coverage
- Every bot has ≥ 70% output field coverage
- No bot has been modified more than 30 days ago without re-validation

### Suite 4: Publication Readiness (--full)
- Service passes `debug_scan` with zero CRITICAL/ERROR issues
- Service is activated
- Service is published (visible on citizen portal)
- At least one print document exists (or explicitly flagged as "no print doc")
- Service has a short_name set

## Output Format

```
Service: <name> (ID: <id>)
Instance: <server>

SUITE 1: Structural Integrity    [PASS | FAIL]
SUITE 2: Completeness            [PASS | FAIL | WARN]
SUITE 3: Bot Coverage            [PASS | FAIL | SKIP]
SUITE 4: Publication Readiness   [PASS | FAIL | SKIP]

Failures: N
Warnings: N

[Detailed findings per failed/warned check]
```

## Usage

```
/test-service 42 jamaica
/test-service 17 --quick
/test-service 42 lesotho2 --full
```
