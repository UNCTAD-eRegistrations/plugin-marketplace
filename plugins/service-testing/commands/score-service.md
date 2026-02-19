---
description: Score a BPA service against UNCTAD trade facilitation quality standards
argument-hint: <service-id> [mcp-server]
allowed-tools: [Read, Write, Bash]
---

# Service Quality Scorer

Score BPA service `$ARGUMENTS` against UNCTAD quality standards.

## Instructions

Parse arguments: service ID (required), MCP server (optional).

Delegate to the `service-tester` agent or follow the `service-quality-standards` skill.

## Scoring Dimensions

### 1. Simplicity (0–25 pts)
- Mandatory fields: 25 pts if ≤ 10, scaled down to 0 pts at > 30
- Document requirements: 25 pts if ≤ 3 per registration, 0 pts if > 8
- Procedure tracks (registrations): 25 pts if ≤ 2, 0 pts if > 5
- Workflow steps: 25 pts if ≤ 3 roles, 0 pts if > 7

### 2. Automation (0–25 pts)
- Bot coverage (avg across all bots): score linearly 0–25 pts from 0% to 100%
- External service integrations (mule services): +5 pts per integration (max 25)

### 3. Completeness (0–25 pts)
- Debug scan: 25 pts if zero issues, -5 per CRITICAL, -2 per ERROR, -1 per WARNING
- All required metadata present (name, description, short_name): 5 pts each

### 4. Citizen Experience (0–25 pts)
- Service is published: 10 pts
- Has print document: 10 pts
- Has citizen manual (check if manual file exists in output/manuals/): 5 pts

## Output

```
Service Quality Score: XX / 100   [Grade: A/B/C/D/F]

Simplicity:          XX / 25
Automation:          XX / 25
Completeness:        XX / 25
Citizen Experience:  XX / 25

[Specific findings and improvement suggestions]
```

## Usage

```
/score-service 42 BPA-jamaica
/score-service 17
```
