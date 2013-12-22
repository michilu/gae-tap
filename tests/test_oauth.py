#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import urlparse

import tests.util

from google.appengine.api import urlfetch_stub
from minimock import mock, restore

def Dummy_RetrieveURL(self, url, payload, method, headers, request, response,
                      follow_redirects, deadline, validate_certificate):
  response.set_content("{}")

class OAuthTest(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"
  domain = "sample"

  def setUp(self):
    super(OAuthTest, self).setUp()
    mock("urlfetch_stub.URLFetchServiceStub._RetrieveURL", mock_obj=Dummy_RetrieveURL)

  def tearDown(self):
    restore()
    super(OAuthTest, self).tearDown()

  def test_oauth(self):
    response = self.app.get("/oauth/google", status=302)
    assert response.location.startswith("https://accounts.google.com/o/oauth2/auth?")
    state = urlparse.parse_qs(response.location)["state"][0]
    self.app.get("/oauth/google/callback?state={0}".format(state), status=500)
    self.expected_logs = [
      ('ERROR', 'lib/webapp2-2.5.2/webapp2.py', '_internal_error', "'access_token'"),
      ('WARNING', 'google/appengine/ext/ndb/tasklets.py', '_help_tasklet_along', "suspended generator _oauth2_callback(handler.py:230) raised KeyError('access_token')"),
    ]

class OAuthSecretsTest(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def test_secrets(self):
    self.app.get("/oauth/google", status=500)
    self.expected_logs = [
      ('WARNING', 'gae/utils.py', '_get_consumer_info_for', "import_string() failed for 'oauth_config.localhost'. Possible ...found in '/Users/endoh/Documents/works/gogom/gae/oauth_config/__init__.pyc'.\n- 'oauth_config.localhost' not found."),
      ('ERROR', 'lib/webapp2-2.5.2/webapp2.py', '_internal_error', 'cannot import name default'),
    ]
