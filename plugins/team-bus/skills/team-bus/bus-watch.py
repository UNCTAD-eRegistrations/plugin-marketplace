#!/usr/bin/env python3
"""team-bus watcher — fetch + diff, no LLM.

Home dir: ~/.claude/team-bus/ (override with TEAM_BUS_HOME)
  jira.env      JIRA_BASE=https://<org>.atlassian.net  JIRA_EMAIL=...  JIRA_TOKEN=...
  routing.json  {"ignore_authors":[...],"jira_tickets":[...],"github_prs":[{"repo":...,"number":...,"check":...}]}
  state.json    created/updated automatically

Prints one JSON line per NEW event; "NO_NEW_EVENTS" when quiet.
First run only records a baseline (no event flood).
"""
import json, os, subprocess, sys

HOME = os.environ.get("TEAM_BUS_HOME", os.path.expanduser("~/.claude/team-bus"))
ENV = os.path.join(HOME, "jira.env")
ROUTING = os.path.join(HOME, "routing.json")
STATE = os.path.join(HOME, "state.json")


def load_env():
    env = {}
    if os.path.exists(ENV):
        for line in open(ENV):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k] = v
    return env


def curl(url, email, token):
    out = subprocess.run(["curl", "-s", "-u", f"{email}:{token}", url],
                         capture_output=True, text=True, timeout=30).stdout
    return json.loads(out) if out else {}


def main():
    env = load_env()
    base, email, token = env.get("JIRA_BASE"), env.get("JIRA_EMAIL"), env.get("JIRA_TOKEN")
    if not (base and email and token):
        print(json.dumps({"source": "bus", "kind": "error",
                          "summary": f"missing JIRA_BASE/JIRA_EMAIL/JIRA_TOKEN in {ENV}"}))
        return 1

    routing = json.load(open(ROUTING))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    own = routing.get("ignore_authors", [])
    events = []

    for ticket in routing.get("jira_tickets", []):
        d = curl(f"{base}/rest/api/2/issue/{ticket}/comment?orderBy=-created&maxResults=10",
                 email, token)
        comments = d.get("comments", [])
        last = state.get(f"jira:{ticket}")
        newest = comments[0]["id"] if comments else last
        for c in comments:
            if last is None:
                break  # baseline run for this ticket
            if int(c["id"]) <= int(last):
                break
            if c.get("author", {}).get("emailAddress", "") in own:
                continue
            events.append({
                "source": "jira", "key": ticket, "kind": "comment",
                "author": c.get("author", {}).get("displayName", "?"),
                "summary": c.get("body", "").replace("\n", " ")[:300],
                "url": f"{base}/browse/{ticket}",
            })
        state[f"jira:{ticket}"] = newest

    for pr in routing.get("github_prs", []):
        out = subprocess.run(
            ["gh", "pr", "view", str(pr["number"]), "--repo", pr["repo"],
             "--json", "state,statusCheckRollup"],
            capture_output=True, text=True, timeout=30).stdout
        if out:
            d = json.loads(out)
            build = next((c.get("conclusion") or c.get("status")
                          for c in d.get("statusCheckRollup", [])
                          if c.get("name") == pr.get("check", "")), None)
            sig = f"{d.get('state')}|{build}"
            skey = f"gh:{pr['repo']}#{pr['number']}"
            if state.get(skey) is not None and state[skey] != sig:
                events.append({
                    "source": "github", "key": f"{pr['repo']}#{pr['number']}",
                    "kind": "status", "author": "-",
                    "summary": f"PR state {d.get('state')}, build {build}",
                    "url": f"https://github.com/{pr['repo']}/pull/{pr['number']}",
                })
            state[skey] = sig

    os.makedirs(HOME, exist_ok=True)
    json.dump(state, open(STATE, "w"), indent=1)
    for e in events:
        print(json.dumps(e, ensure_ascii=False))
    if not events:
        print("NO_NEW_EVENTS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
