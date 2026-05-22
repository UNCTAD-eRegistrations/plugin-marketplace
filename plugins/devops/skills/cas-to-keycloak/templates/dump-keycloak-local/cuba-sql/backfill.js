// Idempotent backfill of missing realm roles + role assignments against an
// already-seeded Keycloak realm.
//
// Use case: a Keycloak realm was seeded from the previous (buggy) keycloak.sql
// dump, which silently dropped ~190 role assignments and never created the 12
// Cuba-specific admin realm roles (VUCE/FITO/RCP/INHEM/ONURE/ZOO/RCENASA/ORSA/
// ONN/FARMYOPT/CERTSAN/CECMED). Instead of taking the realm down and re-
// importing the regenerated dump, this script reaches into the running realm
// and applies the diff.
//
// Inputs (read from migrator-workdir/, produced by extract.sh):
//   user-roles.json   - target state: { attribute_cas_user_id, role_name, realm_role, client }[]
//   users.json        - cas_user_id -> username mapping
//
// Env vars (same names as migrate.js so the same .env works):
//   AUTH_URL                  Keycloak base URL (e.g. https://login.example/)
//   AUTH_REALM_NAME           Target ops realm (e.g. CU)
//   AUTH_ADMIN_USERNAME       master realm admin username
//   AUTH_ADMIN_PASSWORD       master realm admin password
//   AUTH_ADMIN_CLIENT         master realm admin client (admin-cli)
//
// Behaviour:
//   1. Ensures every distinct realm role referenced in user-roles.json exists
//      in the target realm (creates if missing).
//   2. Looks each user up in the target realm by username (no users are
//      created — backfill is purely additive role mapping). Users that aren't
//      present yet are reported and skipped.
//   3. For each user, diffs current realm-role mappings against the desired
//      set in user-roles.json and adds only what's missing.
//   4. Same diff/apply pass for client-role mappings (bpa-frontend.BPA,
//      bpa-backend.BPA, bpa-frontend.TUTORIAL).
//   5. Re-running is a no-op once converged.
//
// The script auths against the master realm (where admin lives) but operates
// against AUTH_REALM_NAME, so a single client instance is configured for ops
// and the auth call temporarily swaps realmName — same pattern migrate-
// wrapper.js uses for the import flow.

const KcAdminClient = require('keycloak-admin').default;
require('dotenv').config();

const users = require('./users.json');
const userRoles = require('./user-roles.json');

const OPS_REALM = process.env.AUTH_REALM_NAME;

const origAuth = KcAdminClient.prototype.auth;
KcAdminClient.prototype.auth = async function (credentials) {
  const ops = this.realmName;
  this.setConfig({ realmName: 'master' });
  try {
    return await origAuth.call(this, credentials);
  } finally {
    this.setConfig({ realmName: ops });
  }
};

function indexUserRolesByCasId() {
  const realm = new Map();
  const client = new Map();
  for (const r of userRoles) {
    const bucket = r.realm_role ? realm : client;
    const list = bucket.get(r.attribute_cas_user_id) || [];
    list.push(r);
    bucket.set(r.attribute_cas_user_id, list);
  }
  return { realm, client };
}

async function ensureRealmRoles(kc) {
  const names = [...new Set(userRoles.filter(r => r.realm_role).map(r => r.role_name))];
  const created = [];
  for (const name of names) {
    const existing = await kc.roles.findOneByName({ name, realm: OPS_REALM });
    if (existing) continue;
    await kc.roles.create({ name, realm: OPS_REALM });
    created.push(name);
  }
  return { total: names.length, created };
}

async function resolveRealmRoleHandles(kc) {
  const names = [...new Set(userRoles.filter(r => r.realm_role).map(r => r.role_name))];
  const handles = {};
  for (const name of names) {
    const role = await kc.roles.findOneByName({ name, realm: OPS_REALM });
    if (!role) throw new Error(`Realm role '${name}' missing after ensureRealmRoles (should not happen)`);
    handles[name] = { id: role.id, name: role.name };
  }
  return handles;
}

async function resolveClientHandles(kc) {
  // Only resolve the clients actually referenced in user-roles.json (client column).
  const clientIds = [...new Set(userRoles.filter(r => !r.realm_role).map(r => r.client))];
  const handles = {};
  for (const clientId of clientIds) {
    const matches = await kc.clients.find({ clientId, realm: OPS_REALM });
    if (!matches.length) {
      console.warn(`  ! client '${clientId}' not found in realm — its role mappings will be skipped`);
      continue;
    }
    handles[clientId] = { uniqueId: matches[0].id };
    handles[clientId].roles = {};
    const names = [...new Set(userRoles
      .filter(r => !r.realm_role && r.client === clientId)
      .map(r => r.role_name))];
    for (const roleName of names) {
      const role = await kc.clients.findRole({
        id: matches[0].id, roleName, realm: OPS_REALM,
      });
      if (!role) {
        console.warn(`  ! client role '${clientId}.${roleName}' not found — assignment will be skipped`);
        continue;
      }
      handles[clientId].roles[roleName] = { id: role.id, name: role.name };
    }
  }
  return handles;
}

async function backfillUser(kc, casUserId, casUsername, realmIdx, clientIdx, realmHandles, clientHandles, stats) {
  // Keycloak usernames are effectively case-insensitive (only one of
  // orlando/Orlando/ORLANDO survives realm seeding), but the admin API's
  // exact=true search is case-sensitive. Use the substring search and filter
  // for case-insensitive equality so all case-variants in the source map back
  // to the single surviving Keycloak user.
  const candidates = await kc.users.find({ username: casUsername, realm: OPS_REALM, max: 50 });
  const match = candidates.find(u => u.username && u.username.toLowerCase() === casUsername.toLowerCase());
  if (!match) {
    stats.usersNotFound.push(casUsername);
    return;
  }
  const kcUserId = match.id;
  stats.usersMatched++;

  // ---- Realm roles ----
  const desiredRealm = realmIdx.get(casUserId) || [];
  if (desiredRealm.length) {
    const current = await kc.users.listRealmRoleMappings({ id: kcUserId, realm: OPS_REALM });
    const currentNames = new Set(current.map(r => r.name));
    const missing = desiredRealm
      .filter(r => !currentNames.has(r.role_name))
      .map(r => realmHandles[r.role_name])
      .filter(Boolean);
    if (missing.length) {
      await kc.users.addRealmRoleMappings({ id: kcUserId, realm: OPS_REALM, roles: missing });
      stats.realmRoleAssignmentsAdded += missing.length;
    }
    stats.realmRoleAssignmentsAlreadyPresent += desiredRealm.length - missing.length;
  }

  // ---- Client roles ----
  const desiredClient = clientIdx.get(casUserId) || [];
  // group by client
  const byClient = desiredClient.reduce((acc, r) => {
    (acc[r.client] = acc[r.client] || []).push(r.role_name);
    return acc;
  }, {});
  for (const clientId of Object.keys(byClient)) {
    const handle = clientHandles[clientId];
    if (!handle) continue;
    const current = await kc.users.listClientRoleMappings({
      id: kcUserId, clientUniqueId: handle.uniqueId, realm: OPS_REALM,
    });
    const currentNames = new Set(current.map(r => r.name));
    const missing = byClient[clientId]
      .filter(n => !currentNames.has(n))
      .map(n => handle.roles[n])
      .filter(Boolean);
    if (missing.length) {
      await kc.users.addClientRoleMappings({
        id: kcUserId, clientUniqueId: handle.uniqueId, realm: OPS_REALM, roles: missing,
      });
      stats.clientRoleAssignmentsAdded += missing.length;
    }
    stats.clientRoleAssignmentsAlreadyPresent += byClient[clientId].length - missing.length;
  }
}

async function main() {
  for (const v of ['AUTH_URL', 'AUTH_REALM_NAME', 'AUTH_ADMIN_USERNAME', 'AUTH_ADMIN_PASSWORD', 'AUTH_ADMIN_CLIENT']) {
    if (!process.env[v]) {
      console.error(`Missing required env var: ${v}`);
      process.exit(2);
    }
  }

  console.log(`Target: ${process.env.AUTH_URL} realm=${OPS_REALM}`);
  console.log(`Inputs: ${users.length} users, ${userRoles.length} role mappings`);

  const kc = new KcAdminClient({ baseUrl: process.env.AUTH_URL, realmName: OPS_REALM });
  await kc.auth({
    username: process.env.AUTH_ADMIN_USERNAME,
    password: process.env.AUTH_ADMIN_PASSWORD,
    clientId: process.env.AUTH_ADMIN_CLIENT,
    grantType: 'password',
  });

  console.log('\n== Step 1: ensure realm roles exist ==');
  const roleSummary = await ensureRealmRoles(kc);
  console.log(`  ${roleSummary.created.length}/${roleSummary.total} created: ${roleSummary.created.join(', ') || '(none — realm already had every role)'}`);

  console.log('\n== Step 2: resolve role + client handles ==');
  const realmHandles = await resolveRealmRoleHandles(kc);
  const clientHandles = await resolveClientHandles(kc);
  console.log(`  ${Object.keys(realmHandles).length} realm roles, ${Object.keys(clientHandles).length} clients resolved`);

  console.log('\n== Step 3: backfill role mappings per user ==');
  const { realm: realmIdx, client: clientIdx } = indexUserRolesByCasId();
  const stats = {
    usersMatched: 0,
    usersNotFound: [],
    realmRoleAssignmentsAdded: 0,
    realmRoleAssignmentsAlreadyPresent: 0,
    clientRoleAssignmentsAdded: 0,
    clientRoleAssignmentsAlreadyPresent: 0,
    failures: [],
  };

  let processed = 0;
  for (const user of users) {
    try {
      await backfillUser(
        kc, user.attribute_cas_user_id, user.username,
        realmIdx, clientIdx, realmHandles, clientHandles, stats,
      );
    } catch (err) {
      stats.failures.push({ username: user.username, error: err?.response?.data?.errorMessage || err.message });
    }
    processed++;
    if (processed % 100 === 0) {
      console.log(`  …${processed}/${users.length} users processed`);
    }
  }

  console.log('\n== Summary ==');
  console.log(`  Realm roles created:                  ${roleSummary.created.length}`);
  console.log(`  Users matched in target realm:        ${stats.usersMatched}`);
  console.log(`  Users not present in target realm:    ${stats.usersNotFound.length}`);
  console.log(`  Realm-role assignments added:         ${stats.realmRoleAssignmentsAdded}`);
  console.log(`  Realm-role assignments already there: ${stats.realmRoleAssignmentsAlreadyPresent}`);
  console.log(`  Client-role assignments added:        ${stats.clientRoleAssignmentsAdded}`);
  console.log(`  Client-role assignments already there:${stats.clientRoleAssignmentsAlreadyPresent}`);
  console.log(`  Failures:                             ${stats.failures.length}`);
  if (stats.usersNotFound.length) {
    console.log(`\n  Missing users (first 20): ${stats.usersNotFound.slice(0, 20).join(', ')}${stats.usersNotFound.length > 20 ? ` …(+${stats.usersNotFound.length - 20})` : ''}`);
  }
  if (stats.failures.length) {
    console.log(`\n  Failure samples:`);
    for (const f of stats.failures.slice(0, 10)) console.log(`    ${f.username}: ${f.error}`);
  }
  // Exit non-zero only on outright failures, not on "users not found" (those
  // are valid — that user may not be in the target realm yet by design).
  process.exit(stats.failures.length ? 1 : 0);
}

main().catch(err => {
  console.error('Backfill aborted:', err?.response?.data || err);
  process.exit(1);
});
