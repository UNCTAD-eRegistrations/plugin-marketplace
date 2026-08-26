# Phase 1 — Restore both backups

SCP both `.bak`s to the shared sqlserver's backup mount. `RESTORE
FILELISTONLY`, then `RESTORE DATABASE` the country DB permanently (e.g.
`50-dbe-TradePortal-<name>` or `50-dbe-eRegulations-<name>`, matching
whatever the other live instances on that host use) and the Global DB into
a **temp** DB (e.g. `temp-global-<name>`) on the *same* SQL Server instance
— same-instance means the later user migration can just do cross-database
`INSERT ... SELECT` instead of the copy-paste-generated-INSERTs dance the
checked-in `Generic_0X_*.sql` scripts describe.
