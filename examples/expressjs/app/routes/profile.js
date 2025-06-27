/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

var express = require('express');
var router = express.Router();

function ensureLoggedIn(req, res, next) {
  if (req.isAuthenticated()) {
    return next();
  }
  res.redirect('/login');
}

/* GET user profile. */
router.get('/', ensureLoggedIn, function(req, res, next) {
  res.render('profile', { user: req.user });
});

module.exports = router;