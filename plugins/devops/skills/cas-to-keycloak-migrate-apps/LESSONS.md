# Lessons learned — cas-to-keycloak-migrate-apps

Retrospective from running the migrate-apps phase against elsalvador LIVE (May 2026, second production cutover after cuba).

## ds-frontend service creation: nobody actually does it

STEP 4.5 in this skill says, paraphrased: *"if ds-frontend is present, update its env vars; if absent, leave it alone — `upgrade-2.16-to-2.17` Rule 5b adds it."* The 2.16→2.17 skill's Rule 5b says, paraphrased: *"if ds-frontend is present, leave it alone; if absent, add it from a template."* Both skills are idempotent-when-present and **defer-when-absent**, so when an instance lacks ds-frontend entirely (elsalvador never had it — it shipped the legacy `eregcms` UI on `ds-backend` since 2.13), **neither skill creates it**. The result: the upgrade chain + CAS→KC cutover both run cleanly, no anomaly fires, and the operator only discovers the gap when they try to use the new DS UX and hit a 404 on root.

On elsalvador LIVE I (the agent) compounded the bug by *explicitly* skipping 2.16→2.17 Rule 5b citing "Phase 6 of the CAS-KC chain creates ds-frontend." It doesn't. Phase 6 *is* this skill (migrate-apps), and STEP 4.5 said the upgrade chain handles it. The circular justification went unchallenged for the entire migration window and only surfaced when the operator hit the URL.

**Patch:** rewrite STEP 4.5 so it is the **single owner** of ds-frontend creation. If the service block is absent, the skill creates it from the canonical template (mali pattern), adapting domains, realm, institutions-group-id, and the public-client `OAUTH_CLIENT_ID` (resolved from the realm.json's `ds-fe-client` clientId, not the legacy mali-style `display-system-frontend`). The 2.16→2.17 Rule 5b should be deprecated to a no-op (or removed) — letting the upgrade chain decide a structural service-add is the wrong layer.

## Sidecar work the skill *doesn't* touch but should warn the operator about

The skill's title implies "flip the apps to Keycloak." Operators reasonably expect that when this runs successfully, the new DS UX works end-to-end. It doesn't, because the skill doesn't (and shouldn't) own the haproxy routes ds-frontend needs to be reachable. On elsalvador LIVE three follow-up edits were necessary, each catching a different "but the apps don't work" surprise:

1. **haproxy: ds-frontend backend + path-based use_backend rules** for `/parta/`, `/services/`, `/manage-business-entity/`, `/redirect/`, `/business-list`, `/login`, `/version`, `/health`, `/part-b` (except `/part-b/edit/*`), `/inspector`, `/financial-report`, and root `^(\/{0,1}$)`. Without these, the user lands on the legacy ds-backend (cms) and gets 404 at root.

2. **haproxy: ds-backend WebSocket route** at `/backend/ws/user-updates-stream/` plus the `Connection: upgrade` + `Upgrade: websocket` header ACLs. The new ds-frontend's `WEBSOCKET_INTEGRATION_ACTIVE=1` reconnects forever without this. Also requires `ds-backend` to expose port 6024 (mapped to internal 8081) — kenya has this in compose; elsalvador didn't until we added it.

3. **haproxy: chrome-url-to-pdf backend** with a load-balanced server pool on ports 8008-8011 and a `replace-path /chrome-url-to-pdf/(.*) /\1\2`. The service is in compose since 2.17 but unreachable without a haproxy route. PDF generation in BPA fails silently.

**Patch:** add an explicit "STEP 5.5: HAProxy companion edits the operator must apply" section to the SKILL.md, with the exact ACL + use_backend + backend bodies for each of the three items, and a note that they are NOT auto-applied by this skill (haproxy.cfg edits are scoped to CAS/PARTC removal only). Cross-link to `cas-to-keycloak/LESSONS.md` lesson #20 (sidecar haproxy work).

## Frontend secrets become dead refs after the cutover

After the migrate-apps cutover, public clients (bpa-frontend, statistics-frontend, ds-frontend) have `OAUTH_SECRET=null` — they're public clients in Keycloak, no secret needed. But the top-level `secrets:` block in docker-stack.yml still declares `BPA_FE_OAUTH_CLIENT_SECRET`, `STATISTICS_FE_OAUTH_CLIENT_SECRET` (and historically `CAS_FE_OAUTH_CLIENT_SECRET`, `PARTC_FE_OAUTH_CLIENT_SECRET`, `NOTARY_CAS_CLIENT_SECRET`). They're orphaned — no service references them, but they're declared as `external: true` and will fail `docker stack deploy` if the operator removed the corresponding docker secrets thinking they were no longer needed.

**Patch:** add `BPA_FE_OAUTH_CLIENT_SECRET` and `STATISTICS_FE_OAUTH_CLIENT_SECRET` to STEP 3.5's removal list alongside the CAS/PARTC/NOTARY_CAS family. Operator notes should mention "these docker secrets can also be removed from the swarm host post-cutover."

## Secret rotation strategy needs operator guidance

Phase 6 needs 3 new docker secrets (`BPA_BE_OAUTH_CLIENT_SECRET`, `CAMUNDA_OAUTH_CLIENT_SECRET`, `STATISTICS_BE_OAUTH_CLIENT_SECRET`) and 2 rotated ones (`DS_OAUTH_CLIENT_SECRET`, `GDB_OAUTH_CLIENT_SECRET` had pre-existing CAS-era values that must be replaced by new realm-generated UUIDs). Docker secrets are immutable in swarm — rotation requires `docker secret rm` + recreate, and the secret is in-use until the next `docker stack deploy`. There's a chicken-and-egg ordering risk: remove the secret too early → services using it crash; redeploy too early → services pick up the new value before the rotation runs.

The operator workflow that worked on elsalvador: create the 3 new secrets *first* (no services reference them yet), then `docker stack deploy` (now bpa-backend etc. reference them and the old DS/GDB secrets), then `docker secret rm DS_OAUTH_CLIENT_SECRET GDB_OAUTH_CLIENT_SECRET && recreate with new values && docker service update --force eregistrations_ds-backend eregistrations_gdb` (force re-read of the rotated secret).

**Patch:** add a "Secret rotation runbook" section to the SKILL.md with the exact ordering. Include a `rotate-secret.sh` helper that takes `<name>` and `<new-value>` and does the rm + recreate + force-recreate dance.

## Quick reference — where each lesson landed

| # | Lesson | Patch landing site |
|---|---|---|
| 20 | ds-frontend creation falls between two stools (upgrade Rule 5b vs migrate-apps STEP 4.5) | rewrite STEP 4.5 as the single owner; deprecate 2.16→2.17 Rule 5b |
| 21 | HAProxy companion edits not in scope but always needed | new STEP 5.5 with ACL/backend bodies for ds-frontend routes, DS WS route, chrome-url-to-pdf route |
| 22 | Frontend `*_FE_OAUTH_CLIENT_SECRET` declarations linger as dead refs | STEP 3.5 also strips `BPA_FE_OAUTH_CLIENT_SECRET`, `STATISTICS_FE_OAUTH_CLIENT_SECRET` |
| 23 | Docker secret rotation needs explicit ordering or services crash mid-cutover | new "Secret rotation runbook" section + helper script |

(Moved out of this file's scope: `ds-fe-client` vs `display-system-frontend` mismatch and `license-registry:` → `gdb:` service-block rename now live in `upgrade-2.16-to-2.17/LESSONS.md` — both are patches against the upgrade-step's image-handling rules, not against migrate-apps.)
