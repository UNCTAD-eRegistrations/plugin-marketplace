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
