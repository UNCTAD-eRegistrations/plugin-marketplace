# Phase 4 — Drop the temp Global DB, raise the compatibility level

Drop the temp Global DB. Bump the country DB (and Global DB before you drop
it, if you touch it further) to `COMPATIBILITY_LEVEL = 150` — required for
EF Core's `OPENJSON` queries.
