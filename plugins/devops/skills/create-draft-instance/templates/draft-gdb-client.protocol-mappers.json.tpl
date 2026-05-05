[
  {
    "name": "Client Host",
    "protocol": "openid-connect",
    "protocolMapper": "oidc-usersessionmodel-note-mapper",
    "consentRequired": false,
    "config": {
      "user.session.note": "clientHost",
      "introspection.token.claim": "true",
      "userinfo.token.claim": "true",
      "id.token.claim": "true",
      "access.token.claim": "true",
      "claim.name": "clientHost",
      "jsonType.label": "String"
    }
  },
  {
    "name": "Client IP Address",
    "protocol": "openid-connect",
    "protocolMapper": "oidc-usersessionmodel-note-mapper",
    "consentRequired": false,
    "config": {
      "user.session.note": "clientAddress",
      "introspection.token.claim": "true",
      "userinfo.token.claim": "true",
      "id.token.claim": "true",
      "access.token.claim": "true",
      "claim.name": "clientAddress",
      "jsonType.label": "String"
    }
  },
  {
    "name": "Client ID",
    "protocol": "openid-connect",
    "protocolMapper": "oidc-usersessionmodel-note-mapper",
    "consentRequired": false,
    "config": {
      "user.session.note": "clientId",
      "introspection.token.claim": "true",
      "userinfo.token.claim": "true",
      "id.token.claim": "true",
      "access.token.claim": "true",
      "claim.name": "clientId",
      "jsonType.label": "String"
    }
  }
]
