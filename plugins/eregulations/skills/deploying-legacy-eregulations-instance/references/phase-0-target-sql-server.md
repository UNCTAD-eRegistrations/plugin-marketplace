# Phase 0 — Which SQL Server this instance gets

Decide this **before** phase 1. It changes where you restore, which password
you use, and how much damage a mistake can do.

**The rule: a production country gets its own dedicated SQL Server. Test,
pilot and demo instances stay on the shared one.**

## Why dedicated is the default for production

Not performance — measured on the migration host, both servers sit far below
their cache ceiling and the load is negligible. Three other reasons decide it.

**`00-dbe-consistency` is fleet-shared and approaching a hard limit.** Every
instance on a shared server writes its step history into that one database.
Measured 2026-09-02 on the migration host: **6 086 MB with 82 564 tickets**,
against SQL Server Express's **10 240 MB per-database hard cap** — 59 % used,
with only a handful of instances connected. When it hits the cap, *every*
instance on that server stops writing at the same moment. A dedicated server
carries only its own country's rows: the same database on the first converted
instance is **33 MB**.

**Blast radius during the migration itself.** Phases 1–5 restore, migrate a
schema, create and drop a temp database, and rewrite credentials — on the
target server, next to the countries already migrated. On a shared server a
mistake at country #7 reaches countries #1–6. On a dedicated server it reaches
nobody.

**Rollback.** A failed migration on a dedicated server is deleted by removing
one Coolify application and one data directory. On the shared server it means
`DROP DATABASE` plus deleting that instance's rows out of the shared
consistency and statistics tables, by hand, by `systemId`.

## What a dedicated server is

A **separate Coolify application** named `<slug>-sql`, built from
`instances/_dedicated-sql/docker-compose.yml` in `eRegulations-deploy`. It
joins the `eregulations-shared` docker network under the alias
`eregulations-<slug>-sqlserver` and publishes nothing. Separate application
means redeploying the country never restarts its database.

It must hold three databases before phase 1's country restore:

| Database | From |
| --- | --- |
| `00-dbe-consistency` | `templates/consistency-template.bak` — schema and `global_*` reference rows, no tickets |
| `00-dbe-statistics` | `templates/statistics-template.bak` — then insert this instance's `Systems` row |
| the country DB | phase 1 restores it here |

## How to create it

**Automatic.** The instance-provisioner does all of the above when the
descriptor carries `"dedicatedSql": true` (checkbox *Dedicated SQL Server* in
the monitor's Add-instance wizard). Prefer this.

**By hand.** Create the Coolify application from the compose file above with
`INSTANCE`, `SA_PASSWORD` (generate a fresh one), `SQL_DATA_DIR` (create the
host directory first, `chown 10001:10001`, or Coolify creates it root-owned and
SQL Server cannot write), and `SQL_MEMORY_LIMIT_MB`. Deploy, wait for the
healthcheck, restore the two templates.

**Converting an instance already on the shared server** is a different
procedure — `convert-to-dedicated.py` on the migration host. Not part of this
skill.

## What changes downstream

| | Shared | Dedicated |
| --- | --- | --- |
| `SHARED_SQL_HOST` | `eregulations-shared-sqlserver` | `eregulations-<slug>-sqlserver` |
| `SA_PASSWORD` | byte-identical to the shared server's — pull from a sibling | **this server's own, freshly generated** |
| Phase 1 name collision | real risk, check both names | server is empty, but run the check anyway |

## Capacity — the reason this is not automatic for everything

A dedicated server costs about **1 GB of RAM at idle**. The migration host has
30 GB. Ten instances with dedicated servers land around 25 GB with their
applications — it fits, without comfort. Beyond roughly ten, the host needs
more memory, a licensed SQL Server edition, or a second host. Do not hand a
dedicated server to a throwaway instance.

Always set `SQL_MEMORY_LIMIT_MB` explicitly. A server with no limit advertises
a target of the whole machine.
