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

from minimock import mock, restore
from testfixtures import LogCapture
import webapp2
import webtest

from google.appengine.api import (
  apiproxy_stub_map,
  users,
)
from google.appengine.datastore import datastore_stub_util
from google.appengine.ext import deferred, testbed
import endpoints


# Search Path

def execute_once(func):

  @wraps(func)
  def inner(_result=[None], *argv, **kwargv):
    if _result[0] is None:
      _result[0] = func(*argv, **kwargv)
      if _result[0] is None:
        raise ValueError("The return value must be not `None`.")
    return _result[0]

  return inner

@execute_once
def sys_path_append():
  import google
  base = os.path.join(os.path.dirname(google.__file__), "../lib/")
  for webapp2 in ["webapp2-2.5.2", "webapp2"]:
    path = os.path.join(base, webapp2)
    if os.path.exists(path):
      sys.path.append(path)
      break
  else:
    raise
  for path in ["django-1.5", "endpoints-1.0", "protorpc-1.0", "jinja2-2.6"]:
    path = os.path.join(base, path)
    if os.path.exists(path):
      sys.path.append(path)
    else:
      raise
  return True

# initialize
sys_path_append()

if os.path.basename(os.path.abspath(".")) != "gae":
  if os.path.exists("gae"):
    os.chdir("gae")
    import tap
    os.chdir("../")
  else:
    import tap


get_tail = re.compile("^(.*/google_appengine([^/]+)?/)?(?P<tail>.*)$").match
is_server_error = re.compile(r"^.*?\s5\d{2}\s.*?$").match

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

def gen_test_app(request_handler, routes=None):
  if routes is None:
    routes = list()
  routes.insert(0, ("/", request_handler))
  return TestApp(webapp2.WSGIApplication(routes=routes))

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
  application = tap.app
  is_endpoints = False

  def __init__(self, *argv, **kwargv):
    super(TestCase, self).__init__(*argv, **kwargv)

    if isinstance(self.application, endpoints.api_config._ApiDecorator):
      api_names = list()
      for api_class in self.application.get_api_classes():
        for name, _method in api_class.all_remote_methods().items():
          api_names.append(name)
      self.api_names = tuple(api_names)
      self.application = endpoints.api_server([self.application], restricted=False)
      self.is_endpoints = True
    else:
      self.api_names = tuple()

  def setUp(self):
    # webtest
    if self.use_cookie:
      cookiejar = cookielib.CookieJar()
    else:
      cookiejar = None
    self.app = TestApp(self.application, domain=self.domain, cookiejar=cookiejar)
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
    restore()
    try:
      # logging
      for record in self.log.records:
        if self.is_endpoints and len(record.args) >= 3:
          exception = record.args[2]
          if isinstance(exception, endpoints.ServiceException):
            try:
              str(exception)
            except TypeError:
              record.args[2].args = [str(arg) for arg in exception.args]
            except UnicodeEncodeError:
              record.args[2].args = [unicode(arg) for arg in exception.args]
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
        elif self.is_endpoints:
          expected_log = (
            'WARNING',
            'google/appengine/ext/ndb/tasklets.py',
            '_help_tasklet_along',
            '... generator ...(....py:...) raised ...Exception(...)')
          if log[:2] == expected_log[:2]:
            if doctest._ellipsis_match(expected_log[3], log[3]):
              matched = True
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

  def endpoints_uri(self, endpoint):
    api_class_name, api_method_name = endpoint.split(".", 1)
    real_api_method_name = "_{0}_{1}".format(api_class_name, api_method_name)
    assert real_api_method_name in self.api_names
    return "/_ah/spi/{0}.{1}".format(api_class_name, real_api_method_name)

  def endpoints_via_oauth(self, email=None, _auth_domain=None,
               _user_id=None, federated_identity=None, federated_provider=None,
               _strict_mode=False):
    if email is not None:
      if _auth_domain is None:
        _auth_domain = email.split("@", 1)[1]
      if _user_id is None:
        _user_id = str(tap.base_decoder(sorted(set(email)))(email))
    user = users.User(email, _auth_domain,
               _user_id, federated_identity, federated_provider,
               _strict_mode)
    mock("endpoints.get_current_user", returns=user, tracker=None)
