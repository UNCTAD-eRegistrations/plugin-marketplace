# Phase 2 — Schema migration, and the drift it does not cover

Apply the schema migration — **see the sections below before doing this — it changes the order of phases 2 and 3.**
Immediately after, run the `Snapshot_*` schema diff from the Snapshot-identity section below against a known-good sibling, and work
through the stale-views section below — none of
this is covered by the migration script you just ran (that's the whole
reason these gotchas exist), and finding it now beats finding it one
broken feature at a time later.

## Which migration script is current

The admin-api repo's `openspec/changes/.../scripts/` folder has several
generated migration SQL files, and **which one is current changes over
time — don't trust this skill's or anyone's memory of the filename, verify
fresh every time:**

1. Check `Migrate-UsersToLocalDB.ps1`'s `-MigrationsScript` default via
   `git log -p` on that one file — whichever file it defaults to *right now*
   is the maintained one. Don't assume the newest-dated file is it, and don't
   assume a past run of this skill picked the file that's still current: the
   default was seen flipping from `migrations_20260522_for_new_admin.sql`
   back to plain `migrations.sql` in a later commit, with no comment
   explaining why — it turned out `migrations.sql` had simply absorbed the
   same guarded, legacy-DB-safe content (confirm by diffing the two files'
   `MigrationId` values — if they cover the identical set, the plain-named
   file is just the newer copy of the same thing, not the "for empty DBs"
   variant its filename-less sibling implies).
2. **Then separately check for migrations newer than whatever's baked into
   that script.** List every migration `.cs` file under
   `Project/Unctad.eRegulations.Library/Migrations/` and compare its date/ID
   against the `MigrationId` values inside the script you picked. A migration
   can be committed to the repo (and even referenced in the commit that
   changed the default script) without ever being folded into either
   generated `.sql` file — it has to be applied manually. Read the migration's
   `Up()` method and hand-write the equivalent guarded SQL (same
   `IF NOT EXISTS (SELECT * FROM __EFMigrationsHistory WHERE MigrationId = ...)`
   pattern the generated scripts use, plus an `INSERT INTO __EFMigrationsHistory`
   at the end so future migration runs see it as already applied). **Check
   this migration for the same Role/Permission-existence-guard bug described in the next section before running it** — a new migration is exactly as likely to have
   it as an old one.

## Role must be seeded before ANY part of the schema migration runs

This is the single most dangerous gotcha in this skill because **it fails
silently.** Login works, the smoke test passes, and the instance looks fully
migrated — until someone actually tries to use the admin panel and finds they
have almost no rights, with no error anywhere to point at why.

The permission-system migration grants permissions to `Admin-Administrators`
and several other legacy roles (`Admin-Regulation-Publishers`, `-Updaters`,
`-Translaters`, `-Certifiers`, `Admin-Feedback`, `Consultant-Admin`) by
checking `EXISTS (SELECT 1 FROM Role WHERE Name = '...')` before each insert —
these guards exist specifically so the migration doesn't error on a DB where
`Role` is still empty. But "doesn't error" also means **the grant is just
silently skipped** if `Role` isn't seeded yet, and every one of these guarded
blocks lives in the *first* migration that touches permissions (the one
right after the migration that creates the `Role`/`User`/`User_Role` tables
themselves) — not in some later, easy-to-isolate block. A *separate*,
unrelated block later in the file (recycle-bin permissions) does the same
kind of grant *unconditionally*, which is what actually throws an error (FK
violation) if `Role` is empty — that hard failure is the one you're likely to
notice and work around, which makes it easy to assume you've handled the
whole problem when you've only handled the loud half of it.

**The fix:** seed `Role` from the temp Global DB immediately after the
migration that creates the `Role` table itself (the very first one in the
schema migration script), before any later migration section runs — not
"sometime before the recycle-bin block." In practice this means splitting the
migration script into two pieces at that boundary (find it by the
`__EFMigrationsHistory` `MigrationId` marking the end of the
table-creation migration, e.g. `..._AddUserManagementTables`), running part
one, seeding `Role`, then running everything else in one pass:

```sql
-- part A: only the migration(s) that create Role/User/User_Role/Permission tables
-- (ends right after that migration's COMMIT)

-- seed Role here, before anything else runs:
INSERT INTO [Role] (Name, Description)
SELECT Name, Description FROM [temp-global-<name>].dbo.[Role] src
WHERE NOT EXISTS (SELECT 1 FROM [Role] dst WHERE dst.Name COLLATE DATABASE_DEFAULT = src.Name COLLATE DATABASE_DEFAULT);

-- part B: everything else (permission grants, recycle-bin, later role additions, etc.)
```

If you've already run the whole script in one pass and only noticed the loud
FK-violation failure (and fixed just that), check for the silent kind too:
compare `SELECT Role_Name, COUNT(*) FROM RolePermission GROUP BY Role_Name`
against a known-good sibling. A role with a handful of rows where the sibling
has dozens is the signature of this bug. Recovery is safe and idempotent —
re-run each guarded `INSERT ... SELECT ... FROM Permission WHERE EXISTS
(SELECT 1 FROM Role WHERE Name = '...')` block from the migration file
directly (not the whole migration — its outer `IF NOT EXISTS (SELECT 1 FROM
RolePermission)` master guard will now skip everything since
`RolePermission` is no longer empty), adding
`AND <PermissionId column> NOT IN (SELECT Permission_ID FROM RolePermission
WHERE Role_Name = '...')` to each so it only inserts what's actually missing.

## SET QUOTED_IDENTIFIER when running migration SQL in pieces

Splitting `migrations.sql` (or writing any ad hoc fixup SQL) into separate
`sqlcmd -i` invocations loses the `SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS
ON;` header that's only ever at the very top of the original file — SQL
Server scopes these SET options per-batch/connection, they don't carry over
between separate `sqlcmd` runs. Any table with a filtered index (`User`,
`RolePermission`, and others) will fail every `INSERT`/`UPDATE` against it
with `Msg 1934: INSERT failed because the following SET options have
incorrect settings: 'QUOTED_IDENTIFIER'` until you prepend that same header
to *every* piece you run separately. The failure happens before any rows are
touched, so it's always safe to just add the header and re-run.

## Missing Snapshot table identity columns

None of the checked-in migration scripts cover this — it predates the whole
"advanced user rights" migration track entirely, and only shows up as pages
break one at a time (e.g. a procedure page 500s with `{"error": "The given
key was not present in the dictionary."}`, and the container logs show the
*real* error underneath: `SqlException: Invalid column name 'XyzId'`).

Root cause: a 2024-02-19 "code first" refactor added a surrogate `int
identity` primary key to every `Snapshot_*` *detail* table (the tables that
hold a frozen, versioned copy of a procedure's content each time it's
published — `Snapshot_Block`, `Snapshot_Step`, `Snapshot_StepRequirement`,
etc; `Snapshot_Registry` itself is unaffected). That refactor was applied
directly to whatever database the EF model snapshot was captured from — it
was never expressed as a migration file, so a DB restored from a backup that
predates Feb 2024 is missing all 19 columns, and nothing in
`openspec/changes/.../scripts/` re-adds them.

Don't wait for each one to break a different page. Right after the schema
migration (phase 2), diff every `Snapshot_*` table's columns
against a known-good sibling on the same shared SQL Server and fix all gaps
in one pass:
```sql
SELECT t.TABLE_NAME, c.COLUMN_NAME
FROM [<known-good-sibling-db>].INFORMATION_SCHEMA.TABLES t
JOIN [<known-good-sibling-db>].INFORMATION_SCHEMA.COLUMNS c ON c.TABLE_NAME = t.TABLE_NAME
WHERE t.TABLE_NAME LIKE 'Snapshot%'
AND NOT EXISTS (
  SELECT 1 FROM [<this-instance-db>].INFORMATION_SCHEMA.COLUMNS c2
  WHERE c2.TABLE_NAME COLLATE DATABASE_DEFAULT = c.TABLE_NAME COLLATE DATABASE_DEFAULT
  AND c2.COLUMN_NAME COLLATE DATABASE_DEFAULT = c.COLUMN_NAME COLLATE DATABASE_DEFAULT
)
ORDER BY t.TABLE_NAME, c.COLUMN_NAME;
```
As of this writing that returns exactly these 19 (table → missing column,
always `int identity(1,1) not null`, always the table's sole primary key,
always zero incoming foreign keys — confirm the FK part before blindly
applying with `SELECT * FROM sys.foreign_keys WHERE
OBJECT_NAME(referenced_object_id) = '<table>'` on the sibling, since that's
what makes it safe to let SQL Server auto-assign identity values to
existing rows):

| Table | Missing column |
|---|---|
| Snapshot_Block | BlockId |
| Snapshot_Object_Media | ObjectMediaId |
| Snapshot_Objective | ObjectiveId |
| Snapshot_ObjectiveSectionVisibility | ObjectiveSectionVisibilityId |
| Snapshot_Step | StepId |
| Snapshot_StepCost | StepCostId |
| Snapshot_StepEntityInCharge | StepEntityInChargeId |
| Snapshot_StepLaw | StepLawId |
| Snapshot_StepPersonInCharge | StepPersonInChargeId |
| Snapshot_StepRecourseEntityInCharge | StepRecourseEntityInChargeId |
| Snapshot_StepRecoursePersonInCharge | StepRecoursePersonInChargeId |
| Snapshot_StepRecourseUnitInCharge | StepRecourseUnitInChargeId |
| Snapshot_StepRegionalEntityInCharge | StepRegionalEntityInChargeId |
| Snapshot_StepRegionalPersonInCharge | StepRegionalPersonInChargeId |
| Snapshot_StepRegionalUnitInCharge | StepRegionalUnitInChargeId |
| Snapshot_StepRequirement | StepRequirementId |
| Snapshot_StepRequirementCost | StepRequirementCostId |
| Snapshot_StepResult | StepResultId |
| Snapshot_StepSectionVisibility | StepSectionVisibilityId |
| Snapshot_StepUnitInCharge | StepUnitInChargeId |

Fix per table:
```sql
ALTER TABLE [<Table>] ADD [<Column>] INT IDENTITY(1,1) NOT NULL;
ALTER TABLE [<Table>] ADD CONSTRAINT [PK_<Table>] PRIMARY KEY ([<Column>]);
```

**The diff can turn up more than these 19 over time, and not all of it is
this same identity-column bug** — a run against a different sibling also
found `Snapshot_StepRegionalEntityInCharge.GoogleMapsURL`, a plain nullable
`nvarchar`, not an identity/PK column. Before assuming a new diff result is
this bug, check whether the column is a legitimate, currently-tracked model
property (`git grep <ColumnName>` across `Model/`, `Business/`, and the
`Migrations/` folder in the admin-api repo — if it shows up in the current
EF model and an actual migration file, it's just a feature the source
backup predates, and the fix is a plain `ALTER TABLE ADD <Column> <Type>
NULL`, not an identity+PK) versus truly untracked (nothing references it in
current source — that's the hand-patched case above).

This class of bug isn't guaranteed to be limited to `Snapshot_*` — it's
whatever tables happened to get hand-patched on some reference DB outside
of migration tracking. If a *different* old-schema instance throws a fresh
"invalid column name" on a table this list doesn't cover, the same
diff-against-a-sibling technique (drop the `LIKE 'Snapshot%'` filter to
check other tables) finds it the same way.

**Confirmed second occurrence, different table, found the reactive way**
(not caught by the proactive diff — this one only surfaced when a user hit
the affected page): on one migrated test instance, `Admin_Menu` was missing
`IsVisibleInPublicHomePage` and `IsWidePage` (both `bit not null` in the
current EF model — `Unctad.eRegulations.Library/Model/Country/Menu.cs`).
Symptom was the Admin SPA's menu-translation list page (`/app/translation/
menus-translation/list`) returning a 500 whose body was the real SQL error:
`Invalid column name 'IsVisibleInPublicHomePage'. Invalid column name
'IsWidePage'.` — check the API's JSON error body first, it's usually the
actual `SqlException` text, not a generic 500 page. Root cause is the same
shape as the `Snapshot_*` bug: `Admin_Menu`'s `CREATE TABLE` migration is
guarded with `if (!CheckIfTableExist<Menu>())`, so on a DB where the table
already existed from an older backup, table creation — and these two
columns — were silently skipped. Fixed additively, defaulting both to
`false` for the instance's existing rows (matches the app's own
default-bool behavior, and is safe to run any time after the restore, not
just right after the schema migration):
```sql
ALTER TABLE Admin_Menu ADD IsVisibleInPublicHomePage BIT NOT NULL CONSTRAINT DF_Admin_Menu_IsVisibleInPublicHomePage DEFAULT 0;
ALTER TABLE Admin_Menu ADD IsWidePage BIT NOT NULL CONSTRAINT DF_Admin_Menu_IsWidePage DEFAULT 0;
```
This is the confirmation that the diff-against-a-sibling technique above is
worth running proactively on *every* table, not just `Snapshot_*` — this
one would have been caught by the same query with the `LIKE 'Snapshot%'`
filter dropped, before a user ever hit the broken page.

## Stale/dead legacy views and stored procedures

Not just `Snapshot_*` tables — the `CreateViews` migration (the one skipped
by `for_new_admin`/`migrations.sql` because it fails against a DB that
already has these objects) guards *every single view* it creates with
`IF NOT EXISTS (view)`. A legacy DB restored from an old backup already has
views under the same names, so the migration leaves every one of them exactly
as it was — 2012- or 2021-dated, none current. Nothing catches this at
migration time; it surfaces later as a specific feature failing with
something like `Invalid column name 'Type'` (that one was
`v_genericrequirement_dependencies` missing both the `[Type]` column and the
entire `Admin_StepResult`/"result" branch that "add a Result to a Step"
depends on). The DB also carries ~200 legacy stored procedures/functions from
before the EF Core rewrite, almost none of which current code calls anymore.

Both are safe to drop — they hold no data — but "drop and recreate" only
makes sense where a *current, canonical source* actually exists to recreate
*from*. Sort what you find into three buckets before touching anything, don't
apply one rule to all of it:

1. **Used by current code, source tracked in a migration — drop + recreate
   freely, zero risk.** This is every view the `CreateViews` migration
   creates (17 observed: `v_requirement`, `v_entityInCharge`,
   `v_genericrequirement(_dependencies)`, `v_law(_dependencies)`, `v_media`,
   `v_media_usage`, `v_menu_tree`, `v_menu_in_recycle_bin`,
   `v_public_menu_tree`, `v_personInCharge`, `v_regulation(_tree|
   _in_recycle_bin)`, `v_unitInCharge`, `v_xmlSerializedItem` — confirmed
   used by checking `CountryDbContext`'s `DbSet<...>` list, which is shared
   by admin-api and Public since Public references the same `Library`
   project). Extract every `CREATE VIEW` script straight from the current
   `CreateViews` migration file
   (`Project/Unctad.eRegulations.Library/Migrations/*_CreateViews.cs` — each
   is a C# verbatim string literal named `v_<name>_script`) and run
   `DROP VIEW` + `CREATE VIEW` for each:
   ```python
   import re
   with open('20240614081631_CreateViews.cs', encoding='utf-8-sig') as f:
       content = f.read()
   for varname, body in re.findall(r'string (v_\w+)_script\s*=\s*\n\s*@"(.*?)";', content, re.DOTALL):
       body = body.replace('""', '"')
       name = re.search(r'CREATE VIEW \[dbo\]\.\[(\w+)\]', body).group(1)
       print(f"IF OBJECT_ID('dbo.{name}', 'V') IS NOT NULL DROP VIEW [dbo].[{name}];\nGO\n{body.strip()}\nGO")
   ```
   (Migration filename/date will drift like everything else in this skill —
   find the current one with `git log` on the `Migrations/` folder, same as
   the schema-migration-script check.)

2. **Used by current code, but no source tracked anywhere in the repo — do
   NOT blindly drop.** `git grep`ing `ExecuteSqlRaw|FromSqlRaw|SqlQuery(` +
   `"EXEC dbo\."` across every `EF6*Repository.cs` (28 of them) plus
   `Business/`/`WebAppCore/`/`Presentation/` in the admin-api repo found
   exactly **one** live stored-procedure call in the whole codebase:
   `sp_on_updated_objective`, invoked from
   `EF6ObjectiveRepository.OnUpdatedObjective()`. It in turn queries
   `v_public_objective_tree`. Public calls zero stored procedures of its own
   but does read two more views directly, `V_partner` and `V_public_review`.
   None of these four objects — the one proc and three views — has a
   `CREATE VIEW`/`CREATE PROCEDURE` statement anywhere in current source
   (not in any migration, not in the legacy `Database/` scripts folder as
   far as this search found). There is no canonical "current" version to
   recreate from, so the only trustworthy definition is whatever a verified
   *currently working* sibling instance has — diff against one before
   assuming the version on your instance is fine, and never drop without
   first capturing a known-good replacement to restore from. (On the
   instance examined, copies of these four were last modified 2021–2024 and
   appeared to work
   for the one action tested — that's not the same as confirmed current.)
3. **Not referenced anywhere in current code — drop outright, nothing to
   recreate.** This is almost everything else: all `Community_*` objects
   (see the `Community_*` section below), the rest of the `sp_on_updated_*`
   family (`entityInCharge`, `genericRequirement`, `law`, `media`, `menu`,
   `menu_tree`, `personInCharge`, `StepRequirement`, `unitInCharge` — every
   one of these is dead despite several carrying 2024 dates, which just
   means someone re-ran a legacy bulk script, not that anything calls them),
   `sp_snapshot_get*`, `sp_*_dynamic_search`, `Public_Summary_*`,
   `Public_Generate_*`, `sp_helper_migrate_*`, `sp_populate_public_data_*`,
   `sp_on_published_*`, `sp_on_deleted_menu`, `sp_lock_snapshot_objective`,
   `sp_update_*Translation`, and the `fn_*` scalar functions. Confirm "not
   referenced" the same way bucket 2 was ruled in: grep the admin-api repo
   (Business/Data/WebAppCore/Presentation) and the Public repo for the exact
   name before dropping, since this list will drift per-instance and this
   search isn't guaranteed exhaustive. Also ignore (don't bother dropping)
   any `dt_*`-prefixed procedure — those are SQL Server's own built-in
   database-diagram tooling, unrelated to the application entirely.

## Leftover Community_* objects (tables, views, procedures, functions)

A DB restored from an old enough backup can carry a whole legacy
`Community_*` subsystem — not just tables but views, stored procedures, and
scalar functions implementing an entire parallel (and much older) user/login/
feedback/options layer. One observed instance had 11 tables
(`Community_Communities`, `Community_ActivityLog`, `Community_Country`,
`Community_Feedback`, `Community_Menu`, `Community_MenuInRoles`,
`Community_Option`, `Community_Lang`, `Community_LayoutHomePage`,
`Community_Catalog_CostVariables`, `Community_ExchangeRate`) plus 104
procedures/functions (`Community_UsersLoginUser`, `Community_UsersGetProfile`,
`Community_FeedbackAddFeedback`, `Community_GetAllOption`, etc. — check for
views too with `SELECT name FROM sys.views WHERE name LIKE 'Community%'`;
that instance had none, but don't assume every instance won't). Nothing in
the current admin-api references any of it (`git grep -i community` across
`Project/` returns nothing) — this is dead weight from a much older platform
version, not a schema gap to fix. Delete all of it.

Drop views and procedures/functions first (no FK constraints to worry about
for these — order doesn't matter among them), then tables last. Confirm no
FK reaches outside the `Community_*` table set before dropping tables
(`SELECT fk.name, OBJECT_NAME(fk.parent_object_id),
OBJECT_NAME(fk.referenced_object_id) FROM sys.foreign_keys WHERE
OBJECT_NAME(fk.parent_object_id) LIKE 'Community%' OR
OBJECT_NAME(fk.referenced_object_id) LIKE 'Community%'` — in the observed
instance the only FK was `Community_ActivityLog` → `Community_Communities`,
i.e. entirely self-contained):
```sql
DECLARE @sql NVARCHAR(MAX) = N'';

-- views
SELECT @sql += 'DROP VIEW ' + QUOTENAME(SCHEMA_NAME(schema_id)) + '.' + QUOTENAME(name) + ';'
FROM sys.views WHERE name LIKE 'Community%';

-- procedures and functions
SELECT @sql += 'DROP ' + CASE type WHEN 'P' THEN 'PROCEDURE' ELSE 'FUNCTION' END + ' ' + QUOTENAME(SCHEMA_NAME(schema_id)) + '.' + QUOTENAME(name) + ';'
FROM sys.objects WHERE type IN ('FN','IF','TF','P') AND name LIKE 'Community%';

EXEC sp_executesql @sql;

-- FKs, then tables
SET @sql = N'';
SELECT @sql += 'ALTER TABLE ' + QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id)) + '.' + QUOTENAME(OBJECT_NAME(parent_object_id)) + ' DROP CONSTRAINT ' + QUOTENAME(name) + ';'
FROM sys.foreign_keys
WHERE OBJECT_NAME(parent_object_id) LIKE 'Community%' OR OBJECT_NAME(referenced_object_id) LIKE 'Community%';
EXEC sp_executesql @sql;

SET @sql = N'';
SELECT @sql += 'DROP TABLE ' + QUOTENAME(TABLE_SCHEMA) + '.' + QUOTENAME(TABLE_NAME) + ';'
FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'Community%';
EXEC sp_executesql @sql;
```
Not urgent enough to block a deploy — safe to do any time after the restore,
including as part of the same pass as the `Snapshot_*` column fix.
