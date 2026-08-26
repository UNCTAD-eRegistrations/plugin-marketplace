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
(`SiteMenu_i18n.Id` is identity everywhere observed so far):
```sql
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
```
Verify no orphans after: `Parent_Id` values all resolve within `SiteMenu`,
every `SiteMenu_i18n.Menu_Id` resolves to a `SiteMenu.Id`. **The sibling you
copy from doesn't have to be the same one used for the `Snapshot_*` diff or
the Coolify deploy-key lookup** — pick whichever sibling actually has the
language(s) this country needs (`SELECT lang, COUNT(*) FROM
[sibling].dbo.SiteMenu_i18n GROUP BY lang` to check first) and the most
complete `SiteMenu` row count, since siblings drift at different rates and
the one with more rows is usually the more current menu structure.
