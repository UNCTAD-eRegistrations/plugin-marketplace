# Gates

Five gates, evaluated by `scripts/gates.py` against one flat context dict.
This file explains what each one means. **It does not decide anything** — the
script does. If this file and the script ever disagree, the script is right and
this file is a bug.

Every gate declares a **failure direction**:

- **Fail closed** — if the input cannot be verified, the gate **blocks**. Used
  wherever proceeding on unverified data could damage a system or touch a
  compromised host. Unresolved input is treated exactly as harshly as
  confirmed-bad input. That is the design, not an oversight.
- **Fail open** — if the input cannot be verified, the gate does not block.
  Used only for advisory facts.

| Gate | Fires when | Direction | Overridable |
| --- | --- | --- | --- |
| `host_posture` | posture is `compromised`, **or unknown/unresolved** | closed | no |
| `branch_pair` | a build touches Admin + Public and the derived pair does not resolve | closed | no |
| `media_mount` | an Admin deploy without `/app/media` mounted | closed | no |
| `unsupported_version` | new work would land on 4.x / 5.x / 6.x | closed | **yes, audited** |
| `windows_target` | the target is Windows/IIS | open (advisory) | n/a |

---

## `host_posture`

**Context key:** `posture` — from `fleet_resolve.py` (Monitor, else the
operator overlay's `hosts.<host>.posture`).

**What it means.** Whether the machine this instance runs on is safe to work on
at all. `ok` passes. `degraded` warns and proceeds with care. `compromised`
blocks. **Anything else — including absent, unknown, or unresolved — blocks
identically to `compromised`.**

The value is compared case-insensitively with surrounding whitespace trimmed,
so `Compromised` and `  compromised ` reach the compromised branch and not the
unresolved one. That is not cosmetic: both spellings block, but they print
**different remedies**, and the remedy is the part an operator acts on. Told
the posture is unresolved, an operator does exactly what that remedy says —
records the host in their overlay, as `ok` — and a gate that was correct the
first time now passes. A value that is not a string at all is not a posture,
and blocks as unresolved.

**Why that direction.** This gate is the reason the plugin's design was revised.
A gate fed by a static table fails in both directions, and the dangerous one is
quiet: a stale record reading "not compromised" means **the gate silently never
fires**, and nobody notices, because a gate that does not fire looks exactly
like a gate that passed. Treating unknown as compromised converts that silent
failure into a loud one. An operator who knows better records the posture and
proceeds; nobody proceeds on a host the system cannot identify.

**When it fires.** If the host is genuinely compromised: **migrate the instance
off it. Do not repair in place** — work done on a compromised host cannot be
trusted afterwards, including the fix itself. If the posture is simply not
recorded, add the host to `~/.ereg/fleet.local.json` under `hosts`, or restore
Monitor access. Recording a posture is a deliberate human statement, which is
the point.

---

## `branch_pair`

**Context key:** `branch_pair_valid` — from `branch_pair.py`'s `valid`.
`touches_admin_public` gates it on the same three-way rule as `media_mount`
above: `true` activates, `false`/absent deactivates, anything else blocks. And
an explicit `branch_pair_valid: false` blocks regardless of that flag, and a
non-boolean `branch_pair_valid` blocks on the same rule as `media_mount`.

**What it means.** Public's web project carries a `ProjectReference` to Admin's
`Unctad.eRegulations.Library`. That reference has to resolve for the build to
succeed, so resolving it *is* the question "are these two checkouts a compatible
pair" — asked of the code rather than of a table someone has to remember to
update. Three outcomes, and the difference between the last two matters:
`true` resolves, `false` does not, `null` could not be determined — **and `null`
blocks**.

**Why that direction.** The whole justification for deriving this rather than
tabulating it is that the derived answer matches what the build will actually
do. An answer that cannot be derived carries no such guarantee, so it earns no
credit. The check is also **case-exact on every host**: a case-insensitive macOS
volume resolves references that `dotnet build` on Linux rejects, and a gate that
says `true` on a laptop and `false` in CI for the same checkout is worse than no
gate.

**When it fires.** Check out a pair whose project reference resolves, then
retry. If the reason names a case-divergent segment, the reference's spelling
and the directory's spelling differ — fix one of them; the build will need it
fixed regardless. If the reason is "could not read", the discovered `.csproj`
path is wrong: the Public web project's filename is **branch-dependent** and
must be discovered, never assumed.

---

## `media_mount`

**Context key:** `media_mount`. `targets_admin_deploy: true` activates the
gate; `false` or an absent key deactivates it; **any other value blocks**,
because a flag nobody can read must not be able to switch a safety gate off.
An explicit `media_mount: false` blocks regardless of that flag — negative
evidence is not withdrawn by a flag saying the check does not apply. The value
must be a real boolean: absent/`null` is "nobody looked", and anything else —
a quoted `"false"`, a `0` — **blocks**, naming the key and the type received.
Malformed evidence is treated no more kindly than a malformed flag.

**What it means.** Admin crashes on startup when `/app/media` is not mounted.
This gate asks whether the target instance's compose actually mounts it. `true`
passes, `false` blocks, and **`null` — could not confirm — blocks too**.

**Why that direction.** The failure it prevents is a deploy that brings the
instance down on start. An unverified precondition is not a satisfied one, and
the cost of blocking is one file read, while the cost of proceeding is an
outage.

**Producer note.** No script sets this key. The router reads the instance's
compose file for a volume targeting `/app/media` (short form
`- <source>:/app/media`, or long form `type: bind` with `target: /app/media`)
and sets `true`/`false`; if the compose cannot be read or the Admin service
cannot be identified, the key stays `null` and this gate blocks.

**When it fires.** Add the `/app/media` mount to the compose file before
deploying. If it fired on `null`, read the compose and confirm the mount by
hand, then retry.

---

## `unsupported_version`

**Context keys:** `version_major` (from `fleet_resolve.py`), plus `kind` and
`secondary_kinds` (from classification).

**What it means.** Policy is **7.x only** for new work. A `version_major` of
`7` passes. `4`, `5` or `6` blocks — **unless `upgrade` is among the request's
kinds**, in which case it passes: a request that is itself the migration to 7.x
must not be blocked by the gate whose own remedy is "upgrade the instance to
7.x". That exemption is shape-checked: `kind` must be the string `upgrade`, or
`secondary_kinds` must be a **list or tuple** of strings containing it — a
dict, a set or a bare string does not qualify. Any other value, including unresolved, blocks.

**Why that direction.** New work on a legacy line accumulates in a place the
organisation has decided to leave, and the decision is only real if something
enforces it. It fails closed on an unresolved version because "we do not know
what this runs" is not a licence to change it.

**Overridable — the only one.** Because the policy is organisational rather
than physical: a legacy line can be genuinely the right target for a specific
change, and a policy with no exception path gets routed around instead of
recorded. The exception is therefore **audited, not silent**:

```bash
python3 <skill-dir>/scripts/audit.py \
  --gate unsupported_version \
  --reason "<the reason the user actually gave>" \
  --context "$(cat /tmp/ereg-context.json)"
```

A blank or whitespace-only reason raises before anything is written, so a
refused override leaves no record and the block still stands. Records append to
`~/.ereg/audit.jsonl` — local, never committed. This is a memory aid and an
incident-reconstruction trail, **not an access control**.

**When it fires.** Fold the upgrade to 7.x into the change, or state a reason
and accept the audit record. If it fired because the version is unresolved,
resolve it — see `resolution.md`.

---

## `windows_target`

**Context key:** `platform`.

**What it means.** Windows/IIS is a transitional target. This gate warns; it
never blocks. `platform` is matched case-insensitively and trimmed, so
`Windows` warns exactly as `windows` does — a cased value must not silently
drop the advisory.

An unresolved `platform` passes, as fail-open requires, and **says that it is
unresolved**. It does not report "target is not Windows", which would be a
claim about the one fact this gate exists to report and one nobody resolved.

**Why that direction.** It is advisory. Most of the legacy fleet still runs on
Windows, and blocking there would stop routine work in order to make a point
about a migration that is already planned. The warning exists so the migration
stays visible in the requests that touch those instances.

**When it fires.** Nothing to do for this request. Plan the move to Ubuntu; do
not treat Windows/IIS as a long-term target.
