/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

const passport = require('passport');
const OpenIDConnectStrategy = require('passport-openidconnect');
const db = require('./database');

passport.use(new OpenIDConnectStrategy({
    issuer: process.env.OIDC_BASE_URI,
    authorizationURL: process.env.OIDC_AUTH_URI,
    tokenURL: process.env.OIDC_TOKEN_URI,
    userInfoURL: process.env.OIDC_USER_URI,
    clientID: process.env.OIDC_CLIENT_ID,
    clientSecret: process.env.OIDC_CLIENT_SECRET,
    callbackURL: `${process.env.APP_BASE_URL}/oauth/callback`,
    scope: process.env.OIDC_SCOPES || 'openid profile'
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