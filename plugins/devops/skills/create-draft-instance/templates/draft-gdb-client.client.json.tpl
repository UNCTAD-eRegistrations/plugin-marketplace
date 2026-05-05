{
  "clientId": "draft-gdb-client",
  "baseUrl": "https://gdb.${DRAFT_DOMAIN}/",
  "surrogateAuthRequired": false,
  "enabled": true,
  "alwaysDisplayInConsole": false,
  "clientAuthenticatorType": "client-secret",
  "redirectUris": [
    "https://gdb.${DRAFT_DOMAIN}/*"
  ],
  "webOrigins": [
    "+"
  ],
  "notBefore": 0,
  "bearerOnly": false,
  "consentRequired": false,
  "standardFlowEnabled": true,
  "implicitFlowEnabled": false,
  "directAccessGrantsEnabled": false,
  "serviceAccountsEnabled": true,
  "publicClient": false,
  "frontchannelLogout": false,
  "protocol": "openid-connect",
  "attributes": {
    "saml.assertion.signature": "false",
    "id.token.as.detached.signature": "false",
    "saml.multivalued.roles": "false",
    "saml.force.post.binding": "false",
    "saml.encrypt": "false",
    "post.logout.redirect.uris": "+",
    "oauth2.device.authorization.grant.enabled": "false",
    "backchannel.logout.revoke.offline.tokens": "false",
    "saml.server.signature": "false",
    "saml.server.signature.keyinfo.ext": "false",
    "use.refresh.tokens": "true",
    "exclude.session.state.from.auth.response": "false",
    "realm_client": "false",
    "oidc.ciba.grant.enabled": "false",
    "saml.artifact.binding": "false",
    "backchannel.logout.session.required": "true",
    "client_credentials.use_refresh_token": "false",
    "saml_force_name_id_format": "false",
    "saml.client.signature": "false",
    "tls.client.certificate.bound.access.tokens": "false",
    "require.pushed.authorization.requests": "false",
    "saml.authnstatement": "false",
    "display.on.consent.screen": "false",
    "saml.onetimeuse.condition": "false"
  },
  "authenticationFlowBindingOverrides": {},
  "fullScopeAllowed": true,
  "nodeReRegistrationTimeout": -1,
  "protocolMappers": [
    {
      "name": "Client Host",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-usersessionmodel-note-mapper",
      "consentRequired": false,
      "config": {
        "user.session.note": "clientHost",
        "id.token.claim": "true",
        "access.token.claim": "true",
        "claim.name": "clientHost",
        "jsonType.label": "String",
        "userinfo.token.claim": "true"
      }
    },
    {
      "name": "Client IP Address",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-usersessionmodel-note-mapper",
      "consentRequired": false,
      "config": {
        "user.session.note": "clientAddress",
        "id.token.claim": "true",
        "access.token.claim": "true",
        "claim.name": "clientAddress",
        "jsonType.label": "String",
        "userinfo.token.claim": "true"
      }
    },
    {
      "name": "Client ID",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-usersessionmodel-note-mapper",
      "consentRequired": false,
      "config": {
        "user.session.note": "clientId",
        "id.token.claim": "true",
        "access.token.claim": "true",
        "claim.name": "clientId",
        "jsonType.label": "String",
        "userinfo.token.claim": "true"
      }
    }
  ],
  "defaultClientScopes": [
    "web-origins",
    "acr",
    "profile",
    "roles",
    "basic",
    "email"
  ],
  "optionalClientScopes": [
    "address",
    "phone",
    "offline_access",
    "microprofile-jwt"
  ]
}
