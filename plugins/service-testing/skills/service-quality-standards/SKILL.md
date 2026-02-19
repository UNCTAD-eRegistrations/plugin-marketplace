---
name: service-quality-standards
description: >
  UNCTAD quality standards and scoring rubrics for eRegistrations BPA services.
  Use when evaluating service quality, scoring a service against UNCTAD benchmarks,
  checking publication readiness, assessing citizen experience quality, or comparing
  a service against best-practice templates from other deployments.
license: UNCTAD-Internal
compatibility: Requires an authenticated BPA MCP server.
allowed-tools: Read Write Bash
metadata:
  version: "1.0.0"
  version-date: "2026-02-19"
  author: "UNCTAD Trade Facilitation Section (tf-tools@unctad.org)"
---

# Service Quality Standards

UNCTAD benchmarks for evaluating eRegistrations service configurations.

## Quality Dimensions

### 1. Simplicity
A good service minimizes burden on the citizen.

| Metric | Excellent | Acceptable | Poor |
|--------|-----------|------------|------|
| Mandatory fields | ≤ 10 | 11–20 | > 20 |
| Document requirements (per registration) | ≤ 3 | 4–6 | > 6 |
| Registrations (procedure tracks) | 1–2 | 3–4 | ≥ 5 |
| Processing roles (agencies) | 1–2 | 3–4 | ≥ 5 |

### 2. Automation
A good service uses bots to reduce manual data entry.

| Metric | Excellent | Acceptable | Poor |
|--------|-----------|------------|------|
| Bot input coverage | ≥ 90% | 70–89% | < 70% |
| Bot output coverage | ≥ 90% | 70–89% | < 70% |
| External service integrations | ≥ 2 | 1 | 0 |

### 3. Configuration Integrity
A valid service has zero errors.

| Metric | Target |
|--------|--------|
| `debug_scan` CRITICAL issues | 0 |
| `debug_scan` ERROR issues | 0 |
| `debug_scan` WARNING issues | < 5 |
| Orphaned determinants | 0 |

### 4. Citizen Experience
A published service is accessible and documented.

| Requirement | Check |
|-------------|-------|
| Published on citizen portal | `service_get.published == true` |
| Has at least one print document | `print_document_list` not empty |
| Has citizen manual (HTML) | file exists in output/manuals/ |
| Has short name | `service_get.short_name` not null |

## Grade Scale

| Score | Grade | Meaning |
|-------|-------|---------|
| 90–100 | A | Excellent — showcase deployment |
| 80–89 | B | Good — minor improvements available |
| 70–79 | C | Acceptable — improvements recommended |
| 60–69 | D | Below standard — improvements required |
| < 60 | F | Failing — major issues to address |

## Pre-Go-Live Checklist

Before publishing a new service, verify:

- [ ] `debug_scan` returns zero CRITICAL/ERROR issues
- [ ] All roles have at least one institution assigned
- [ ] All registrations are linked and active
- [ ] All bots pass `bot_validate`
- [ ] Service is activated (`service_activate`)
- [ ] At least one print document created
- [ ] Service published (`service_publish`)
- [ ] Citizen manual generated (`/service-manual`)
- [ ] Quality score ≥ 70 (`/score-service`)

## Changelog

- 1.0.0 (2026-02-19) tf-tools — Initial quality standards
