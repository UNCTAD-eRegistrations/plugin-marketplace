# Handoff Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a `handoff` plugin with three commands (`create`, `quick`, `resume`) backed by one skill that auto-detects session state and generates agent-agnostic `HANDOFF.md` files.

**Architecture:** Three thin command files delegate to a single `handoff` skill. The skill handles git auto-detection, conversational prompting (for `create`), and document generation/consumption. No external dependencies — pure markdown files using Bash for git commands.

**Tech Stack:** Markdown (command/skill definitions), Bash (git commands), no runtime dependencies.

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `plugins/handoff/.claude-plugin/plugin.json` | Plugin manifest |
| Create | `plugins/handoff/commands/create.md` | `/handoff:create` command |
| Create | `plugins/handoff/commands/quick.md` | `/handoff:quick` command |
| Create | `plugins/handoff/commands/resume.md` | `/handoff:resume` command |
| Create | `plugins/handoff/skills/handoff/SKILL.md` | Core skill: auto-detection + generation |
| Create | `plugins/handoff/README.md` | Plugin documentation |

---

### Task 1: Plugin manifest

**Files:**
- Create: `plugins/handoff/.claude-plugin/plugin.json`

- [ ] **Step 1: Create plugin directory structure**

```bash
mkdir -p plugins/handoff/.claude-plugin
mkdir -p plugins/handoff/commands
mkdir -p plugins/handoff/skills/handoff
```

- [ ] **Step 2: Write plugin.json**

Create `plugins/handoff/.claude-plugin/plugin.json`:

```json
{
  "name": "handoff",
  "description": "Session handoff — capture state so any AI agent can continue your work",
  "version": "1.0.0",
  "category": "productivity",
  "author": {
    "name": "Software Factory"
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add plugins/handoff/.claude-plugin/plugin.json
git commit -m "chore: scaffold handoff plugin with manifest"
```

---

### Task 2: Handoff skill (core logic)

**Files:**
- Create: `plugins/handoff/skills/handoff/SKILL.md`

This is the core of the plugin. All three commands delegate here. The skill defines three modes: `create`, `quick`, and `resume`.

- [ ] **Step 1: Write SKILL.md**

Create `plugins/handoff/skills/handoff/SKILL.md`:

````markdown
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
````

- [ ] **Step 2: Verify the skill file is valid**

Read the file back and check:
- Frontmatter YAML is well-formed (no unclosed quotes, correct indentation)
- All three modes (create, quick, resume) are fully defined
- No placeholder text (TBD, TODO)

- [ ] **Step 3: Commit**

```bash
git add plugins/handoff/skills/handoff/SKILL.md
git commit -m "feat: add handoff skill with create/quick/resume modes"
```

---

### Task 3: Create command (`/handoff:create`)

**Files:**
- Create: `plugins/handoff/commands/create.md`

- [ ] **Step 1: Write create.md**

Create `plugins/handoff/commands/create.md`:

```markdown
---
description: Full session handoff with auto-detection and conversational context gathering
argument-hint: "[title]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Create Session Handoff

Create a full session handoff document. `$ARGUMENTS`

## Instructions

Parse arguments: the optional first argument is the handoff title. If omitted, infer from the current branch name or active plan.

Follow the `handoff` skill in this plugin (`skills/handoff/SKILL.md`), using **Mode: Create**.

## Usage

` ``
/handoff:create
/handoff:create OAuth2 integration
` ``
```

- [ ] **Step 2: Commit**

```bash
git add plugins/handoff/commands/create.md
git commit -m "feat: add /handoff:create command"
```

---

### Task 4: Quick command (`/handoff:quick`)

**Files:**
- Create: `plugins/handoff/commands/quick.md`

- [ ] **Step 1: Write quick.md**

Create `plugins/handoff/commands/quick.md`:

```markdown
---
description: Minimal session handoff — auto-detected state plus a one-liner goal
argument-hint: <goal description>
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Quick Session Handoff

Create a minimal handoff document. `$ARGUMENTS`

## Instructions

Parse arguments: all arguments form the goal description. If no arguments provided, ask for a one-liner goal.

Follow the `handoff` skill in this plugin (`skills/handoff/SKILL.md`), using **Mode: Quick**.

## Usage

` ``
/handoff:quick Fix token refresh endpoint
/handoff:quick Adding field validation to registration form
` ``
```

- [ ] **Step 2: Commit**

```bash
git add plugins/handoff/commands/quick.md
git commit -m "feat: add /handoff:quick command"
```

---

### Task 5: Resume command (`/handoff:resume`)

**Files:**
- Create: `plugins/handoff/commands/resume.md`

- [ ] **Step 1: Write resume.md**

Create `plugins/handoff/commands/resume.md`:

```markdown
---
description: Continue work from an existing HANDOFF.md — detects drift and guides re-entry
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Resume from Handoff

Read an existing HANDOFF.md and continue the work.

## Instructions

No arguments needed. Follow the `handoff` skill in this plugin (`skills/handoff/SKILL.md`), using **Mode: Resume**.

## Usage

` ``
/handoff:resume
` ``
```

- [ ] **Step 2: Commit**

```bash
git add plugins/handoff/commands/resume.md
git commit -m "feat: add /handoff:resume command"
```

---

### Task 6: README

**Files:**
- Create: `plugins/handoff/README.md`

- [ ] **Step 1: Write README.md**

Create `plugins/handoff/README.md`:

```markdown
# Handoff Plugin

Session handoff for AI continuity. Captures your work state so any AI agent can pick up where you left off.

## Commands

| Command | Description |
|---------|-------------|
| `/handoff:create` | Full handoff with auto-detection and conversational prompts |
| `/handoff:quick` | Minimal handoff — auto-detected state + one-liner goal |
| `/handoff:resume` | Continue from an existing HANDOFF.md |

## How It Works

**Creating a handoff:** When your session is ending (context limit, switching tools, taking a break), run `/handoff:create`. The plugin auto-detects git state, active plans, and environment context, then asks you to fill in what it can't detect (failed approaches, key decisions, code context). It writes everything to `HANDOFF.md` at the repo root.

**Quick handoff:** For simple tasks, `/handoff:quick Fix the auth bug` skips the conversational prompts and generates a lean handoff from auto-detected state plus your one-liner.

**Resuming:** In a new session, run `/handoff:resume`. It reads `HANDOFF.md`, checks for drift (branch changes, new commits), summarizes the state, and guides you through the resume instructions step by step.

## Agent-Agnostic

The output is plain markdown. Any AI agent can be told "Read HANDOFF.md and continue the work" — no Claude Code dependency required.

## What Gets Auto-Detected

- Current branch, uncommitted changes, recent commits
- Active design specs and implementation plans (progress tracking)
- Environment setup from CLAUDE.md / README.md
```

- [ ] **Step 2: Commit**

```bash
git add plugins/handoff/README.md
git commit -m "docs: add handoff plugin README"
```

---

### Task 7: Integration verification

- [ ] **Step 1: Verify plugin structure**

```bash
find plugins/handoff -type f | sort
```

Expected output:
```
plugins/handoff/.claude-plugin/plugin.json
plugins/handoff/README.md
plugins/handoff/commands/create.md
plugins/handoff/commands/quick.md
plugins/handoff/commands/resume.md
plugins/handoff/skills/handoff/SKILL.md
```

- [ ] **Step 2: Verify plugin.json is valid JSON**

```bash
python3 -c "import json; json.load(open('plugins/handoff/.claude-plugin/plugin.json')); print('Valid JSON')"
```

Expected: `Valid JSON`

- [ ] **Step 3: Verify all command files have valid frontmatter**

Check each command file starts with `---` and has required fields (`description`, `allowed-tools`):

```bash
for f in plugins/handoff/commands/*.md; do
  echo "=== $f ==="
  head -6 "$f"
  echo
done
```

Expected: Each file shows frontmatter with `description` and `allowed-tools` fields.

- [ ] **Step 4: Verify SKILL.md frontmatter**

```bash
head -15 plugins/handoff/skills/handoff/SKILL.md
```

Expected: Valid YAML frontmatter with `name`, `description`, `allowed-tools`, and `metadata` fields.

- [ ] **Step 5: Final commit (if any fixes needed)**

Only if verification steps revealed issues. Otherwise skip.
