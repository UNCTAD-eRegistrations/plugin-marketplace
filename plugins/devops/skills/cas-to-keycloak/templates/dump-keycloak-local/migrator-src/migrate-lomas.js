// Imports users exported from the legacy eRegistrations v2 (mano) platform of
// Lomas de Zamora (elomas.gob.ar) into a Keycloak realm. LOM-21.
//
// Unlike migrate.js (CAS source), the v2 password scheme bcrypt(sha256(email+password))
// cannot be verified by Keycloak, so users are created WITHOUT credentials and set a
// new password through the "Forgot password" flow at first login.
//
// Inputs (either or both):
//   --csv <path>   users-list.csv from server/scripts/generate-users-list.js
//                  (Email;First Name;Last Name;Date Created;Submitted Count, date d/m/yyyy)
//   --json <path>  enriched export from server/scripts/generate-users-migration-export.js
//                  [{ userId, email, firstName, lastName, roles, institution,
//                     identificationNumber, phone, createdAt, submittedCount }]
//                  Rows sharing an email across the two files are merged (JSON wins)
//                  when they describe the same person (same names).
// Options:
//   --dry-run                 parse + validate + write reports only, no Keycloak calls
//   --out-dir <path>          report directory (default ./out)
//   --env-file <path>         credentials file (default ./.env.lomas): AUTH_URL, AUTH_REALM_NAME,
//                             AUTH_ADMIN_CLIENT + AUTH_ADMIN_SECRET (client_credentials) or
//                             AUTH_ADMIN_USERNAME + AUTH_ADMIN_PASSWORD (password grant)
//   --dup-policy <mode>       what to do when one email is shared by rows with DIFFERENT
//                             names (distinct people — the realm allows one account per
//                             email): exclude (default; none imported, all listed as
//                             conflict-email for manual resolution) | oldest | newest
//                             (keep the account created first/last, list the rest).
//                             Rows with the same email AND same names are one person
//                             exported twice and are always deduplicated silently.
//
// Reports written to out-dir:
//   results-<timestamp>.csv         email;status;detail;kcUserId
//   officials-mapping-sheet.csv     officials found in the JSON export, with blank
//                                   KC role/group columns to fill for manual assignment

const KeycloakAdminClient = require('keycloak-admin').default;
const cliProgress = require('cli-progress');
const fs = require('fs');
const path = require('path');

const REAUTH_INTERVAL_MS = 4 * 60 * 1000; // re-login before the 5-minute default token expiry
const EMAIL_RE = /^[^\s@;]+@[^\s@;]+\.[^\s@;]+$/;
const CSV_HEADER = 'Email;First Name;Last Name;Date Created;Submitted Count';
const DUP_POLICIES = ['exclude', 'oldest', 'newest'];

const args = process.argv.slice(2);
const getArg = (name) => {
  const i = args.indexOf(name);
  return i !== -1 ? args[i + 1] : null;
};
const csvPath = getArg('--csv');
const jsonPath = getArg('--json');
const dryRun = args.includes('--dry-run');
const outDir = getArg('--out-dir') || path.join(__dirname, 'out');
const dupPolicy = getArg('--dup-policy') || 'exclude';
// Credentials file (gitignored) wins over the tracked .env — keeps real secrets out of git.
// --env-file lets a rehearsal realm use its own file (e.g. .env.lomas.test).
const envFile = getArg('--env-file') || path.join(__dirname, '.env.lomas');
require('dotenv').config({ path: envFile });
require('dotenv').config();

if ((!csvPath && !jsonPath) || !DUP_POLICIES.includes(dupPolicy)) {
  console.error('Usage: node migrate-lomas.js [--csv <users-list.csv>] [--json <migration-export.json>]'
    + ' [--dry-run] [--out-dir <dir>] [--dup-policy exclude|oldest|newest] [--env-file <path>]');
  process.exit(1);
}

const results = []; // { email, status, detail, kcUserId }
const record = (email, status, detail, kcUserId) =>
  results.push({ email: email || '', status, detail: detail || '', kcUserId: kcUserId || '' });

// v2 CSV dates are d/m/yyyy (Argentina); JSON carries ISO strings. Returns a Date or null.
const parseCreated = (value) => {
  if (!value) return null;
  const dmy = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(String(value).trim());
  const date = dmy ? new Date(Date.UTC(+dmy[3], +dmy[2] - 1, +dmy[1])) : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
};
const isoDate = (value) => {
  const date = parseCreated(value);
  if (!date) return value ? String(value) : undefined;
  return /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(String(value).trim()) ? date.toISOString().slice(0, 10) : date.toISOString();
};
// Same person if names match ignoring case, accents and spacing ("María Pérez" == "maria perez").
const nameKey = (user) => `${user.firstName}|${user.lastName}`.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .toLowerCase().replace(/\s+/g, ' ').trim();
const describe = (user) => `${user.firstName} ${user.lastName} (created ${user.createdAt || '?'})`.trim();

const readCsvUsers = (file) => {
  const users = [];
  const raw = fs.readFileSync(file, 'utf8').replace(/^﻿/, '');
  const lines = raw.split(/\r?\n/).filter((line) => line.trim() !== '');
  if (lines[0].trim() !== CSV_HEADER) {
    console.error(`Unexpected CSV header in ${file}:\n  got      "${lines[0].trim()}"\n  expected "${CSV_HEADER}"`);
    process.exit(1);
  }
  lines.slice(1).forEach((line, idx) => {
    const cols = line.split(';');
    if (cols.length !== 5) {
      record(line, 'invalid', `line ${idx + 2}: expected 5 columns, got ${cols.length} (semicolon inside a field?)`);
      return;
    }
    users.push({
      email: cols[0].trim(),
      firstName: cols[1].trim(),
      lastName: cols[2].trim(),
      createdAt: cols[3].trim(),
      submittedCount: cols[4].trim(),
    });
  });
  return users;
};

const readJsonUsers = (file) => {
  const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (!Array.isArray(parsed)) {
    console.error(`${file} must contain a JSON array`);
    process.exit(1);
  }
  return parsed.map((user) => ({
    email: (user.email || '').trim(),
    firstName: (user.firstName || '').trim(),
    lastName: (user.lastName || '').trim(),
    createdAt: user.createdAt,
    submittedCount: user.submittedCount,
    userId: user.userId,
    roles: Array.isArray(user.roles) ? user.roles : [],
    institution: user.institution,
    identificationNumber: user.identificationNumber,
    phone: user.phone,
  }));
};

// Merge rows describing the same person: later rows (JSON after CSV) overlay non-empty fields.
const mergeRows = (rows) => rows.reduce((merged, row) => {
  Object.keys(row).forEach((key) => {
    if (row[key] !== undefined && row[key] !== '' && row[key] !== null) merged[key] = row[key];
  });
  return merged;
}, {});

const resolveGroup = (rows) => {
  const distinctPeople = [...new Set(rows.map(nameKey))];
  if (distinctPeople.length === 1) {
    if (rows.length > 1) {
      rows.slice(1).forEach((row) => record(row.email, 'duplicate', `${row.source}: same person listed ${rows.length}x — merged into one account`));
    }
    return mergeRows(rows);
  }
  // Same email, different people: the realm allows one account per email.
  const summary = rows.map(describe).join(' / ');
  if (dupPolicy === 'exclude') {
    rows.forEach((row) => record(row.email, 'conflict-email',
      `${row.source}: email shared by ${distinctPeople.length} different people — none imported, resolve manually: ${summary}`));
    return null;
  }
  const byDate = rows.slice().sort((a, b) => (parseCreated(a.createdAt) || 0) - (parseCreated(b.createdAt) || 0));
  const kept = dupPolicy === 'oldest' ? byDate[0] : byDate[byDate.length - 1];
  rows.filter((row) => row !== kept).forEach((row) => record(row.email, 'duplicate',
    `${row.source}: email shared by different people — kept ${dupPolicy} account ${describe(kept)}, dropped ${describe(row)}`));
  return kept;
};

const collectUsers = () => {
  const groups = new Map();
  const add = (user, source) => {
    if (!user.email || !EMAIL_RE.test(user.email)) {
      record(user.email, 'invalid', `${source}: missing or malformed email`);
      return;
    }
    const key = user.email.toLowerCase();
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push({ ...user, source });
  };
  if (csvPath) readCsvUsers(csvPath).forEach((user) => add(user, 'csv'));
  if (jsonPath) readJsonUsers(jsonPath).forEach((user) => add(user, 'json'));
  return [...groups.values()].map(resolveGroup).filter(Boolean);
};

const toKeycloakUser = (user, realm) => {
  const attributes = { migrated_from: ['elomas-v2'] };
  if (user.userId) attributes.legacy_user_id = [String(user.userId)];
  if (user.createdAt) attributes.legacy_created_at = [isoDate(user.createdAt)];
  if (user.submittedCount !== undefined && user.submittedCount !== '') {
    attributes.legacy_submitted_count = [String(user.submittedCount)];
  }
  if (user.identificationNumber) attributes.identification_number = [String(user.identificationNumber)];
  if (user.phone) attributes.phone = [String(user.phone)];
  return {
    realm,
    username: user.email.toLowerCase(),
    email: user.email.toLowerCase(),
    firstName: user.firstName,
    lastName: user.lastName,
    emailVerified: true, // only active (confirmed) accounts are exported from v2
    enabled: true,
    attributes,
  };
};

const writeReports = (users) => {
  fs.mkdirSync(outDir, { recursive: true });

  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const resultsFile = path.join(outDir, `results-${stamp}.csv`);
  const csvEscape = (value) => String(value).replace(/;/g, ',');
  fs.writeFileSync(resultsFile, 'email;status;detail;kcUserId\n'
    + results.map((r) => [r.email, r.status, r.detail, r.kcUserId].map(csvEscape).join(';')).join('\n') + '\n');

  const officials = users.filter((user) => user.roles && user.roles.some((role) => role !== 'user'));
  let officialsFile = null;
  if (officials.length) {
    officialsFile = path.join(outDir, 'officials-mapping-sheet.csv');
    fs.writeFileSync(officialsFile, 'email;firstName;lastName;v2_roles;v2_institution;kc_realm_roles;kc_institution_group_path\n'
      + officials.map((user) => [user.email, user.firstName, user.lastName,
        user.roles.join(','), user.institution || '', '', ''].map(csvEscape).join(';')).join('\n') + '\n');
  }
  return { resultsFile, officialsFile, officialsCount: officials.length };
};

const summarize = (users, files) => {
  const counts = {};
  results.forEach((r) => { counts[r.status] = (counts[r.status] || 0) + 1; });
  console.log();
  console.log(dryRun ? 'Dry-run complete — no data written to Keycloak.' : 'Migration process complete.');
  console.log(`${users.length} unique users in input (shared-email policy: ${dupPolicy})`);
  Object.keys(counts).sort().forEach((status) => console.log(`  ${status}: ${counts[status]}`));
  console.log(`Results: ${files.resultsFile}`);
  if (files.officialsFile) {
    console.log(`Officials needing manual role/institution assignment: ${files.officialsCount} → ${files.officialsFile}`);
  }
};

const startMigration = async () => {
  const users = collectUsers();

  if (dryRun) {
    users.forEach((user) => record(user.email, 'would-create', `source: ${user.source}`));
    return users;
  }

  const authClient = new KeycloakAdminClient({
    baseUrl: process.env.AUTH_URL,
    realmName: process.env.AUTH_REALM_NAME,
  });
  // AUTH_ADMIN_SECRET set → confidential client (service account) login;
  // otherwise the classic admin username/password flow from migrate.js
  const authenticate = () => authClient.auth(process.env.AUTH_ADMIN_SECRET
    ? {
      grantType: 'client_credentials',
      clientId: process.env.AUTH_ADMIN_CLIENT,
      clientSecret: process.env.AUTH_ADMIN_SECRET,
    }
    : {
      username: process.env.AUTH_ADMIN_USERNAME,
      password: process.env.AUTH_ADMIN_PASSWORD,
      clientId: process.env.AUTH_ADMIN_CLIENT,
      grantType: 'password',
    });
  await authenticate().catch((error) => {
    console.log('Authentication failed:', error?.response?.data?.error_description || error.message);
    return Promise.reject(new Error('auth'));
  });
  let lastAuth = Date.now();

  const progressBar = new cliProgress.SingleBar({}, cliProgress.Presets.shades_classic);
  progressBar.start(users.length, 0);
  let processed = 0;

  for (const user of users) {
    if (Date.now() - lastAuth > REAUTH_INTERVAL_MS) {
      await authenticate();
      lastAuth = Date.now();
    }
    await authClient.users.create(toKeycloakUser(user, process.env.AUTH_REALM_NAME))
      .then((result) => record(user.email, 'created', '', result.id))
      .catch(async (error) => {
        if (error?.response?.status === 409) {
          const existing = await authClient.users.find({
            realm: process.env.AUTH_REALM_NAME, email: user.email.toLowerCase(), exact: true,
          }).catch(() => []);
          record(user.email, 'skipped-existing', 'already present in realm', existing[0]?.id);
        } else {
          const reason = error?.response?.data?.errorMessage
            || error?.response?.data?.error
            || error?.message
            || `HTTP ${error?.response?.status ?? '?'}`;
          record(user.email, 'failed', reason);
          console.log();
          console.log(`Failed to create user ${user.email}.`, reason);
        }
      })
      .finally(() => progressBar.update(++processed));
  }
  progressBar.stop();
  return users;
};

startMigration()
  .then((users) => summarize(users, writeReports(users)))
  .catch((error) => { if (error.message !== 'auth') throw error; });
