# Common mistakes

- Trusting a `.bak` file's extension — `file <path>` first, some arrive as
  `.zip` despite being a raw SQL Server backup.
- Running the user-data migration before the schema migration — the tables
  don't exist yet.
- Skipping the duplicate-username check and only noticing when two people
  share a login.
- Leaving the temp Global DB running on shared prod infrastructure longer
  than the same session.
- Forgetting the credential-hash step and wondering why literally no migrated
  account can log in (check `LEN(Password)` — 64 means already hashed).
- Hashing `nvarchar` directly with `HASHBYTES` instead of converting to
  `varchar` first — produces a 64-char string that looks right but is the
  wrong hash, so login *still* fails and the length check doesn't catch it.
  Always verify against a known-working sibling's hash for a shared master
  user, not just the length.
- Forgetting the three SSO env vars — login works but "Go to Admin" / any
  admin↔public handoff silently does nothing.
- Assuming the admin nav menu is baked into the Angular bundle and skipping
  it — it's per-country DB data (`SiteMenu`/`SiteMenu_i18n`), and a DB
  restored from an old backup carries stale, broken menu data even though
  every instance is supposed to show the identical menu.
- Deploying a fresh or ad hoc admin-api container without the `/app/media`
  bind mount — Admin has no existence check before wiring up `/media`
  static file serving, so it crashes on startup with a
  `DirectoryNotFoundException` instead of just breaking media links the
  way a missing chown would. See `phase-7-content.md`.
- Leaving `MultilangCentralRepository-<name>` as `root:root` instead of
  `chown 1654:1654` — every translation save 500s with a permission-denied
  error on a temp file, and this is easy to miss because phase 7's blanket content-folder chown doesn't cover it (it lives under the separate
  `shared/` path, not `/data/eregulations/<name>/`). See `phase-7-content.md`.
- Trusting that the migration scripts cover the *entire* schema gap. They
  only cover the advanced-user-rights tables. A DB old enough to predate
  that also predates other, untracked schema changes (see the Snapshot-identity section below) — run the sibling-diff check
  proactively instead of finding out one broken page at a time. Confirmed
  not limited to `Snapshot_*` — `Admin_Menu` hit the identical bug shape
  (`IsVisibleInPublicHomePage`/`IsWidePage` missing) and was only found
  reactively, from a live 500 on the menu-translation page, because the
  proactive diff had never been run without the `Snapshot%` filter.
- Running `docker ps | grep <instance-name>` to find an instance's
  containers and concluding it's not on this host when nothing matches —
  Coolify names containers with a random project suffix
  (`admin-api-<hash>-<timestamp>`), not the instance name. Match by Traefik
  label instead: `docker inspect <id> --format '{{ range $k,$v :=
  .Config.Labels }}{{ $k }}={{ $v }}\n{{ end }}' | grep <instance-name>` —
  the `caddy_0`/`traefik...rule` labels carry the actual hostname, and
  `coolify.resourceName`/`coolify.serviceName` carry the Coolify-side
  instance name. Same technique gets you straight to
  `ConnectionStrings__DefaultConnection` (DB name + the SA credential) via
  `docker inspect <id> --format '{{ range .Config.Env }}{{ println . }}{{
  end }}' | grep -i 'DB\|SQL\|CONNECTION'` on the matched container, instead
  of guessing the DB name from the instance name.
- Extracting the media zip with plain `unzip` — accented filenames from a
  non-UTF8-flagged, non-English-locale source silently end up under the
  wrong (but plausible-looking) name, and individual files "go missing"
  one broken link at a time. Use the CP850-aware Python extraction instead.
- Seeding `Role` right before the recycle-bin-permissions block instead of
  right after the table-creation migration — the recycle-bin block's FK
  violation is loud and gets fixed, but the permission-system migration's
  *guarded* role grants (several roles, not just `Admin-Administrators`) run
  earlier and fail silently instead, leaving the instance's admin accounts
  with almost no rights and no error anywhere. See `phase-2-schema-migration.md`.
- Treating a successful login as proof the migration worked. It only proves
  the credential hash is right. Compare `RolePermission` counts per role
  against a sibling before calling the migration done.
- Re-running a split-off piece of `migrations.sql` without re-adding
  `SET QUOTED_IDENTIFIER ON` — fails on the first `INSERT`/`UPDATE` against
  any table with a filtered index, before any rows are touched.
- Calling Coolify's `GET /api/v1/security/keys` to find a deploy key — it
  returns raw private key material in plaintext. Cross-reference a sibling
  app's `private_key_id` instead.
- Assuming the Coolify dashboard/API lives on the server you're deploying
  to — it's commonly a separate central instance managing that server over
  SSH.
- Leaving old `Community_*` tables, views, procedures, and functions in
  place because they don't error or block anything — they're a dead legacy
  subsystem from a much older platform version with zero current code
  references; drop all of it (see `phase-2-schema-migration.md`).
- Only checking `Snapshot_*` tables for schema drift and assuming the
  `CreateViews` migration's views are fine because they didn't error during
  the migration run. They didn't error because they were silently skipped
  (same `IF NOT EXISTS` guard pattern) — a legacy DB's own 2012/2021-era
  views stay in place untouched, and a specific feature breaks with a column
  error the first time someone exercises the exact query path the current
  view added. Refresh all of them proactively (see `phase-2-schema-migration.md`) instead of waiting for each one to
  surface reactively.
- Treating "drop and recreate" as a single blanket rule for all legacy
  views/procedures. It's genuinely risk-free for the objects with a current
  source tracked in a migration — but a handful of objects (one stored
  procedure, a few views) are still called by live code with *no* current
  definition tracked anywhere in the repo. Dropping one of those without
  first securing a known-good replacement destroys logic you can't get back,
  not "nothing to lose." Sort into the three buckets in that gotcha before
  touching anything.
