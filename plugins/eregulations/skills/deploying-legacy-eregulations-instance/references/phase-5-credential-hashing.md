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
