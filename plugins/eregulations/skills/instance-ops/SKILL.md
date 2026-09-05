---
name: instance-ops
description: >
  Use when operating a 7.x eRegulations/TradePortal instance on the Coolify host — "what runs on
  burundi", "is comoros behind", "create the togo instance", "move X to stable", "hold burundi",
  "redeploy", "verify after the release", "adopt this old app", "write a descriptor for <uuid>".
  Drives `eregulations` (eRegulations-deploy/tools/eregulations.py): descriptor in git, plan before any
  change, drift from three sources. Not for releases (docs/RELEASING.md) and not for legacy Windows hosts.
allowed-tools: Read, Bash, Grep, Glob, Skill
metadata:
  version: "0.1.0"
  version-date: "2026-09-06"
---

# Operating an instance

Run `ereg-router` first: it resolves the instance and blocks on an unsafe host or an unsupported line.
Then, from `~/PROJECTS/02-eRegulations/eRegulations-deploy`:

| You want | Run |
|---|---|
| the fleet | `secret run EREGULATIONS_PROVISIONER_TOKEN COOLIFY_READ_TOKEN -- python3 tools/eregulations.py --json fleet` |
| one instance | `… instance show <slug> --json`, then `… instance diff <slug>` (exit 1 = drift) |
| a change | `… --dry-run instance apply <slug>` → read the plan → the same with `--yes` and the secret names in `secret run` |
| after a deploy | `… instance verify <slug>` |
| an app with no descriptor | `… instance import <uuid>`; fill the listed fields; `instance diff` must be clean before anything else |
| feed the router | `… fleet --for-router > ~/.ereg/fleet.json` |

## Rules

1. Never print, echo, log or paste a secret value. The CLI refuses to; so do you. Vault names only.
2. Never run a mutating command without its `--dry-run` plan in the transcript first.
3. Evidence is `/release.json` equality and a procedure id that exists (`/api/procedure/<id>`), not a 200 on a shell page.
4. The CLI does not change variables, domains, SQL apps or DNS. Say so and stop; do not PATCH Coolify yourself.
5. Production follows `stable`. `--allow-production-on-next` is the release manager's call, not yours.
6. A refusal (exit 1) is an answer. Report it with the provisioner's reason; do not retry with different flags.
