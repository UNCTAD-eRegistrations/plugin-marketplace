# Lessons learned — upgrade-eregistrations-instance (orchestrator)

Retrospective from driving the full 2.13 → 2.18 chain against elsalvador LIVE (May 2026, first time the chain ran end-to-end on a CAS instance crossing the 2.14 boundary).

## Coordination with `/devops:cas-to-keycloak-orchestrator` is undocumented but matters

The orchestrator handles platform-version steps. A CAS instance crossing the 2.14 boundary picks up the Keycloak Quarkus block (2.13→2.14 Step 3.5), but the apps themselves are still on CAS — there are no `KEYCLOAK_URL` env vars to drop /auth from, no Keycloak-routed haproxy ACLs. The instance only becomes "functionally Keycloak" when `/devops:cas-to-keycloak-orchestrator` also runs.

The two orchestrators have an interaction the operator has to think through:

| Order | Pros | Cons |
|---|---|---|
| CAS→KC first, then upgrade | Keycloak block added at 2.13 baseline; upgrade chain sees a Quarkus block already present and skips Step 3.5; smaller per-step diffs | The keycloak image gets bumped to `:RC` then `:BETA` then `:2.17` then `:2.18` during the upgrade, each step a separate restart |
| Upgrade first, then CAS→KC | One Keycloak deploy at the end | The upgrade-2.13-to-2.14 Step 3.5 detects no Keycloak block (CAS instance) and skips Quarkus migration; CAS→KC then needs to add the Keycloak block on a 2.18 baseline; CAS images like `casbackend`, `casfrontend`, `partcbackend`, `eregpartc`, `myaccount` get bumped through `:RC` / `:BETA` / `:2.17` / `:2.18` but those tags don't exist in the registry — deploy fails until the operator hand-reverts them |

On elsalvador LIVE the operator chose CAS→KC first (with the orchestrator's "Phase 1 add-service" + "Phase 2 prepare-realm" landing on the 2.13 baseline), then ran the upgrade chain, then completed CAS→KC phases 3-8 on the upgraded 2.18 instance. This worked but required interleaving knowledge that neither orchestrator documents.

**Patch:**
1. **Add a STEP 0.5 to this orchestrator: "If the source instance is currently on CAS authentication, recommend running `/devops:cas-to-keycloak-orchestrator` first (phases 0-2) to land the Keycloak service block at the 2.13 baseline. Continue with the upgrade after."** Surface the trade-offs above.
2. **Mirror in `cas-to-keycloak-orchestrator`:** a corresponding STEP 0.5 that recommends running the upgrade chain after phases 0-2 if the instance is pre-2.14.

## CAS-era image tags don't exist in `:RC` / `:BETA` / `:2.17` / `:2.18`

Detailed in `upgrade-2.13-to-2.14/LESSONS.md` and applies across the whole chain: `casbackend`, `casfrontend`, `partcbackend`, `eregpartc`, `myaccount` don't have the platform-tagged versions. Each step in the chain re-bumps them, and each step's deploy fails on the missing tag until the operator unwinds.

For an orchestrator-managed multi-step chain, the issue is **compounded**: each sub-skill commits its own version, the chain squashes at the end, and the operator only sees the final state in the PR. If they merge the PR without inspecting per-step diffs they get a single squashed commit that's deploy-broken in 5 separate ways.

**Patch:** the orchestrator's STEP 5c "between-step pause" already asks the operator to verify each step's diff. But the failure mode here is silent — `casbackend:RC` looks like a normal image bump until you try to pull it. Add an explicit cross-step check before the squash: query the docker registry for each rewritten image's target tag; if any 404s, raise as an anomaly with default-abort. Operator can choose to skip or run a per-step revert.

## LIVE retype-country rail is good but not enough — operator skips ahead at the between-step prompts

elsalvador LIVE was the second time the chain ran through the between-step "Continue to step <i+1>?" pauses with a real operator. The first time (some country I-don't-recall in test), the operator answered "y to all" without inspecting the per-step diffs. The chain ran to completion, then the deploy failed mid-rollout. The retype-country rail at the start of the chain didn't help — the operator's intent was to do the upgrade; what they needed was a forced pause between each step to actually look at the diff.

**Patch:** the between-step pause should require typing a confirmation string (not just `y`/`N`), at least on LIVE. Something like: "type `step <i+1>` to continue, anything else aborts." Cheap friction, ensures the operator at least sees the step name.

## Apex-domain instances (no country subdomain) work but expose realm-name ambiguity

elsalvador LIVE uses `login.eregistrations.org` (apex) instead of `login.elsalvador.eregistrations.org` (country-subdomain) for Keycloak. The upgrade chain doesn't touch these URLs (Rules 5-9 in 2.13→2.14 drop `/auth` but apex/non-apex doesn't matter), so no issue surfaces during the upgrade itself. But the side effect is that the kenya reference instance uses country-subdomain, and the verify mode (and the per-step skill diffs) compare against kenya — so apex-domain instances flag every `https://login.investkenya.go.ke/...` ↔ `https://login.eregistrations.org/...` as a delta. Noise, not a bug.

**Patch:** the verify mode (in cas-to-keycloak) should normalize domain references when comparing — treat `login.<anything>` ↔ `login.<anything>` as equivalent for the structural-diff purpose. Or document that apex-domain instances will see expected noise and the operator should ignore domain-only deltas.

## Post-handoff BPA-backend boot crashes: Flyway `repair()` removes rows for renamed migrations

Not strictly the orchestrator's concern (this is BPA-backend Java behaviour), but the orchestrator's STEP 6 ("After the chain finishes…") is where it surfaces. Document here so operators landing on a BPA crash post-deploy know where to look.

The BPA `FlywayConfiguration.java` calls `flyway.repair()` before `flyway.migrate()` on every boot. If a migration script was **renamed in the codebase** (e.g. `V073.001__general_translation_aud_global_name_to_text.sql` was once committed as `V074.001__…` and applied with that name, then later renamed to V073.001), repair() sees the historical row's `script` doesn't match any resolved migration in the jar and **deletes the row**. Adjacent rows that *do* match the resolver survive. The first boot post-rename deletes the misnamed row; the second boot then sees ALL the lower-version migrations as "out of order" because the canonical max-applied dropped from 074.001 to 066.001.

On elsalvador LIVE this surfaced as: operator deleted 4 rows by hand thinking they were stuck; the *real* deletions were performed earlier by `flyway.repair()` on a 074.001-but-named-V073.001 rename mismatch. The 4 hand-deleted rows had to be re-INSERTed with NULL checksum to recover.

**Patch:** docs in this file (BPA-backend Java code, not in any skill's mutate scope). Pre-deploy detection query for the operator (run before the deploy that ships a renamed migration):
```sql
SELECT installed_rank, version, script FROM flyway_schema_history
WHERE script !~ ('^V' || REPLACE(version, '.', '\\.') || '__');
```
Any rows surfaced will be deleted by the next `flyway.repair()` — back them up first, decide whether to UPDATE the script to the new filename or accept the deletion.

## Post-handoff BPA-backend boot crashes: `-Dflyway.outOfOrder=true` via JAVA_OPTS silently ignored

Same scope-boundary as the previous lesson — surfaces during post-handoff but not the orchestrator's code to fix.

A natural reaction to "Detected resolved migration not applied to database: …" is to set `JAVA_OPTS=-Dflyway.outOfOrder=true` on the bpa-backend container, restart, and expect Flyway to pick it up. **It doesn't.** BPA's `Flyway.configure()` returns `new FluentConfiguration()` with no auto-loading of either JVM system properties (`-Dflyway.*`) or env vars (`FLYWAY_*`). Only explicit builder calls (`.outOfOrder(true)`) take effect. Spring's `spring.flyway.*` family also doesn't help — BPA disables Spring's Flyway auto-config (`spring.flyway.enabled=false`) and runs its own.

On elsalvador LIVE this cost an entire bpa-backend restart cycle. The workaround that worked: insert `flyway_schema_history` rows with NULL checksum for the known-applied-out-of-band migrations, let `flyway.repair()` recompute the checksums on next boot. Idempotent migrations + `spring.jpa.hibernate.ddl-auto=update` made this safe — Hibernate auto-created any tables the migrations would have created.

**Patch:** docs here. If you need outOfOrder semantics, edit BPA-backend's `FlywayConfiguration.java` and ship a new jar; JAVA_OPTS alone won't do it.

## Post-handoff BPA-backend boot quirks: Hibernate `ddl-auto=update` masks missing migrations

elsalvador LIVE's `eregistrationbpa` had migrations applied up to version `066.001` then jumped to `074.001` — 9 mid-range migrations (068.001 → 073.002) were never applied. Bpa-backend running with `spring.jpa.hibernate.ddl-auto=update` (the BPA convention) auto-created any new tables / columns the entities introduced, masking the missing migration files at runtime. Only Flyway's strict validation on next boot revealed the gap.

The 9 missing migrations were a mix of DDL (which Hibernate covered) and data fixups (which Hibernate doesn't). For data-fixup-only migrations the production state is functionally equivalent to "applied" — the operator can choose to mark them applied (`INSERT INTO flyway_schema_history` with NULL checksum + `flyway.repair()` recomputes on next boot).

This isn't the orchestrator's bug — BPA's been running this way for years. But the orchestrator's post-handoff is where a previously-silent gap becomes loud (the new jar's Flyway sees more files than the running DB tracked).

**Patch:** add to STEP 6 post-handoff checklist: "If bpa-backend boot crashes with `FlywayValidateException: Detected resolved migration not applied to database`, the gap is usually pre-existing (Hibernate auto-DDL covered the schema side). Reconcile via the NULL-checksum INSERT pattern documented in the lessons above."

## Quick reference — where each lesson landed

| # | Lesson | Patch landing site |
|---|---|---|
| 1 | Two orchestrator chains (upgrade + CAS→KC) interact, neither documents the ordering | new STEP 0.5 in both orchestrators with cross-links and trade-off table |
| 2 | CAS-era images get bumped through `:RC` / `:BETA` / `:2.17` / `:2.18` that don't exist in registry | per-step registry check before squash; default-abort on any 404 |
| 3 | Between-step `y`/`N` pause is too easy to skip | require typing `step <i+1>` at least on LIVE |
| 4 | Apex-domain instances see noise in verify-against-reference | normalize `login.<anything>` ↔ `login.<anything>` in the comparator |
| 5 | BPA-backend `flyway.repair()` deletes rows for renamed migrations | docs only — BPA-backend Java code, not in any skill's mutate scope; pre-deploy detection query |
| 6 | BPA-backend `-Dflyway.outOfOrder=true` JAVA_OPTS silently ignored by raw `Flyway.configure()` | docs only — BPA-backend code limitation; workaround is NULL-checksum INSERT |
| 7 | Hibernate `ddl-auto=update` masks pre-existing migration gaps that newer jars surface | STEP 6 checklist entry |
