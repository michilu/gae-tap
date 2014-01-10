#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import tests.util
import tap

from google.appengine.ext import ndb
from google.appengine.runtime import apiproxy_errors
import webapp2

import conf

class BugTest(tests.util.TestCase):
  root_path = conf.root_path

  def test_cache(self):

    class App(tap.RequestHandler):
      @tap.cache(10)
      def get(self):
        self.tasklet()

      @ndb.tasklet
      def tasklet(self):
        raise apiproxy_errors.OverQuotaError

    self.app = tests.util.gen_test_app(App,
      routes=[webapp2.Route("/_tap/i18n/<domain>.<language>.js", "tap.I18Njs", name="I18Njs")],
    )
    self.app.get("/", status=500)
    self.expected_logs = [
      ('WARNING', 'google/appengine/ext/ndb/tasklets.py', '_help_tasklet_along', 'suspended generator inner(__init__.py:...) raised OverQuotaError()'),
    ]

  def test_cache_period(self):

    class App(tap.RequestHandler):
      @tap.cache()
      def get(self):
        pass

    self.app = tests.util.gen_test_app(App)
    self.app.get("/")
