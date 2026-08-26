---
name: deploying-legacy-eregulations-instance
description: >
  Use when standing up a legacy Windows/SQL-Server-hosted eRegulations or
  TradePortal country instance as a new per-country application on the
  shared-services Coolify host — symptoms include having a raw `.bak` country
  DB backup, an old "Global DB" `.bak`, a content zip
  (Multilang/PublicConfig/PublicContent/media), and an old `Web.config` to
  migrate onto eRegulations-deploy's shared sqlserver + Coolify architecture.
  Triggers on "deploy <country> to Coolify", "stand up the legacy instance",
  "migrate this .bak onto the shared SQL Server". This is the `deploy` dispatch
  target of `ereg-router` for a legacy instance. DO NOT TRIGGER for redeploying
  an instance that already exists on Coolify (that is a plain redeploy), or for
  a 7.x-native instance that was never on the legacy Windows stack.
allowed-tools: Read, Bash, Grep, Glob
metadata:
  version: "0.1.0"
  version-date: "2026-08-26"
  argument-hint: "[country-slug]"
---

# Deploying a legacy eRegulations/TradePortal instance to Coolify

Every instance follows the same shape: restore two old `.bak` files, catch the
country DB up to the *current* admin-api schema, migrate its old Global-DB
users into the new local user-rights tables, drop in content, then create a
Coolify application.

The mechanical steps are in `eRegulations-deploy`'s `docs/NEW-INSTANCE.md` and
`COOLIFY-MULTI-INSTANCE.md` — **read those first**. This skill covers the parts
that are not written down there and will bite you if you improvise.

Each phase below is a summary. **Open the phase's reference file before running
it** — the detail that makes each phase safe lives there, not here.

## Inputs — check all four before touching any infrastructure

Ask for whatever is missing now, not mid-migration.

| Input | Check |
| --- | --- |
| Country `.bak` | `file <path>` says `Windows NTbackup archive` / `Microsoft SQL Server`. Never trust the extension — these often arrive named `.zip`. |
| Old Global DB `.bak` | Same `file` check. Holds pre-migration Users/Roles/UserFeedback. **A separate file from the country backup and the one most often missing from a handoff** — without it you can only seed shared master users. |
| Old `Web.config` | Extract `SystemInstanceID` (old numeric ID, scopes the user migration), `CountryName`, `CountryCode` (often blank — confirm the ISO code with the handoff, do not guess), `DefaultLang`, `Currency`. |
| Content zip | `unzip -l` shows `Media`/`media`, `Multilang`, `PublicConfig`, `PublicContent` somewhere inside, whatever the top-level prefix and casing. Extra `ftp/`, `upload/` folders are normal. |

## The nine phases

1. **Restore both backups** — country DB permanently, Global DB into a temp DB
   on the *same* SQL Server instance so later steps can do cross-database
   `INSERT ... SELECT`. → `references/phase-1-restore.md`
2. **Schema migration** — plus the drift the migration scripts do *not* cover:
   `Snapshot_*` identity columns, stale legacy views and procedures, leftover
   `Community_*` objects, `SET QUOTED_IDENTIFIER`.
   → `references/phase-2-schema-migration.md`
3. **Migrate users** — master users + this instance's own users + `User_Role` +
   `UserFeedback`, with `COLLATE DATABASE_DEFAULT` on every cross-database
   comparison and a duplicate-username check first.
   → `references/phase-3-user-migration.md`
4. **Drop the temp Global DB**, then set `COMPATIBILITY_LEVEL = 150` — required
   for EF Core's `OPENJSON`. → `references/phase-4-drop-temp-db.md`
5. **Hash the migrated credentials** — the legacy column is plaintext, so no
   migrated account can log in until this runs. **Not idempotent.**
   → `references/phase-5-credential-hashing.md`
6. **Replace the admin `SiteMenu` data** from a known-good sibling — the nav is
   per-country DB data, not part of the Angular bundle.
   → `references/phase-6-sitemenu.md`
7. **Content folders** — extract (not with plain `unzip`), `chown -R 1654:1654`,
   and confirm both the `/app/media` mount and the separate
   `MultilangCentralRepository-<name>` ownership.
   → `references/phase-7-content.md`
8. **Create the Coolify application** — env vars, the right creation endpoint,
   then `docker_compose_domains` and deploy.
   → `references/phase-8-coolify-app.md`
9. **Smoke test** — containers healthy, homepage 200, *a real procedure page*
   200, and a `RolePermission` count comparison against the sibling. A
   successful login proves almost nothing.
   → `references/phase-9-smoke-test.md`

`references/common-mistakes.md` collects the failure modes seen in practice —
worth reading once before the first run.

## Decision points

These are the places where doing the obvious thing produces a silently wrong
instance. None of them can be answered from memory.

- **Which migration script is current** — verify fresh every time from
  `Migrate-UsersToLocalDB.ps1`'s `-MigrationsScript` default, then separately
  check for migrations newer than the ones baked into it. The default has
  flipped between files with no explanatory comment. (Phase 2)
- **`Role` must be seeded before *any* permission-granting migration runs** —
  not "before the recycle-bin block". The permission grants are guarded with
  `EXISTS (SELECT 1 FROM Role ...)`, so an unseeded `Role` table makes them
  *skip silently*: login works, smoke test passes, and admins have almost no
  rights. This splits phase 2 and reorders it against phase 3. **The single
  most dangerous item in this skill.** (Phase 2)
- **Legacy views and procedures sort into three buckets, not one rule** —
  tracked in a migration (drop + recreate freely), used by live code with no
  tracked source (never drop without capturing a known-good copy first), and
  unreferenced (drop outright). (Phase 2)
- **Which sibling to copy from** — the `SiteMenu` sibling, the `Snapshot_*`
  diff sibling and the Coolify deploy-key sibling do not have to be the same
  instance. Pick per purpose; siblings drift. (Phases 2, 6, 8)
- **`SiteMenu.Id` is identity on some instances and plain int on others** —
  query `COLUMNPROPERTY(...)` before assuming either way. (Phase 6)
- **Which values are shared and which are fresh** — `SA_PASSWORD` must be
  byte-identical to the shared sqlserver's actual value (pull it from a sibling
  app or ask the operator; never generate it). The three SSO variables are
  per-instance and *should* be freshly generated. (Phase 8)
- **Which Coolify creation endpoint** — `/applications/public` accepts an SSH
  git URL, returns 200, and then fails every deploy with
  `Permission denied (publickey)`, because it attaches no key. Use
  `/applications/private-deploy-key`. `private_key_uuid` can only be set at
  creation and is rejected on `PATCH`, so getting this wrong means deleting and
  recreating the app. (Phase 8)

## Scope

This skill covers the migration onto Coolify. It does not cover DNS, TLS
issuance, or the shared sqlserver's own provisioning — those are the
`eRegulations-deploy` docs' territory.
