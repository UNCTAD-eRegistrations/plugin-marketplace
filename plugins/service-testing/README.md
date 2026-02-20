# service-testing

Validate BPA service configuration, score against UNCTAD quality standards, and snapshot for regression testing.

## Commands

| Command | Description |
|---------|-------------|
| `/test-service <id> [--quick\|--full]` | Run structural + completeness + bot + publication test suites |
| `/score-service <id>` | Score service 0–100 across Simplicity, Automation, Completeness, Citizen Experience |
| `/snapshot-service <id> [--compare\|--diff]` | Save/compare service snapshots for regression testing |

## Agents

| Agent | Description |
|-------|-------------|
| `service-tester` | Comprehensive QA agent — cross-references form, determinants, roles, bots, registrations |

## Skills

| Skill | Description |
|-------|-------------|
| `service-quality-standards` | UNCTAD benchmarks, scoring rubrics, pre-go-live checklist |

## Test Suites (in `/test-service`)

1. **Structural Integrity** — orphan detection, reference validity
2. **Completeness** — roles, institutions, costs, document requirements
3. **Bot Coverage** — mapping completeness, validation
4. **Publication Readiness** — activated, published, print doc, citizen manual

## Typical Workflow

```bash
# Before making changes — save a snapshot
/snapshot-service 42 jamaica

# Make your changes...

# After changes — verify only intended changes happened
/snapshot-service 42 jamaica --compare

# Full test suite
/test-service 42 jamaica --full

# Quality score
/score-service 42 jamaica
```

## Requirements

- `bpa-mcp` plugin installed and configured
