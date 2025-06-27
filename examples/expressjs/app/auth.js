/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

const passport = require('passport');
const OpenIDConnectStrategy = require('passport-openidconnect');
const db = require('./database');

passport.use(new OpenIDConnectStrategy({
    issuer: process.env.OIDC_ISSUER,
    authorizationURL: process.env.OIDC_AUTHORIZATION_URL,
    tokenURL: process.env.OIDC_TOKEN_URL,
    userInfoURL: process.env.OIDC_USERINFO_URL,
    clientID: process.env.OIDC_CLIENT_ID,
    clientSecret: process.env.OIDC_CLIENT_SECRET,
    callbackURL: process.env.OIDC_CALLBACK_URL,
    scope: 'openid profile'
  },
  function verify(issuer, profile, cb) {
    db.oneOrNone('SELECT * FROM users WHERE name = $1', [profile.displayName])
      .then(user => {
        if (user) {
          return cb(null, user);
        }
        return db.one('INSERT INTO users(name, password) VALUES($1, $2) RETURNING *', [profile.displayName, ''])
          .then(newUser => {
            return cb(null, newUser);
          });
      })
      .catch(err => {
        return cb(err);
      });
  }
));

passport.serializeUser(function(user, cb) {
  process.nextTick(function() {
    cb(null, { id: user.id, username: user.name });
  });
});

passport.deserializeUser(function(user, cb) {
  process.nextTick(function() {
    return cb(null, user);
  });
});

module.exports = passport;