---
name: handoff
description: >
  Session handoff for AI continuity. Auto-detects git state, plan files, and
  environment context, then generates or consumes a HANDOFF.md file so any
  AI agent can continue the work. Supports three modes: create (full),
  quick (minimal), and resume (continue from existing handoff).
license: MIT
compatibility: Any git repository
allowed-tools: Read, Write, Edit, Bash(git *), Bash(date *), Bash(ls *), Bash(cat *), Glob, Grep
metadata:
  version: "1.0.0"
  version-date: "2026-03-31"
  author: "Software Factory"
  argument-hint: "<create|quick|resume> [title or goal]"
---

# Session Handoff

Capture session state so any AI agent can continue your work.

## Modes

This skill operates in three modes, selected by the invoking command:

- **create** — Full handoff with auto-detection + conversational prompts
- **quick** — Minimal handoff with auto-detection + user-provided goal
- **resume** — Read existing handoff and continue the work

## Mode: Create

### Step 1: Check for existing HANDOFF.md

```bash
ls HANDOFF.md 2>/dev/null
```

If it exists, ask the user: **"HANDOFF.md already exists. Overwrite?"**
- If yes, proceed.
- If no, abort with: "Use `/handoff:resume` to continue from the existing handoff, or remove it manually."

### Step 2: Auto-detect state

Gather the following in parallel:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline -10
```

Also check for plan/spec files:

```bash
ls docs/superpowers/specs/*.md 2>/dev/null
ls docs/superpowers/plans/*.md 2>/dev/null
```

If spec or plan files exist, read them to extract:
- The goal/purpose from the spec
- Progress (completed/remaining tasks) from the plan

Check for environment context:

```bash
ls CLAUDE.md README.md .env.example 2>/dev/null
```

If `CLAUDE.md` or `README.md` exist, scan them for setup instructions (env vars, dependencies, build commands).

### Step 3: Conversational prompts

Present the auto-detected state to the user as a summary, then ask each question one at a time. Skip questions where auto-detection already provided the answer.

1. **Goal** — "What's the goal of this work?" (skip if extracted from spec/plan)
2. **Status** — "What's the current status? (In Progress / Blocked / Ready for Review)"
3. **Failed approaches** — "Any approaches that failed and should not be repeated? Include error messages if you have them."
4. **Key decisions** — "Any key decisions you made and why?"
5. **Code context** — "Any code signatures, API shapes, or config the next agent needs to know? Paste code blocks."
6. **Setup** — "Any setup required beyond what's in the README?" (skip if auto-detected)
7. **Warnings** — "Any gotchas or things that will waste time if the next agent doesn't know?"

### Step 4: Generate HANDOFF.md

Compose the handoff document at the repo root. Use this exact structure — **omit sections that have no content**:

```markdown
# Handoff: [Title]

> Commit this file to persist it across sessions, or leave it untracked for ephemeral use.

**Generated**: [YYYY-MM-DD HH:MM from `date "+%Y-%m-%d %H:%M"`]
**Branch**: [from git branch]
**Commit**: [short hash from git rev-parse --short HEAD]
**Status**: [from user response]

## Goal
[From spec/plan or user response — one paragraph]

## Completed
- [x] [Items from plan progress or user input]

## Not Yet Done
- [ ] [Items from plan progress or user input]

## Failed Approaches (Don't Repeat These)
[From user response — narrative with error messages and file:line refs]

## Key Decisions
| Decision | Rationale |
|----------|-----------|
| [From user response] | [From user response] |

## Current State
**Working**: [What functions correctly]
**Broken**: [What's failing, with errors and locations]

## Code Context
[From user response — code blocks only]

## Resume Instructions
[Numbered steps with expected outcomes and verification]

## Setup Required
[From README/CLAUDE.md auto-detection + user additions]

## Warnings
[From user response]
```

Write the file to `HANDOFF.md` at the repo root.

### Step 5: Confirm

Tell the user: "Handoff saved to `HANDOFF.md`. The next agent can pick up with `/handoff:resume` or by reading the file directly."

---

## Mode: Quick

### Step 1: Check for existing HANDOFF.md

Same as create mode — check and prompt for overwrite.

### Step 2: Parse arguments

The user's arguments are the goal description. If no arguments provided, ask: "What's the one-liner goal?"

### Step 3: Auto-detect state

Same git commands as create mode. Also check for plan files to extract completed/remaining items.

### Step 4: Generate lean HANDOFF.md

Write `HANDOFF.md` with only these sections:

```markdown
# Handoff: [Goal summary or branch name]

> Commit this file to persist it across sessions, or leave it untracked for ephemeral use.

**Generated**: [YYYY-MM-DD HH:MM]
**Branch**: [branch name]
**Commit**: [short hash]
**Status**: In Progress

## Goal
[From user arguments]

## Completed
- [x] [From plan progress or recent commits]

## Not Yet Done
- [ ] [From plan progress or uncommitted work]

## Resume Instructions
1. [Inferred from git state and plan progress]
```

No conversational prompts. No failed approaches, decisions, code context, or warnings sections.

### Step 5: Confirm

Tell the user: "Quick handoff saved to `HANDOFF.md`."

---

## Mode: Resume

### Step 1: Read HANDOFF.md

```bash
cat HANDOFF.md
```

If the file does not exist, stop with: "No HANDOFF.md found in this directory. Create one with `/handoff:create` or `/handoff:quick`."

### Step 2: Detect drift

Compare the handoff metadata against current state:

```bash
git branch --show-current
git rev-parse --short HEAD
```

Check for drift:
- **Branch changed** — handoff says `feature/auth` but current branch is `main`
- **New commits** — handoff commit hash doesn't match current HEAD

If drift detected, warn the user:
> "Drift detected since this handoff was created:
> - Branch: [handoff branch] → [current branch]
> - Commits: [N] new commits since handoff
>
> The handoff may be outdated. Proceed anyway?"

Wait for confirmation.

### Step 3: Present summary

Summarize the handoff for the user:
- **Goal**: [from handoff]
- **Completed**: [count] items done
- **Remaining**: [count] items to do
- **Warnings**: [if any]
- **Resume instructions**: [list steps]

Ask: **"Ready to continue?"**

### Step 4: Execute resume instructions

Follow the resume instructions one step at a time. After each step:
- Report what was done and the outcome
- Ask if the user wants to continue to the next step

Do NOT auto-execute all steps. The user controls the pace.
