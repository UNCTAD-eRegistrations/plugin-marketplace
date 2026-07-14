---
name: team-bus
metadata:
  version: 1.0.0
description: Set up Jira-centered collaboration between team members and their Claude sessions — a 15-minute watcher that surfaces new ticket comments and PR status changes in your session, plus the shared conventions (findings as ticket comments, one epic as shared memory). TRIGGER when the user says "team bus", "set up the bus", "watch these tickets", "follow the epic", or wants their Claude session to react to Jira/PR activity without manual polling.
---

# team-bus — one watcher per person, Jira as the shared memory

Humans and Claude sessions collaborate through Jira, not through chat relays. Each person runs a small watcher; every session reads and writes ticket comments. This skill sets it up and teaches the conventions.

## The conventions (read to the user during setup)

1. **The epic is the shared memory.** One umbrella ticket carries the goal + definition of done; work items are its children. Anything a teammate (or their Claude) must know goes in a ticket comment — chat is for humans only.
2. **Findings and solutions land as comments on the ticket they belong to** — not in chat, not in DMs. Your Claude posts there too (with your Jira account).
3. **The watcher ignores your own comments** (or it loops on itself).
4. **A message seen is not a message read**: the watcher surfaces events in YOUR live session; if your session is closed, events wait in state and surface at the next cycle. Nothing is lost, nothing depends on someone relaying.

## Setup wizard (run these steps)

### 1. Credentials — the user does this part themselves
Ask the user to create a Jira API token at https://id.atlassian.com/manage-profile/security/api-tokens (they must create it and paste it — never create it for them). Then write `~/.claude/team-bus/jira.env` (chmod 600):

```
JIRA_BASE=https://<org>.atlassian.net
JIRA_EMAIL=<their-atlassian-email>
JIRA_TOKEN=<their-token>
```

Verify with: `curl -s -u "$JIRA_EMAIL:$JIRA_TOKEN" "$JIRA_BASE/rest/api/2/myself"` → must return their account.

### 2. What to watch
Ask which tickets (usually: one epic + its children — offer to resolve children automatically via `/rest/api/2/search/jql?jql=parent%3D<EPIC>`), and optionally which GitHub PRs (needs `gh` CLI authenticated). Write `~/.claude/team-bus/routing.json`:

```json
{
  "ignore_authors": ["<their-atlassian-email>"],
  "jira_tickets": ["TOBE-17982", "TOBE-17983"],
  "github_prs": [{"repo": "UNCTAD-eRegistrations/DS-Frontend", "number": 145, "check": "build-and-push-docker"}]
}
```

### 3. Install the watcher
Copy `bus-watch.py` (bundled next to this SKILL.md) to `~/.claude/team-bus/bus-watch.py`. Run it once — first run prints `NO_NEW_EVENTS` and records the baseline in `state.json`.

### 4. Arm the cron (per session)
Create a session cron (CronCreate), every 15 minutes on off-minutes (e.g. `4,19,34,49 * * * *`), with this prompt:

> Team-bus cycle. Be silent and brief. Run `python3 ~/.claude/team-bus/bus-watch.py`. If it prints NO_NEW_EVENTS: output "Bus: nothing new" and stop. Otherwise, for each JSON event line report: who commented on which ticket, the substance in 1-2 plain lines, and ONE concrete proposed next action. Significant = a failure point, a merge, anything addressed to us.

Tell the user: **the cron lives in the session** — re-arm it when starting a new session (this skill's step 4 alone re-arms; steps 1-3 persist on disk).

### 5. Close the loop
Remind the user: when they (or their Claude) finish something, the result goes as a comment on the ticket — that is what everyone else's watcher picks up.

## /team-bus status

Run `python3 ~/.claude/team-bus/bus-watch.py` once and show: watched tickets, watched PRs, last state timestamps, and whether a cron is armed in this session (CronList).

## Notes

- Requires: Python 3, curl; `gh` CLI only if PRs are watched.
- The token is personal — comments posted by a session appear under that person's Jira account.
- Multiple workstreams: add tickets to `jira_tickets`; one watcher covers them all.
