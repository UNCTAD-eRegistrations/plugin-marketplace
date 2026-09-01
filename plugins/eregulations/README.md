# eregulations

One front door for eRegulations work. Describe a development, deployment or
bugfix problem in plain English and the router takes it to the right
knowledge, resolves which instance and version it concerns, and blocks on
unsafe hosts, mismatched Admin/Public branches, and unsupported versions
before anything runs.

Plain English is the front door: plugin commands are namespaced
`plugin:command`, so a bare `/ereg` is not available from a plugin. The
explicit form is `/eregulations:ereg [--dry-run] <request>`.

## What the router does

It runs five steps before handing a request off to the work itself:

1. **Classify the request** — decide what kind of work this is (development,
   deployment, bugfix, or something else) so the right knowledge and skills
   get pulled in.
2. **Resolve the instance** — figure out which eRegulations instance the
   request concerns, from context or by asking.
3. **Resolve the version** — determine which platform version that instance
   runs, since behavior and fixes differ across versions.
4. **Check the safety gates** — look up the instance's host posture and
   Admin/Public branch alignment, and block if the host is unsafe, the
   branches mismatch, or the version is unsupported.
5. **Dispatch** — only once all gates pass, hand the classified, resolved
   request off to the appropriate skill.

See `skills/ereg-router/references/gates.md` for the gate rules in detail.

## No fleet data ships here

This repository is public. The plugin itself holds no fleet data — no
instance list, no host addresses, no credentials, no VPN details. All of
that lives in an operator-provided overlay file that is never committed
anywhere.

## Operator setup

The plugin ships no fleet data — this repository is public. Create your own
overlay at `~/.ereg/fleet.local.json` (JSON, never committed anywhere):

```json
{
  "instances": {
    "<instance-slug>": {
      "host": "<host-name>",
      "version": "7.2",
      "platform": "ubuntu"
    }
  },
  "hosts": {
    "<host-name>": {
      "posture": "ok",
      "address": "<address>",
      "vpn": "<vpn-profile-name>"
    }
  }
}
```

`posture` is one of `ok`, `degraded`, `compromised`. **A host you do not list
resolves as unknown, and unknown blocks** — that is deliberate. See
`skills/ereg-router/references/gates.md`.

## Verified (2026-08-26)

Phase A acceptance run, against the synthetic fixture
`skills/ereg-router/fixtures/fleet.sample.json` (`EREG_OVERLAY` pointed at it —
never a real overlay, since the fixture's `bravo` is deliberately compromised
and `charlie` deliberately unlisted). Wiring was confirmed first: resolving
`bravo` reports `"posture": "compromised"`, proving `EREG_OVERLAY` reaches the
script before any scenario below was trusted.

| # | Scenario | Outcome |
| --- | --- | --- |
| 1 | `bravo has started throwing 500s` (plain English, no command) | **NOT VERIFIED — requires local install.** Exercising the description-based front door needs a live session with the plugin installed; that install step is out of scope for this run (it would replace the operator's current marketplace source). To verify: `/plugin marketplace add <local-or-published-source>`, `/plugin install eregulations@unctad-digital-government`, then in a fresh turn type `bravo has started throwing 500s` with no command. Expect the router to fire unprompted and block on host posture `compromised`. |
| 2 | `charlie is down, need to look at it` (plain English) | **NOT VERIFIED — requires local install.** Same reason and setup as #1. Expect the router to fire unprompted and block on host posture unresolved (charlie's host is not listed in the overlay's `hosts` map) — the fail-closed assertion. |
| 3 | `I need to build admin and public together` (plain English) | **NOT VERIFIED — requires local install.** Same reason and setup as #1. Expect the router to fire unprompted and block on the derived Admin/Public branch pair, citing the actual `.csproj` reference it found. |
| 4 | Resolve `alpha` with `EREG_OVERLAY` unset and no Monitor, then evaluate gates | **Passed.** `fleet_resolve.py alpha` reported every advisory fact (`host`, `version`, `platform`, `posture`) unresolved. Feeding that context to `gates.py` blocked on two gates: `host_posture` ("host posture is unresolved") and `unsupported_version` ("target version is unresolved") — the fail-closed gates blocked on unverified facts as specified. |
| 5 | Gates on a `deploy` context for `delta` | **Passed.** `delta` resolves with a known host (`posture: ok`) and platform but no `version`. Gate evaluation blocked on exactly `unsupported_version` ("target version is unresolved"); `host_posture`, `branch_pair`, `media_mount` and `windows_target` all passed. |
| 6 | `audit.py` override with a blank reason, then with a real one (scratch log, never `~/.ereg/audit.jsonl`) | **Passed.** First call (`--reason ""`) raised `ValueError: an override requires a stated reason` and exit code 1; the scratch log file did not exist afterward. Second call, same context, a real reason, wrote exit code 0 and appended exactly one JSONL record to the scratch log (line count 1). `~/.ereg/audit.jsonl` was never created or touched by this run. |
| 7 | Gates on a compound context (`kind=bugfix`, `secondary_kinds=["upgrade"]`, `version_major="5"`) | **Passed.** `unsupported_version` returned `pass` with reason "target is 5.x, but this request is itself the upgrade to 7.x" — the upgrade passthrough recognised `upgrade` in `secondary_kinds` even though the primary kind was `bugfix`. All other gates passed. |
| — | Compromised posture vs. absent posture (fail-closed assertion) | **Passed.** `bravo` (posture `compromised`) and `charlie` (host absent from the overlay's `hosts` map) both evaluated to `host_posture: block` — same status, as fail-closed requires, with distinct reasons ("host is recorded as compromised" vs. "host posture is unresolved") so the operator can tell the two apart. |

Also run and clean, off the real repository (not the fixture):

- `uv run --python 3.9 --with pytest python -m pytest plugins/eregulations/skills -q` — 100 passed.
- `uv run --python 3.13 --with pytest python -m pytest plugins/eregulations/skills -q` — 100 passed.
  (Both bundled suites: 83 in `ereg-router/tests`, 17 in
  `merged-eregulations-translations-into-langadmin/tests`. CI runs each suite
  as its own pytest invocation, so the per-suite figures are what a CI log
  shows; the combined run is what this command reports.)
- `uv run --python 3.9 python -m compileall plugins/ -q` — clean compile, no errors.
- `python3 scripts/generate-kimi-manifests.py --check` — all manifests up to date.
- `uv run --python 3.12 scripts/validate-plugins.py` — 16 error(s), all pre-existing in other
  plugins; **none from `eregulations`**. `origin/main` reports the same 16, so this branch
  adds none. (An earlier revision of this block said 14: that was the baseline before
  `change-document` landed on `main` and contributed two.)

### Changelog entries

No CHANGELOG file exists anywhere in this repository to follow as precedent, and
this run made no functional change to any skill — `metadata.version` stays
`0.1.0` on all four skills, so `CLAUDE.md`'s "changelog entry on version bump"
rule does not trigger here. Where that entry should live for a future bump is
still open; see the maintainer note in the Phase A task plan.
