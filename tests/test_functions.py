#!/usr/bin/env python
# -*- coding: utf-8 -*-

from random import random
import cPickle as pickle
import os
import unittest

import pytest

import tests.util
import utils

from google.appengine.api import mail, taskqueue
from google.appengine.ext import deferred, ndb
from google.appengine.ext.appstats import recording
from google.appengine.runtime import apiproxy_errors
from minimock import mock, restore

class Model(ndb.Model):
  pass

class Entity(object):
  key = "test"

class OverQuotaError():
  @ndb.tasklet
  def get_async(self, *argv, **kwargv):
    if kwargv.get("keys_only"):
      raise apiproxy_errors.OverQuotaError
    yield Model.query().get_async(*argv, **kwargv)
    raise ndb.Return(Entity())

  @ndb.tasklet
  def fetch_async(self, *argv, **kwargv):
    if kwargv.get("keys_only"):
      raise apiproxy_errors.OverQuotaError
    yield Model.query().fetch_async(*argv, **kwargv)
    raise ndb.Return([Entity()])

class TestFunctions(unittest.TestCase):
  def test_base_encode(self):
    assert utils.base_encode("test", 0) == "t"

  def test_encodeURI(self):
    assert utils.encodeURI(" /;") == "%20/;"

  def test_encodeURIComponent(self):
    assert utils.encodeURIComponent(" /;") == "%20%2F%3B"

  @ndb.synctasklet
  def test_get_keys_only(self):
    result = yield utils.get_keys_only(Model.query())
    assert result is None
    result =  yield utils.get_keys_only(OverQuotaError())
    assert result

  @ndb.synctasklet
  def test_fetch_keys_only(self):
    result = yield utils.fetch_keys_only(Model.query())
    assert result == []
    result = yield utils.fetch_keys_only(OverQuotaError())
    assert result

  def test_send_exception_report(self):
    with tests.util.set_config(DEBUG=False, JOB_EMAIL_RECIPIENT=True):
      with pytest.raises(mail.InvalidEmailError):
        assert utils.send_exception_report() == ""

  def test_exception_report(self):

    @utils.exception_report
    def f():
      raise

    with pytest.raises(Exception):
      f()

  def test_no_retry(self):

    @utils.no_retry
    def f():
      raise

    f()
    with tests.util.set_environ(HTTP_X_APPENGINE_TASKRETRYCOUNT="0"):
      with pytest.raises(deferred.PermanentTaskFailure):
        f()

  def test_memoize(self):

    @ndb.toplevel
    @utils.memoize(use_memcache=True)
    def f(x):
      return random()

    result = f(1)
    assert f(1) == result
    assert f(2) != result
    f._cache.clear()
    assert f(1) == result

class TestCacheMixin(unittest.TestCase):
  def test_get_key_name(self):
    assert utils.CacheMixin.get_key_name("") == "1B2M2Y8AsgTpgAmY7PhCfg"
    assert utils.CacheMixin.get_key_name("/") == "/"
    assert utils.CacheMixin.get_key_name("/"*22) == "//////////////////////"
    assert utils.CacheMixin.get_key_name("/"*23) == "qaf6bjEFhOwOKQzsIeCiIA"

class TestRequestHandler(unittest.TestCase):
  def test_to_cache_key(self):
    assert utils.RequestHandler.to_cache_key("") == "1B2M2Y8AsgTpgAmY7PhCfg"
    assert utils.RequestHandler.to_cache_key("/") == "/"
    assert utils.RequestHandler.to_cache_key("/"*22) == "//////////////////////"
    assert utils.RequestHandler.to_cache_key("/"*23) == "qaf6bjEFhOwOKQzsIeCiIA"

class AppTest(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  class Rec(object):
    def json(self): pass
    def record_http_status(self, *argv): pass
    def save(self): pass

  def setUp(self):
    super(AppTest, self).setUp()
    mock("recording.users.is_current_user_admin", returns=True)
    mock("recording.recorder_proxy.get_for_current_request", returns=self.Rec())

  def tearDown(self):
    restore()
    super(AppTest, self).tearDown()

  def test_end_recording(self):
    origin_RECORD_FRACTION = recording.config.RECORD_FRACTION
    recording.config.RECORD_FRACTION = 1
    origin_DEBUG = recording.config.DEBUG
    recording.config.DEBUG = True
    try:
      recording.start_recording()
      recording.end_recording("200", firepython_set_extension_data=lambda *argv:None)
    finally:
      recording.config.RECORD_FRACTION = origin_RECORD_FRACTION
      recording.config.DEBUG = origin_DEBUG

class TestTokenBucket(unittest.TestCase):
  def test_is_acceptable(self):
    with pytest.raises(ValueError):
      utils.TokenBucket(rate=3, size=10)

    b = utils.TokenBucket(rate=1, size=2)
    b.is_acceptable = ndb.toplevel(utils.make_synctasklet(b.is_acceptable_async))
    assert b.is_acceptable() is True
    assert b.is_acceptable() is True
    assert b.is_acceptable() is False

    b = utils.TokenBucket(rate=1, size=1, prefix="test")
    b.is_acceptable = ndb.toplevel(utils.make_synctasklet(b.is_acceptable_async))
    assert b.is_acceptable() is True
    assert b.is_acceptable() is False
    assert b.is_acceptable(key="test") is True
    assert b.is_acceptable(key="test") is False

def func():
  raise apiproxy_errors.OverQuotaError

class TestDeferredRun(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def test(self):
    with pytest.raises(deferred.PermanentTaskFailure):
      assert utils.deferred_run(None) is None

    data = pickle.dumps((func, tuple(), dict()))
    queue = taskqueue.Queue("default")
    assert queue.fetch_statistics().tasks == 0
    assert utils.deferred_run(data) is None
    assert queue.fetch_statistics().tasks == 1

class TestWaitEach(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  @ndb.tasklet
  def task(self):
    pass

  @ndb.tasklet
  def failer(self):
    yield self.task()
    raise Exception

  @ndb.tasklet
  def succeser(self):
    yield self.task()
    raise ndb.Return("success")

  def test_wait_each(self):
    futures = utils.wait_each([self.failer(), self.succeser()])
    assert futures.next() == "success"
    self.expected_logs = [
      ('WARNING', 'google/appengine/ext/ndb/tasklets.py', '_help_tasklet_along', 'suspended generator failer(test_functions.py:...) raised Exception()'),
      ('WARNING', 'gae/utils.py', 'wait_each', ''),
    ]

class TestWaitMap(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def setUp(self):
    super(TestWaitMap, self).setUp()
    self._WAIT_MAP_SIZE_org = utils.config.WAIT_MAP_SIZE
    utils.config.WAIT_MAP_SIZE = 1

  def tearDown(self):
    utils.config.WAIT_MAP_SIZE = self._WAIT_MAP_SIZE_org
    super(TestWaitMap, self).tearDown()

  @ndb.tasklet
  def task(self):
    pass

  @ndb.tasklet
  def failer(self):
    yield self.task()
    raise Exception

  @ndb.tasklet
  def succeser(self):
    yield self.task()
    raise ndb.Return("success")

  def test_wait_map(self):
    futures = utils.wait_map(lambda x:x, [self.failer(), self.succeser()])
    assert futures.next() == "success"
    self.expected_logs = [
      ('WARNING', 'google/appengine/ext/ndb/tasklets.py', '_help_tasklet_along', 'suspended generator failer(test_functions.py:...) raised Exception()'),
      ('WARNING', 'gae/utils.py', 'wait_map', ''),
    ]
