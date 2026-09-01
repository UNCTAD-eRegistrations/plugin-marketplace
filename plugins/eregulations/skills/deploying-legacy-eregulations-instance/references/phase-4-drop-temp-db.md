# Phase 4 — Drop the temp Global DB, raise the compatibility level

Drop the temp Global DB. Bump the country DB (and Global DB before you drop
it, if you touch it further) to `COMPATIBILITY_LEVEL = 150` — required for
EF Core's `OPENJSON` queries.

## Keep both `.bak` files until phase 5 is verified

**Do not tidy the backup mount yet.** This phase reads as cleanup, and cleanup
invites clearing the `.bak`s off the mount in the same pass. That would
destroy the only rollback for phase 5.

Phase 5's credential hashing is the one **irreversible, non-idempotent** write
in this sequence: it overwrites every plaintext credential in place, and it
fails *silently* if the inner `CONVERT` is omitted — lengths look right, the
migration looks clean, and every login still fails. Its documented undo is
"restore the Global DB backup again into a fresh temp DB and copy `Password`
back", which only exists while the Global DB `.bak` is still on the mount.

Drop the temp *database* here. Delete the `.bak` *files* only once phase 5's
hash comparison against a known-good sibling has come back `MATCH`. See
`phase-5-credential-hashing.md`.
