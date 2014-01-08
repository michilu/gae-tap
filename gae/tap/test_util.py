from contextlib import contextmanager
from functools import wraps
import abc
import base64
import cookielib
import doctest
import logging
import os
import pdb
import re
import sys
import unittest

from testfixtures import LogCapture
import webapp2
import webtest

from google.appengine.api import apiproxy_stub_map
from google.appengine.datastore import datastore_stub_util
from google.appengine.ext import deferred, testbed

get_tail = re.compile("^(.*/google_appengine([^/]+)?/)?(?P<tail>.*)$").match
is_server_error = re.compile(r"^.*?\s5\d{2}\s.*?$").match

# initialize
if os.path.basename(os.path.abspath(".")) != "gae":
  if os.path.exists("gae"):
    os.chdir("gae")
    import tap
    os.chdir("../")
  else:
    import tap

@contextmanager
def set_config(**kwargv):
  config = tap.config
  origin = dict()
  for key, value in kwargv.iteritems():
    if hasattr(config, key):
      origin[key] = getattr(config, key)
    setattr(config, key, value)
  try:
    yield
  finally:
    for key, value in kwargv.iteritems():
      if key in origin:
        setattr(config, key, origin[key])
      else:
        delattr(config, key)

@contextmanager
def set_environ(**kwargv):
  origin = dict()
  for key, value in kwargv.iteritems():
    if key in os.environ:
      origin[key] = os.environ[key]
    os.environ[key] = value
  try:
    yield
  finally:
    for key, value in kwargv.iteritems():
      if key in origin:
        os.environ[key] = origin[key]
      else:
        del os.environ[key]

def gen_test_app(request_handler):
  return TestApp(webapp2.WSGIApplication(routes=[("/", request_handler)]))

def set_domain(domain):

  def decorator(func):

    @wraps(func)
    def wrapper(url, *args, **kwargv):
      return func("http://{domain}{url}".format(domain=domain, url=url), *args, **kwargv)

    return wrapper

  return decorator

class TestApp(webtest.TestApp):
  def __init__(self, app, domain=None, *argv, **kwargv):
    if domain is not None:
      decorator = set_domain(domain)
      #for method_name in ("get", "post", "put", "patch", "delete", "options", "head", "post_json", "put_json", "patch_json", "delete_json"):
      for method_name in ("get", "post", "put", "delete", "options", "head", "post_json", "put_json", "delete_json"):
        setattr(self, method_name, decorator(getattr(self, method_name)))
    super(TestApp, self).__init__(app, *argv, **kwargv)

  def _check_status(self, status, res):
    try:
      return super(TestApp, self)._check_status(status, res)
    except Exception as e:
      if isinstance(e, webtest.AppError) and is_server_error(e.message):
        res.showbrowser()
      raise

  def _check_errors(self, res):
    try:
      return super(TestApp, self)._check_errors(res)
    except Exception as e:
      if isinstance(e, webtest.AppError) and is_server_error(e.message):
        res.showbrowser()
      raise

class TestCase(unittest.TestCase):
  __metaclass__ = abc.ABCMeta
  root_path = os.path.dirname(os.path.dirname(__file__))
  environ = dict()
  domain = None
  use_cookie = False

  def setUp(self):
    # webtest
    if self.use_cookie:
      cookiejar = cookielib.CookieJar()
    else:
      cookiejar = None
    self.app = TestApp(tap.app, domain=self.domain, cookiejar=cookiejar)
    # os.environ
    self.origin_environ = dict()
    if "HTTP_HOST" not in self.environ.viewkeys():
      self.environ["HTTP_HOST"] = "localhost"
    for key, value in self.environ.viewitems():
      self.origin_environ[key], os.environ[key] = os.environ.get(key), value
    # testbed
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub(consistency_policy=datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0))
    self.testbed.init_blobstore_stub()
    self.testbed.init_files_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_taskqueue_stub(root_path=self.root_path)
    # logging
    self.log = LogCapture(level=logging.WARNING)
    self.log.install()

  def tearDown(self):
    try:
      # logging
      for record in self.log.records:
        pathname = get_tail(record.pathname).group("tail")
        log = (record.levelname, pathname.replace(os.path.abspath(os.curdir), "").lstrip("/"), record.funcName, record.getMessage())
        if getattr(self, "expected_logs", None):
          if log in self.expected_logs:
            continue
          matched = None
          for expected_log in self.expected_logs:
            if "..." in expected_log[3]:
              if log[:2] == expected_log[:2]:
                if doctest._ellipsis_match(expected_log[3], log[3]):
                  matched = True
                  continue
          if matched:
            continue
        print(record.levelname, pathname, record.lineno, record.funcName, record.getMessage())
        assert not log
    finally:
      self.log.clear()
      self.log.uninstall()
      # testbed
      self.testbed.deactivate()
      # os.environ
      for key, value in self.origin_environ.iteritems():
        if value is not None:
          os.environ[key] = value

  def execute_tasks(self, queue_name):
    taskqueue_stub = apiproxy_stub_map.apiproxy.GetStub("taskqueue")
    tasks = taskqueue_stub.GetTasks(queue_name)
    for task in tasks:
      deferred.run(base64.b64decode(task["body"]))
      taskqueue_stub.DeleteTask(queue_name, task["name"])
