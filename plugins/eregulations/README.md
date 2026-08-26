# eregulations

One front door for eRegulations work. The `/ereg` command routes a
development, deployment, or bugfix request to the right knowledge, resolves
which instance and version it concerns, and blocks on unsafe hosts,
mismatched Admin/Public branches, and unsupported versions before anything
runs.

## What `/ereg` does

`/ereg` runs five steps before handing a request off to the work itself:

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
