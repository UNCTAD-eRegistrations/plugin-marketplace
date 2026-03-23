# Rauno Handover

Knowledge handover plugin — a collection of skills capturing Rauno's institutional knowledge, workflows, and expertise for the team.

## Adding Skills

To add a new handover skill:

1. Create a directory under `skills/` with a descriptive name
2. Add a `SKILL.md` with proper frontmatter:

```yaml
---
name: skill-name
description: >
  What this skill teaches and when to use it.
metadata:
  version: "1.0.0"
  version-date: "YYYY-MM-DD"
  author: "Rauno"
---
```

3. Include any supporting files in `references/`, `scripts/`, or `assets/` subdirectories as needed

## Structure

```
rauno-handover/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── (add skills here)
└── README.md
```
