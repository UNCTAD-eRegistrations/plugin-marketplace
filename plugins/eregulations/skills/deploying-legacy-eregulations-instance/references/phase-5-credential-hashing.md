# Phase 5 — Hash the migrated credentials

**Hash the migrated credentials.** The old Global DB's `User.Password`
column is plaintext (check: `SELECT MIN(LEN(Password)), MAX(LEN(Password))
FROM [User]` — a real SHA256 hash is exactly 64 hex chars; plaintext values will be much shorter and vary in length). The current
`admin-api` login flow hashes the submitted credential with SHA256
(lowercase hex, no separators — `UserController.EncryptExistingUsersPasswords`
/ `POST /api/user/encrypt` does this exact transform) and compares against
the stored value, so plaintext rows can never log in. Run once, directly
against the country DB:
```sql
UPDATE [User]
SET Password = LOWER(CONVERT(VARCHAR(64), HASHBYTES('SHA2_256', CONVERT(VARCHAR(200), Password)), 2));
```
**The inner `CONVERT(VARCHAR(200), Password)` is not optional.** `Password`
is `nvarchar`; `HASHBYTES` on an nvarchar value hashes its raw UTF-16LE
bytes, but the app's `GetHash()` does `SHA256(Encoding.UTF8.GetBytes(...))`
— for any ASCII credential these are two completely different byte
sequences, hence two completely different hashes, even though both are
valid-looking 64-char hex strings. Skip the inner `CONVERT` and every stored credential silently becomes wrong: lengths look right, migration looks
clean, and every single login still fails. Verify before moving on — pick
one master username shared with an already-working sibling instance and
confirm the hash is byte-identical:
```sql
SELECT CASE WHEN
  (SELECT Password FROM [User] WHERE UserName = '<shared-master-username>')
  COLLATE DATABASE_DEFAULT =
  (SELECT Password FROM [<known-good-sibling-db>].dbo.[User] WHERE UserName = '<shared-master-username>')
  COLLATE DATABASE_DEFAULT
THEN 'MATCH' ELSE 'NO MATCH' END;
```

> **Limitation — this statement is only correct for ASCII credentials, and the
> `MATCH` check above will not catch the case where it is not.**
>
> `CONVERT(VARCHAR(200), Password)` converts `nvarchar` to `varchar`. Per
> documented SQL Server behaviour, characters with no representation in the
> database's code page are replaced with `?` during that conversion. So a
> credential containing an accented or non-Latin character is hashed from
> mangled bytes, and the application — which hashes the real UTF-8 bytes — can
> never reproduce it. That is the same silent, irreversible failure this
> section exists to warn about, arriving through a different door, and it
> survives the verification step: the shared master account's password is
> almost certainly ASCII, so `MATCH` is returned while every non-ASCII
> credential on the instance is quietly unusable.
>
> **On SQL Server 2019 or later**, hashing the UTF-8 bytes directly avoids the
> conversion entirely:
>
> ```sql
> UPDATE [User]
> SET Password = LOWER(CONVERT(VARCHAR(64),
>   HASHBYTES('SHA2_256', CONVERT(VARBINARY(400), Password COLLATE Latin1_General_100_CI_AS_SC_UTF8)), 2));
> ```
>
> Confirm the server supports a UTF-8 collation before using it —
> `SELECT SERVERPROPERTY('ProductMajorVersion')` must be 15 or higher, and
> `SELECT name FROM sys.fn_helpcollations() WHERE name LIKE '%UTF8'` must
> return rows. On an older server there is no in-database fix: hash those
> credentials outside SQL Server, or reset them.
>
> **Provenance:** the code-page replacement behaviour is taken from Microsoft's
> documentation for `CONVERT` between `nvarchar` and `varchar`, not from a run
> against a live instance — no SQL Server was available to execute it here.
> Confirm on your own instance before relying on either statement, ideally by
> hashing one deliberately non-ASCII test credential and attempting a login
> with it.
If you already ran the update without the inner `CONVERT`, the plaintext
is gone (overwritten) — restore the Global DB backup again into a fresh
temp DB, copy `Password` back from it by `ID` to undo the damage, then
re-run the corrected UPDATE above.

**That undo exists only while the Global DB `.bak` is still on the backup
mount.** Phase 4 runs before this one and reads as a cleanup step, so this is
a real way to lose the rollback: `phase-4-drop-temp-db.md` says to keep both
`.bak` files until this phase has been verified, for exactly this reason. If
the mount was already cleared, there is no undo — the plaintext credentials
are gone for good and every account has to be reset by hand.

Do this via direct SQL, not the `/api/user/encrypt` endpoint — that
endpoint requires `[Authorize]` with no anonymous override, which is
circular before any account can log in (nothing hashes correctly yet).
**This is NOT idempotent — running it twice double-hashes every credential
and locks everyone out again.** Verify with the length check above
(should read exactly 64/64 after) and never re-run it on the same DB.
