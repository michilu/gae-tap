#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from random import random
import os

import tests.util
import utils

from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from google.appengine.runtime import apiproxy_errors

class CacheTest(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def test_cache(self):

    class App(utils.RequestHandler):
      @utils.cache(60)
      def get(self):
        self.response.write(random())

    self.app = tests.util.gen_test_app(App)

    queue_name = "cache"
    queue = taskqueue.Queue(queue_name)
    assert queue.fetch_statistics().tasks == 0

    response = self.app.get("/")
    assert queue.fetch_statistics().tasks == 1
    cache = queue.lease_tasks(0, 1)[0]

    assert self.app.get("/").body == response.body
    assert queue.fetch_statistics().tasks == 1
    assert int(queue.lease_tasks(0, 1)[0].name[:10]) - int(cache.name[:10]) in (0, 1)

  def test_period(self):

    class App(utils.RequestHandler):
      @utils.cache(1)
      def get(self):
        self.response.write(random())

    self.app = tests.util.gen_test_app(App)
    response = self.app.get("/")
    assert self.app.get("/").body == response.body

  def test_period_zero(self):

    class App(utils.RequestHandler):
      @utils.cache(0)
      def get(self):
        self.response.write(random())

    self.app = tests.util.gen_test_app(App)
    response = self.app.get("/")
    assert self.app.get("/").body != response.body

  def test_period_minus(self):

    class App(utils.RequestHandler):
      @utils.cache(-1)
      def get(self):
        self.response.write(random())

    self.app = tests.util.gen_test_app(App)
    response = self.app.get("/")
    assert self.app.get("/").body != response.body

  def test_period_none(self):

    class App(utils.RequestHandler):
      @utils.cache()
      def get(self):
        self.response.write(random())

    self.app = tests.util.gen_test_app(App)
    response = self.app.get("/")
    assert self.app.get("/").body != response.body

  def test_expire(self):

    class App(utils.RequestHandler):
      @utils.cache(60, expire=datetime(2100, 1, 1))
      def get(self):
        self.response.write(random())

    self.app = tests.util.gen_test_app(App)
    response = self.app.get("/")
    assert self.app.get("/").body == response.body

  def test_expired(self):

    class App(utils.RequestHandler):
      @utils.cache(60, expire=datetime(2000, 1, 1))
      def get(self):
        self.response.write(random())

    self.app = tests.util.gen_test_app(App)
    response = self.app.get("/")
    assert self.app.get("/").body != response.body

  def test_empty(self):

    class App(utils.RequestHandler):
      @utils.cache(60)
      def get(self):
        pass

    self.app = tests.util.gen_test_app(App)
    response = self.app.get("/")

    queue_name = "cache"
    queue = taskqueue.Queue(queue_name)
    assert queue.fetch_statistics().tasks == 0

  def test_empty_true(self):

    class App(utils.RequestHandler):
      @utils.cache(60, empty=True)
      def get(self):
        pass

    self.app = tests.util.gen_test_app(App)
    response = self.app.get("/")

    queue_name = "cache"
    queue = taskqueue.Queue(queue_name)
    assert queue.fetch_statistics().tasks == 1
