# Resolving fleet facts

How the router learns which host an instance runs on, what version it runs, and
whether that host is safe to touch. This file describes **how to resolve**, not
**what the answers are** — no instance list, no hosts, no addresses ship here.

## The order

> **Monitor → operator overlay → unresolved.**

There is no third source and no guessing.

1. **Monitor is authoritative for STATE** — up/down, the version actually
   running, which server hosts an instance, SSL status. State changes without
   anyone editing a file, so only a live source can be right about it.
   **`posture` is the exception**: it is a judgement about whether a host is
   safe to touch, not state, and both sources can hold one — so the **more
   severe** value wins, whichever source it came from. See *Posture* below.
2. **The operator overlay** (`~/.ereg/fleet.local.json`) fills what Monitor
   cannot yet serve, and is the baseline the plugin ships in: every Monitor read
   endpoint sits behind authentication, so without an account there is no live
   path at all.
3. **Unresolved** is a real outcome, not an error to paper over. The fail-closed
   gates act on it — see `gates.md`.

The plugin itself is authoritative for **policy**: what is supported, which
gates exist, what each one does. Policy and state do not override each other
because they answer different questions.

## Running it

```bash
python3 <skill-dir>/scripts/fleet_resolve.py <instance-slug>
```

| Flag | Environment variable | Default |
| --- | --- | --- |
| `--overlay` | `EREG_OVERLAY` | `~/.ereg/fleet.local.json` |
| `--monitor-url` | `EREG_MONITOR_URL` | unset — overlay-only mode |
| `--token` | `EREG_MONITOR_TOKEN` | unset |

Output, as JSON:

| Field | Meaning |
| --- | --- |
| `instance` | the slug you asked for |
| `host`, `version`, `platform`, `posture` | the resolved facts |
| `version_major` | the leading component of `version`, e.g. `"7"` |
| `source` | `monitor` if a Monitor record was used, else `overlay` |
| `drift` | fields where Monitor and the overlay disagree |
| `unresolved` | fields no source could supply |
| `known_instance` | whether the slug was found at all — in Monitor, or in the overlay's `instances` |
| `known_slugs` | the full sorted roster of slugs the overlay knows about |

The last two are **resolution metadata, not gate context.** They describe what
the resolver could look the slug up in; they say nothing about the host, the
version, the platform or the posture. The gates do not read them and must not:
a slug somebody wrote down is not evidence about an instance, and treating it
as such is exactly the inference the fail-closed design forbids. They are not
copied into the gate context — see SKILL.md 4c.

They exist because `unresolved` cannot, on its own, tell a **typo** from a
**thin record**. A slug nobody has heard of and a slug recorded with no facts
behind it both come back with every field unresolved, and the two call for
opposite responses:

| | `known_instance` | `unresolved` | The response |
| --- | --- | --- | --- |
| Slug not recognised | `false` | everything | offer the nearest matches from `known_slugs` and ask which instance was meant |
| Recognised, thin record | `true` | what is missing | name the missing fields; add them to the overlay, or restore Monitor access |

`known_slugs` is drawn from the overlay because the overlay is the only scripted
source of a roster: Monitor is queried one slug at a time and is never listed.
An empty roster (no overlay, or one with no `instances`) is a real answer — it
means there is nothing to offer, not that the slug was recognised.

A missing overlay file is fine — it resolves to nothing and everything lands in
`unresolved`. A **malformed** overlay is not: it raises, naming the file, rather
than silently behaving as if it were empty. So does an **unreadable** one — a
permissions problem, or a directory where the file should be. Only *absent*
degrades to nothing: an overlay the resolver cannot read must not be reported as
one that was never written, or the remedy you are handed ("add the fact to the
overlay") is for a file that already exists and still cannot be read.

Monitor being unreachable is likewise not an error. It degrades to the overlay,
and whatever stays unresolved is what the gates block on.

## Drift

Where Monitor and the overlay disagree on a field, **Monitor wins and the
disagreement is reported** — for every field except `posture`, where the more
severe value wins instead:

```json
{"field": "version", "monitor": "7.2", "overlay": "5.1"}
```

Report every entry to the user. The overlay is a human artefact and drifts
silently otherwise; surfacing the disagreement is what gets it corrected by real
runs instead of left to rot. The router never edits the overlay itself — a fact
worth writing down is a fact worth a human deciding to write down.

## Posture

`posture` is the one field where Monitor does not simply win. The **more severe
value wins, whichever source supplied it**:

> `ok` < `degraded` < *unreadable* < `compromised`

Neither source overrules the other downwards. An operator who marks a host
compromised is not overruled by a Monitor that is stale or optimistic — that is
the whole reason the overlay lets them write it down — and equally a Monitor
reporting `compromised` is not overruled by a stale local `ok`.

An *unreadable* posture (a typo, a value that is not one of the three, anything
that is not a string) ranks above `degraded` because the `host_posture` gate
**blocks** on a posture it cannot read while only warning on `degraded`. It
ranks below `compromised` so that a garbage reading from one source cannot
displace a real `compromised` from the other and swap the gate's remedy
("migrate the instance off this host") for the wrong one ("record the host").

A source with nothing to say does not vote for safety: if only one source
supplies a posture, that value stands; if neither does, the field is unresolved
and the fail-closed gate blocks on it. The disagreement is reported as `drift`
either way — resolving to the severe value never hides it.

## Unresolved

Never fill an unresolved field by inference: not from the country name, not from
a sibling instance on the same host, not from what it was last month. A guessed
`posture` of `ok` is indistinguishable, to every gate downstream, from a
verified one — and that is precisely the failure the fail-closed design exists
to prevent.

The remedy is always one of: add the fact to the overlay, or restore Monitor
access.

## The overlay

`~/.ereg/fleet.local.json` — JSON, created by the operator, **never committed
anywhere**. JSON rather than YAML because bundled scripts are stdlib-only by CI
policy and PyYAML is a third-party package.

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

- `instances.<slug>.host` is a **name**, and it joins the two maps: posture is
  looked up as `hosts[instances[slug].host].posture`. A host named in
  `instances` but absent from `hosts` resolves to an unknown posture, **and
  unknown blocks**.
- `posture` is one of `ok`, `degraded`, `compromised`. Anything else, including
  a typo, is unknown — and blocks.
- `version` is the full version string; `version_major` is derived from it.
- `platform` is what the version gate's sibling `windows_target` reads; use
  `windows` for Windows/IIS.
- `address` and `vpn` are read by the operator and by the lane probes, not by
  the gates. They live **only** here.

`fixtures/fleet.sample.json` is a synthetic example of this shape, used by the
tests. It contains no real hosts.

## Populating it from what you already know

You do not need a fleet inventory to start. Add instances as you touch them:

1. **The slug** is whatever you call the instance in conversation. Be
   consistent — it is the lookup key.
2. **The host name** is a label of your choosing, not a hostname you must
   resolve. Several instances on one machine share one entry, which is the
   point: record the posture once.
3. **The version** — read it from the running instance or from Monitor. If you
   are not sure, leave it out. An absent version blocks, which is the honest
   outcome; a guessed one does not.
4. **The posture** — `ok` is a statement that you have reason to believe the
   host is sound, not a default. If a host is recorded elsewhere as likely
   compromised, write `compromised` here and let the gate do its job. That
   marking **holds even against a live Monitor reporting `ok`** — see
   *Posture* — so it is worth writing down even for an instance Monitor
   already covers.
5. **The address and VPN profile name** — copy them from wherever you keep them
   today. They never leave this file. See `access.md`.

Adding one instance is enough to unblock work on that instance. There is no
requirement to complete the fleet, and no penalty for a partial file beyond the
gates blocking on what is missing.
