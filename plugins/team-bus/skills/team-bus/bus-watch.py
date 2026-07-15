#!/usr/bin/env python3
"""team-bus watcher v2 — fetch + diff, no LLM.

Watches, per Jira ticket in routing.json:
  - new comments and EDITED comments
  - changelog: status transitions, assignee, description, attachments, parent
  - plus GitHub PR state/build changes
State: per-ticket watermark (last processed Jira timestamp string).
First sight of a ticket = baseline only (no event flood).
Prints one JSON line per NEW event; "NO_NEW_EVENTS" when quiet.
"""
import json, os, subprocess, sys

HOME = os.environ.get("TEAM_BUS_HOME", os.path.expanduser("~/.claude/team-bus"))
KEYS = os.path.join(HOME, "jira.env")
ROUTING = os.path.join(HOME, "routing.json")
STATE = os.path.join(HOME, "state.json")


def load_keys():
    env = {}
    for line in open(KEYS):
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
    keys = load_keys()
    base = keys.get("JIRA_BASE", "").rstrip("/")
    email, token = keys.get("JIRA_EMAIL"), keys.get("JIRA_TOKEN")
    if not (base and email and token):
        print(json.dumps({"source": "bus", "kind": "error",
                          "summary": f"missing JIRA_BASE/JIRA_EMAIL/JIRA_TOKEN in {KEYS}"}))
        return 1

    routing = json.load(open(ROUTING))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    own = routing.get("ignore_authors", [])
    events = []

    for ticket in routing.get("jira_tickets", []):
        skey = f"jira:{ticket}"
        prev = state.get(skey)
        # migrate v1 state (comment-id string) -> v2 watermark dict
        if not isinstance(prev, dict):
            prev = None
        watermark = prev.get("watermark") if prev else None
        newmark = watermark or ""

        d = curl(f"{base}/rest/api/2/issue/{ticket}?fields=summary,status,assignee,updated",
                 email, token)
        if not d.get("fields"):
            continue
        url = f"{base}/browse/{ticket}"

        # changelog: fetch the LAST page explicitly (expand=changelog returns only
        # the oldest 50 histories — busy tickets silently lose the newest ones)
        cl = curl(f"{base}/rest/api/2/issue/{ticket}/changelog?maxResults=1", email, token)
        total = cl.get("total", 0)
        start = max(0, total - 30)
        cl = curl(f"{base}/rest/api/2/issue/{ticket}/changelog?startAt={start}&maxResults=30",
                  email, token)
        for h in cl.get("values", []):
            ts = h.get("created", "")
            newmark = max(newmark, ts)
            if watermark is None or ts <= watermark:
                continue
            author = h.get("author", {})
            if author.get("emailAddress", "") in own:
                continue
            for item in h.get("items", []):
                field = item.get("field", "")
                frm = (item.get("fromString") or "—")[:60]
                to = (item.get("toString") or "—")[:120]
                kind = "status" if field == "status" else "change"
                events.append({
                    "source": "jira", "key": ticket, "kind": kind,
                    "author": author.get("displayName", "?"),
                    "summary": f"{field}: {frm} → {to}",
                    "url": url,
                })

        # comments: new + edited
        c = curl(f"{base}/rest/api/2/issue/{ticket}/comment?orderBy=-created&maxResults=15",
                 email, token)
        for com in c.get("comments", []):
            created, updated = com.get("created", ""), com.get("updated", "")
            newmark = max(newmark, created, updated)
            if watermark is None:
                continue
            author = com.get("author", {})
            if author.get("emailAddress", "") in own:
                continue
            body = com.get("body", "").replace("\n", " ")[:300]
            if created > watermark:
                events.append({"source": "jira", "key": ticket, "kind": "comment",
                               "author": author.get("displayName", "?"),
                               "summary": body, "url": url})
            elif updated > watermark:
                events.append({"source": "jira", "key": ticket, "kind": "comment-edit",
                               "author": author.get("displayName", "?"),
                               "summary": "(edited) " + body, "url": url})

        state[skey] = {"watermark": newmark or d["fields"].get("updated", "")}

    for pr in routing.get("github_prs", []):
        out = subprocess.run(
            ["gh", "pr", "view", str(pr["number"]), "--repo", pr["repo"],
             "--json", "state,statusCheckRollup"],
            capture_output=True, text=True, timeout=30).stdout
        if out:
            d = json.loads(out)
            build = next((x.get("conclusion") or x.get("status")
                          for x in d.get("statusCheckRollup", [])
                          if x.get("name") == pr.get("check", "build-and-push-docker")), None)
            sig = f"{d.get('state')}|{build}"
            gkey = f"gh:{pr['repo']}#{pr['number']}"
            if state.get(gkey) is not None and state[gkey] != sig:
                events.append({"source": "github", "key": f"{pr['repo']}#{pr['number']}",
                               "kind": "status", "author": "-",
                               "summary": f"PR state {d.get('state')}, build {build}",
                               "url": f"https://github.com/{pr['repo']}/pull/{pr['number']}"})
            state[gkey] = sig

    os.makedirs(HOME, exist_ok=True)
    json.dump(state, open(STATE, "w"), indent=1)
    for e in events:
        print(json.dumps(e, ensure_ascii=False))
    if not events:
        print("NO_NEW_EVENTS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
