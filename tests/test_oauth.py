#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import urlparse

import tests.util

class OAuthTest(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"
  domain = "sample"

  def test_oauth(self):
    response = self.app.get("/oauth/google", status=302)
    assert response.location.startswith("https://accounts.google.com/o/oauth2/auth?")
    state = urlparse.parse_qs(response.location)["state"][0]
    self.app.get("/oauth/google/callback?state={0}".format(state), status=500)
    self.expected_logs = [('ERROR', 'lib/webapp2-2.5.2/webapp2.py', '_internal_error', "'access_token'")]

class OAuthSecretsTest(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def test_secrets(self):
    self.app.get("/oauth/google", status=500)
    self.expected_logs = [
      ('WARNING', 'gae/utils.py', '_get_consumer_info_for', "import_string() failed for 'oauth_secrets.localhost'. Possible ...found in '/Users/endoh/Documents/works/gogom/gae/oauth_secrets/__init__.pyc'.\n- 'oauth_secrets.localhost' not found."),
      ('ERROR', 'lib/webapp2-2.5.2/webapp2.py', '_internal_error', 'cannot import name default'),
    ]
