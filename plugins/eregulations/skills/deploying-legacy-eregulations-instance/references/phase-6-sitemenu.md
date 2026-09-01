# Phase 6 — Replace the admin `SiteMenu` data

**Replace the admin `SiteMenu` data with a known-good sibling's.** The
admin SPA's navigation isn't hardcoded in the Angular bundle — it's served
by admin-api's `GET /api/resources/sitemenu/{lang}`, which reads the
`SiteMenu` (+ `SiteMenu_i18n`) tables out of the *country* DB. A DB
restored from an old backup carries old menu rows (stale `Page` routes,
different structure) that predate the current admin SPA, even though the
menu is meant to be identical on every instance. Fix by replacing wholesale
from any known-good sibling on the same shared SQL Server. **Check whether
`SiteMenu.Id` is identity on *this* DB before assuming either way** — it's
plain int on some instances and identity on others; query
`SELECT COLUMNPROPERTY(OBJECT_ID('SiteMenu'), 'Id', 'IsIdentity')` first and
wrap the `SiteMenu` insert in `SET IDENTITY_INSERT` if it returns 1
(`SiteMenu_i18n.Id` is identity everywhere observed so far).

**Back both tables up first, then run the whole replacement in one
transaction.** The `DELETE`s and the `INSERT ... SELECT`s are a single logical
operation, and only the deletes are guaranteed to succeed: the insert is
*cross-database*, so it fails if the sibling DB name is wrong or the login
lacks read permission on it, and the `IDENTITY_INSERT` branch above is decided
by a query whose answer this file says varies by instance. Run bare and
unwrapped, any of those leaves the admin navigation deleted with nothing to
restore — the one destructive step in this runbook with no undo. Phases 1, 4
and 5 each document a way back; this one needs the same.

```sql
-- 1. The undo path. Keep these until the smoke test in phase 9 passes.
SELECT * INTO [SiteMenu_backup_<yyyymmdd>]      FROM [SiteMenu];
SELECT * INTO [SiteMenu_i18n_backup_<yyyymmdd>] FROM [SiteMenu_i18n];

-- 2. The replacement, all-or-nothing.
SET XACT_ABORT ON;
BEGIN TRANSACTION;

DELETE FROM [SiteMenu_i18n];
DELETE FROM [SiteMenu];

SET IDENTITY_INSERT [SiteMenu] ON;  -- omit if IsIdentity returned 0
INSERT INTO [SiteMenu] (Id, [Key], Name, Page, [Order], Image, Parent_Id, IsVisible, Type)
SELECT Id, [Key], Name, Page, [Order], Image, Parent_Id, IsVisible, Type
FROM [<known-good-sibling-db>].dbo.[SiteMenu];
SET IDENTITY_INSERT [SiteMenu] OFF;

SET IDENTITY_INSERT [SiteMenu_i18n] ON;
INSERT INTO [SiteMenu_i18n] (Id, Name, lang, Menu_Id)
SELECT Id, Name, lang, Menu_Id
FROM [<known-good-sibling-db>].dbo.[SiteMenu_i18n];
SET IDENTITY_INSERT [SiteMenu_i18n] OFF;

COMMIT TRANSACTION;
```

`SET XACT_ABORT ON` matters here: without it a statement-level error inside an
explicit transaction leaves the transaction *open* rather than rolling it back,
so a failed insert would sit there holding the deletes uncommitted until
whatever runs next commits them by accident or the session disconnects. With it
the batch aborts and rolls back as a unit. If the batch does fail, you are back
to the pre-run menu with nothing to restore by hand.

To undo after a successful but wrong-looking replacement, delete both tables
again and `INSERT ... SELECT` back from the two `*_backup_<yyyymmdd>` tables —
same `IDENTITY_INSERT` consideration, same transaction wrapper. Drop the backup
tables once phase 9's smoke test has confirmed the admin navigation renders.

Verify no orphans after: `Parent_Id` values all resolve within `SiteMenu`,
every `SiteMenu_i18n.Menu_Id` resolves to a `SiteMenu.Id`. **The sibling you
copy from doesn't have to be the same one used for the `Snapshot_*` diff or
the Coolify deploy-key lookup** — pick whichever sibling actually has the
language(s) this country needs (`SELECT lang, COUNT(*) FROM
[sibling].dbo.SiteMenu_i18n GROUP BY lang` to check first) and the most
complete `SiteMenu` row count, since siblings drift at different rates and
the one with more rows is usually the more current menu structure.
