const KeycloakAdminClient = require('keycloak-admin').default;
const cliProgress = require('cli-progress');
const users = require('./users');
const usersMemberships = require('./user-memberships.json');
const usersRoles = require('./user-roles.json');
const institutions = require('./institutions');
const units = require('./units');
require('dotenv').config()

const attrPrefix = 'attribute_';
const progressBar = new cliProgress.SingleBar({}, cliProgress.Presets.shades_classic);
let importedSuccessfully = 0;
let importFailed = 0;

const authClient = new KeycloakAdminClient({
  baseUrl: process.env.AUTH_URL,
  realmName: process.env.AUTH_REALM_NAME,
});

// If KC rejects a username as a duplicate (case-insensitive collision between
// two DISTINCT CAS accounts that share a username), retry once with the email
// as the username so the "loser" is not dropped. Mirrors the cuba.live LIVE
// convention where collision users are keyed by email; they then sign in by
// email (loginWithEmailAllowed). The retried user still flows through the
// normal .then() role/group assignment below.
async function createUserWithUsernameFallback(client, newUser) {
  try {
    return await client.users.create(newUser);
  } catch (error) {
    const msg = error?.response?.data?.errorMessage || '';
    if (error?.response?.status === 409 && /username/i.test(msg)
        && newUser.email && newUser.email !== newUser.username) {
      console.log();
      console.log(`Username "${newUser.username}" collided; retrying with email "${newUser.email}" as username.`);
      return await client.users.create({ ...newUser, username: newUser.email });
    }
    throw error;
  }
}

const startMigration = async () => {
  progressBar.start(users.length + units.length + institutions.length, 0);
  let attributes = {};
  let clientRoles = {};
  let clients = {};
  const authenticationFailed = await authClient.auth({
    username: process.env.AUTH_ADMIN_USERNAME,
    password: process.env.AUTH_ADMIN_PASSWORD,
    clientId: process.env.AUTH_ADMIN_CLIENT,
    // only needed if your admin client is set to confidential
    // clientSecret: process.env.AUTH_ADMIN_SECRET,
    grantType: 'password',
  }).catch(error => {
    console.log(error?.response?.data?.error_description);
    importFailed = users.length;
    progressBar.update(importFailed);
    return true;
  });

  if (authenticationFailed) return Promise.reject();

  const realmRoles = {};
  for (const role_name of [...new Set(usersRoles.filter(role => role.realm_role).map(role => role.role_name))]) {
    realmRoles[role_name] = await authClient.roles.findOneByName({
      name: role_name,
      realm: process.env.AUTH_REALM_NAME
    });
  }

  const keycloakClients = await authClient.clients.find({ realm: process.env.AUTH_REALM_NAME });
  keycloakClients.forEach(client => {
    clients[client.clientId] = client.id;
  })

  usersRoles.filter(role => !role.realm_role).forEach(member => {
    if (!clientRoles.hasOwnProperty(member.client)) clientRoles[member.client] = {};
    clientRoles[member.client][member.role_name] = null;
  });

  for (const client of Object.keys(clientRoles)) {
    for (const role of Object.keys(clientRoles[client])) {
      clientRoles[client][role] = await authClient.clients.findRole({
        roleName: role,
        id: clients[client],
        realm: process.env.AUTH_REALM_NAME
      });
    }
  }

  for (let group of institutions) {
    attributes = {};
    Object.keys(group).filter(key => key.startsWith(attrPrefix)).forEach(key => {
      attributes[key.substring(attrPrefix.length)] = [group[key]];
    });

    const newGroup = {
      name: group.name,
      path: '/institutions/' + group.name,
      attributes: attributes,
    };

    await authClient.groups.setOrCreateChild({
      id: process.env.INSTITUTION_GROUP_ID,
      realm: process.env.AUTH_REALM_NAME
    }, newGroup).then(async (result) => {
      importedSuccessfully++;
      group.keycloak_group_id = result.id;
      group.path = newGroup.path;

      for (let unit of units.filter((unit) => unit.attribute_partc_institution_id === group.attribute_partc_institution_id)) {
        attributes = {};
        Object.keys(unit).filter(key => key.startsWith(attrPrefix)).forEach(key => {
          attributes[key.substring(attrPrefix.length)] = [unit[key]];
        });
        const newSubgroup = {
          name: unit.name,
          path: '/institutions/' + group.name + '/' + unit.name,
          attributes: attributes,
        };
        await authClient.groups.setOrCreateChild({
          id: group.keycloak_group_id,
          realm: process.env.AUTH_REALM_NAME
        }, newSubgroup).then((result) => {
          unit.keycloak_group_id = result.id;
          unit.path = newSubgroup.path;
          importedSuccessfully++;
        }).catch(error => {
          importFailed++;
          console.log();
          console.log(`Failed to create unit ${unit.name}.`, error?.response?.data?.errorMessage)
        }).finally(() => {
          progressBar.update(importFailed + importedSuccessfully);
        })
      }
    }).catch(error => {
      importFailed++;
      console.log();
      console.log(`Failed to create institution ${group.name}.`, error?.response?.data?.errorMessage)
    }).finally(() => {
      progressBar.update(importFailed + importedSuccessfully);
    });
  }

  for (let user of users) {
    attributes = {};
    const userClientRoles = {};
    Object.keys(user).filter(key => key.startsWith(attrPrefix)).forEach(key => {
      attributes[key.substring(attrPrefix.length)] = [user[key]];
    });

    usersRoles.filter(ur => !ur.realm_role && ur.attribute_cas_user_id === user.attribute_cas_user_id).forEach(ur => {
      if (!userClientRoles[ur.client]) userClientRoles[ur.client] = [];
      userClientRoles[ur.client].push(ur.role_name);
    });

    const newUser = {
      realm: process.env.AUTH_REALM_NAME,
      credentials: [
        {
          algorithm: 'bcrypt',
          hashedSaltedValue: user.password, // the bcrypt-hashed password
          hashIterations: 10,
          type: 'password',
        },
      ],
      email: user.primary_email,
      emailVerified: user.email_validated,
      username: user.username,
      lastName: user.name,
      firstName: user.first_name,
      attributes: attributes,
      groups: usersMemberships.filter(um => um.attribute_cas_user_id === user.attribute_cas_user_id)
          .map(um => {
            if (um.institution_id) {
              return institutions.find(i => i.attribute_partc_institution_id === um.institution_id)?.path;
            }
            return units.find(i => i.attribute_partc_institution_unit_id === um.institution_unit_id)?.path;
          })
          .filter(Boolean), // drop unresolvable (orphan) memberships — a stale partc membership
                            // whose institution/unit isn't in the migrated set resolves to undefined,
                            // serializes as null, and makes KC NPE → HTTP 500 on user create.
      enabled: true,
    };
    await createUserWithUsernameFallback(authClient, newUser)
        .then(async (result) => {
          await authClient.users.addRealmRoleMappings({
            id: result.id,
            realm: process.env.AUTH_REALM_NAME,
            roles: usersRoles.filter(ur => ur.realm_role && ur.attribute_cas_user_id === user.attribute_cas_user_id)
                .map(um => {
                  return { id: realmRoles[um.role_name].id, name: realmRoles[um.role_name].name };
                })
          })
          for (const client of Object.keys(userClientRoles)) {
            await authClient.users.addClientRoleMappings({
              id: result.id,
              clientUniqueId: clients[client],
              realm: process.env.AUTH_REALM_NAME,
              roles: userClientRoles[client].map(roleName => {
                    return { id: clientRoles[client][roleName].id, name: clientRoles[client][roleName].name };
                  })
            })
          }
          importedSuccessfully++;
        })
        .catch(error => {
          importFailed++;
          console.log();
          // Surface the real reason. `errorMessage` is only populated for KC's
          // structured 4xx bodies (e.g. the 409 username collision); for any
          // other failure it is undefined, which previously printed a bare
          // "Failed to create user X. undefined" and hid the actual cause.
          const reason = error?.response?.data?.errorMessage
            || error?.response?.data?.error
            || error?.message
            || `HTTP ${error?.response?.status ?? '?'}`;
          console.log(`Failed to create user ${user.username} (cas_user_id ${user.attribute_cas_user_id}).`, reason);
        }).finally(() => {
          progressBar.update(importFailed + importedSuccessfully);
        });
  }
};

startMigration()
    .catch(() => console.log('Authentication failed'))
    .finally(() => {
      progressBar.stop();
      console.log();
      console.log('Migration process complete.');
      console.log(`${importedSuccessfully} records successfully migrated`)
      console.log(`${importFailed} records import failed`)
    })
