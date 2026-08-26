# Version lineage and support policy

> **This file is a hint for humans. It is not a source of truth and nothing
> enforces it.**
>
> The enforceable version fact comes from `scripts/fleet_resolve.py`, resolved
> per instance at runtime. The enforceable pairing fact comes from
> `scripts/branch_pair.py`, derived from the actual `csproj` project reference.
> A table of versions and branches in a public repo has nothing to correct it
> and rots quietly; these two paragraphs exist so a human reading a resolved
> context knows what the numbers mean.

## The lines

| Line | What it is | Status |
| --- | --- | --- |
| **4.x** | The original stack: `eRegulations-4.0-Admin`, `eRegulations-4.0-Public`, `eRegulations-4.0-API`. ASP.NET + SQL Server, deployed on Windows/IIS. Admin's `Unctad.eRegulations.Library` originates here and is still the project every later line references. | legacy |
| **5.x** | Adds the Angular admin SPA (`eRegulations-5.0-Admin-SPA`) in front of the 4.x Admin API. The server-side code is still the 4.x line. | legacy |
| **6.x** | The .NET 8 / EF Core 8 database-layer rework, carried on branches such as `database-layer-update-NET8`, and the point at which the stack becomes containerisable. | transitional |
| **7.x** | The current line. The only line new work may land on. | **supported** |

## The policy

**7.x only going forward.** New work targeting 4.x, 5.x or 6.x is blocked by the
`unsupported_version` gate. It is the one overridable gate, and only with a
stated reason that is written to `~/.ereg/audit.jsonl` before the work proceeds
— see `gates.md`.

One deliberate exception is built into the gate rather than left to judgement:
a request whose kinds include `upgrade` **passes** on a 4.x/5.x/6.x target,
because that request is the migration to 7.x. This is why the router carries
secondary kinds into the gate context.

**Windows/IIS is transitional.** Most of the legacy fleet still runs there. The
`windows_target` gate warns rather than blocks: the migration to Ubuntu is
planned, and stopping routine work would not make it happen faster.

## Two things this table cannot tell you

**Which line an instance actually runs.** Resolve it —
`python3 <skill-dir>/scripts/fleet_resolve.py <slug>` — and if it comes back
unresolved, that is the answer, and the gates act on it. Do not infer a version
from a country, a host, or a repository name.

**Which branches pair.** The line number does not live in the repository
directory name: repositories named `4.0` carry branches belonging to later
lines, so a checkout of `eRegulations-4.0-Admin` may well be 6.x. As recorded in
the design spec, the two local clones at the time of writing were Admin
`database-layer-update-NET8` (6.x) and Public `tradeportal` (5.x) — an invalid
pair that the branch-pair gate rejects. Derive the pair from the code; never
read it off a name.

## Repositories

| Repository | Holds |
| --- | --- |
| `eRegulations-4.0-Admin` | the admin server and `Unctad.eRegulations.Library` — the project everything else references |
| `eRegulations-4.0-Public` | the public portal / TradePortal web app |
| `eRegulations-4.0-API` | the API surface |
| `eRegulations-5.0-Admin-SPA` | the Angular admin SPA |
| `eRegulations-Statistics` | the statistics library referenced by the public build |
| `eRegulations-deploy` | compose files, per-instance content, and deployment docs |
| `eRegulations-Monitor` | the fleet dashboard and its API — the state source in `resolution.md` |

The pairing constraint follows from the first row: the Library is referenced by
the admin applications **and** by the public application, so a checkout that
suits one build can break the other. That is a fact about the code, which is why
the gate reads the code.
