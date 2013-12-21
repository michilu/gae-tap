#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import tests.util
import utils

from google.appengine.ext import ndb
from google.appengine.runtime import apiproxy_errors

class BugTest(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def test_cache(self):

    class App(utils.RequestHandler):
      @utils.cache(10)
      def get(self):
        self.tasklet()

      @ndb.tasklet
      def tasklet(self):
        raise apiproxy_errors.OverQuotaError

    self.app = tests.util.gen_test_app(App)
    self.app.get("/", status=500)
    self.expected_logs = [
      ('WARNING', 'google/appengine/ext/ndb/tasklets.py', '_help_tasklet_along', 'initial generator get(test_bugs.py:...) raised OverQuotaError()'),
      ('WARNING', 'google/appengine/ext/ndb/tasklets.py', '_help_tasklet_along', 'suspended generator inner(utils.py:...) raised OverQuotaError()'),
      ('ERROR', 'lib/webapp2-2.5.2/webapp2.py', '_internal_error', 'error.html'),
    ]

  def test_cache_period(self):

    class App(utils.RequestHandler):
      @utils.cache()
      def get(self):
        pass

    self.app = tests.util.gen_test_app(App)
    self.app.get("/")
