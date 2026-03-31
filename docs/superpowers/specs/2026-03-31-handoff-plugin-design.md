# Handoff Plugin — Design Spec

**Date:** 2026-03-31
**Status:** Approved
**Plugin name:** `handoff`
**Version:** 1.0.0

## Purpose

A Claude Code plugin for session continuity. When an AI session ends — context limit, tool switch, break — the handoff captures enough state for any AI agent to continue seamlessly. Inspired by [willseltzer/claude-handoff](https://github.com/willseltzer/claude-handoff).

This is **separate** from the `rauno-handover` plugin, which captures institutional knowledge. This plugin captures session state.

## Plugin Structure

```
plugins/handoff/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── create.md         # /handoff:create — full handoff
│   ├── quick.md          # /handoff:quick — minimal handoff
│   └── resume.md         # /handoff:resume — continue from handoff
├── skills/
│   └── handoff/
│       └── SKILL.md      # Core logic: auto-detection + generation
└── README.md
```

## Commands

### `/handoff:create`

Full handoff with conversational context gathering.

**Flow:**
1. Skill auto-detects git state, plan files, environment context
2. Prompts user for what can't be auto-detected:
   - Goal (if no plan file found)
   - Failed approaches the next agent should avoid
   - Key decisions and rationale
   - Code signatures or API shapes the next agent should know
   - Warnings or gotchas
3. Generates `HANDOFF.md` at repo root

**Arguments:** Optional `[title]` — used as the handoff title. If omitted, inferred from branch name or plan.

### `/handoff:quick`

Minimal handoff — auto-detected state + user-provided one-liner.

**Flow:**
1. Skill auto-detects git state (same as create)
2. No conversational prompts — skips failed approaches, decisions, code context, warnings
3. Generates a lean `HANDOFF.md` with: Goal, Completed, Not Yet Done, Resume Instructions

**Arguments:** `[goal description]` — one-liner describing the task. Required.

### `/handoff:resume`

Continue from an existing handoff.

**Flow:**
1. Read `HANDOFF.md` from repo root
2. If not found, error with clear message
3. Check for drift: compare branch name and last commit hash from handoff against current state
4. If drift detected, warn user with specifics (e.g., "3 new commits since handoff, branch changed from X to Y")
5. Present summary to user: goal, what's done, what's remaining, warnings
6. Ask "Ready to continue?" — wait for confirmation
7. Follow resume instructions step by step, confirming with user at each step

**Arguments:** None.

**Resume contract:** The agent does NOT auto-execute. It reads, summarizes, confirms, then proceeds one step at a time with user oversight.

## Auto-Detection

When creating a handoff, the skill gathers:

| Source | What it collects |
|--------|-----------------|
| `git branch --show-current` | Current branch name |
| `git status` | Uncommitted changes (staged, unstaged, untracked) |
| `git log --oneline -10` | Recent commit history |
| `git rev-parse HEAD` | Current commit hash (for drift detection on resume) |
| `docs/superpowers/specs/*.md` | Active design specs — extracts goal and scope |
| `docs/superpowers/plans/*.md` | Active implementation plans — extracts progress |
| `CLAUDE.md`, `README.md` | Environment setup notes, if present |

**Empty-state behavior:** If auto-detection finds nothing interesting (clean repo, no plans, no recent commits), the skill says so and leans on conversational prompts for `create`. For `quick`, it produces a minimal template with just what the user provides.

**What is NOT auto-detected:**
- Code Context section (user-supplied during conversational phase of `create`)
- Failed approaches (user-supplied)
- Test results (no automatic test running — too slow/intrusive)

## Handoff Document Format

Output: `HANDOFF.md` at repo root.

```markdown
# Handoff: [Task Title]

**Generated**: YYYY-MM-DD HH:MM
**Branch**: feature/xxx
**Commit**: abc1234
**Status**: In Progress | Blocked | Ready for Review

## Goal
One paragraph: what we're trying to accomplish.

## Completed
- [x] Step that's done
- [x] Another done step

## Not Yet Done
- [ ] Remaining work
- [ ] More remaining work

## Failed Approaches (Don't Repeat These)
Narrative format. What was tried, why it failed, what error/behavior
was observed. Include actual error messages and file:line references.

## Key Decisions
| Decision | Rationale |
|----------|-----------|
| Chose X over Y | Because Z |

## Current State
**Working**: What functions correctly right now
**Broken**: What's failing, with error messages and locations

## Code Context
Key signatures, API shapes, or config that the next agent needs.
Shown as code blocks, not descriptions.

## Resume Instructions
Numbered steps. Specific. Each step has:
1. What to do
   - Expected outcome
   - How to verify

## Setup Required
Env vars, dependencies, services that need to be running.

## Warnings
Things that will waste time if you don't know them upfront.
```

**Section omission:** Sections with no content are omitted entirely. `/handoff:quick` typically produces only: Goal, Completed, Not Yet Done, Resume Instructions.

## File Policies

**Collision:** If `HANDOFF.md` already exists when creating, prompt the user: "HANDOFF.md already exists. Overwrite?" If declined, abort — the user should resume or manually remove the old handoff first.

**Git:** Don't commit or gitignore by default. The handoff document itself notes: "Commit this file to persist it across sessions, or leave it untracked for ephemeral use."

**Agent-agnostic:** The format is plain markdown. Any AI agent can be told "Read HANDOFF.md and continue the work."

## plugin.json

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

## Scope Boundaries

**In scope:**
- Three commands (create, quick, resume)
- One skill (handoff auto-detection + generation)
- HANDOFF.md generation and consumption

**Out of scope:**
- Multiple concurrent handoffs (branch-scoped files)
- Integration with auto-memory system
- Automatic test running during handoff creation
- Handoff history/versioning
