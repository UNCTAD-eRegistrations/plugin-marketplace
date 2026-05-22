// Wrapper that lets the cas-to-keycloak tool authenticate as the *master*
// realm admin (admin/admin) while running its operations against the *CU*
// realm. The tool itself always uses a single realmName for both auth and
// ops, so we monkey-patch KcAdminClient.auth: swap to master for the token
// request, then swap back to the constructor-supplied realm for every op.
//
// Also: before delegating to migrate.js, ensure every realm role referenced
// in user-roles.json exists in the CU realm. migrate.js calls
// roles.findOneByName for each distinct realm-role name and then dereferences
// the result without a null check, so any name the realm doesn't already know
// (e.g. Cuba-specific admin roles like VUCE/FITO/RCP/...) would crash the run
// or silently drop the assignment. Pre-creating them here keeps the upstream
// tool unmodified and makes the pipeline self-healing for future custom roles
// added to partc.role.
//
// Required env vars are read by migrate.js directly via dotenv/process.env:
//   AUTH_URL, AUTH_REALM_NAME (= CU), AUTH_ADMIN_USERNAME, AUTH_ADMIN_PASSWORD,
//   AUTH_ADMIN_CLIENT, INSTITUTION_GROUP_ID

const KcAdminClient = require('keycloak-admin').default;
const origAuth = KcAdminClient.prototype.auth;

KcAdminClient.prototype.auth = async function (credentials) {
  const opsRealm = this.realmName;
  this.setConfig({ realmName: 'master' });
  try {
    const result = await origAuth.call(this, credentials);
    return result;
  } finally {
    this.setConfig({ realmName: opsRealm });
  }
};

async function ensureRealmRoles() {
  require('dotenv').config();
  const userRoles = require('./user-roles.json');
  const realm = process.env.AUTH_REALM_NAME;

  const names = [...new Set(userRoles.filter(r => r.realm_role).map(r => r.role_name))];
  if (names.length === 0) return;

  const kc = new KcAdminClient({ baseUrl: process.env.AUTH_URL, realmName: realm });
  await kc.auth({
    username: process.env.AUTH_ADMIN_USERNAME,
    password: process.env.AUTH_ADMIN_PASSWORD,
    clientId: process.env.AUTH_ADMIN_CLIENT,
    grantType: 'password',
  });

  const created = [];
  for (const name of names) {
    const existing = await kc.roles.findOneByName({ name, realm });
    if (existing) continue;
    await kc.roles.create({ name, realm });
    created.push(name);
  }
  if (created.length) {
    console.log(`Pre-created ${created.length} missing realm role(s): ${created.join(', ')}`);
  }
}

ensureRealmRoles()
  .then(() => require('./migrate.js'))
  .catch(err => {
    console.error('Realm-role pre-flight failed:', err?.response?.data || err);
    process.exit(1);
  });
