# Phase 1 — Restore both backups

SCP both `.bak`s to the shared sqlserver's backup mount. `RESTORE
FILELISTONLY`, then `RESTORE DATABASE` the country DB permanently (e.g.
`50-dbe-TradePortal-<name>` or `50-dbe-eRegulations-<name>`, matching
whatever the other live instances on that host use) and the Global DB into
a **temp** DB (e.g. `temp-global-<name>`) on the *same* SQL Server instance
— same-instance means the later user migration can just do cross-database
`INSERT ... SELECT` instead of the copy-paste-generated-INSERTs dance the
checked-in `Generic_0X_*.sql` scripts describe.

## Confirm both target names are free BEFORE restoring anything

**This is the only step in the whole sequence that can destroy another
country's data.** The SQL Server is shared and already hosts live instances,
and the naming convention above deliberately makes your target resemble its
neighbours — `50-dbe-TradePortal-<name>` differs from a live sibling's name by
a country slug and nothing else. `RESTORE DATABASE` onto an existing name
**overwrites that database in place**: no confirmation prompt, no automatic
rename, no undo, and the overwritten instance's own last backup is the only
way back.

Same shape as the FK pre-check in `phase-2-schema-migration.md` — run the
check, read the answer, then decide. Run this for **both** names and stop if
either comes back `IN USE`:

```sql
SELECT
  CASE WHEN DB_ID('<country-db-name>')  IS NULL THEN 'FREE' ELSE 'IN USE' END AS country_db,
  CASE WHEN DB_ID('temp-global-<name>') IS NULL THEN 'FREE' ELSE 'IN USE' END AS temp_global_db;
```

`IN USE` on the country DB means one of two things, and which one has to be
established before you type anything else:

- **You picked a name a live sibling already holds.** Pick a different one.
  `SELECT name FROM sys.databases ORDER BY name` lists what is actually on the
  host; compare against the instance list rather than against memory of the
  convention.
- **A previous run of this phase already restored it.** Re-restoring is fine,
  but confirm it is yours first (`SELECT TOP 1 * FROM
  [<name>].sys.database_principals`, the row counts, whatever identifies it),
  and take a fresh `.bak` of it before overwriting if anything has been done to
  it since. Only then add `WITH REPLACE`.

`IN USE` on the temp Global DB is usually a leftover from an aborted run —
drop it deliberately (`DROP DATABASE [temp-global-<name>]`) rather than
letting a `RESTORE` overwrite whatever it turns out to be.

Never reach for `WITH REPLACE` to make an `IN USE` result go away. That flag
is precisely the one that turns this step into someone else's outage.
