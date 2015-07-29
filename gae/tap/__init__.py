# -*- coding: utf-8 -*-

from __future__ import absolute_import

from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps
from itertools import chain, imap, islice, izip
from xml.sax import saxutils
import UserDict
import cPickle as pickle
import inspect
import logging
import os
import pdb
import pprint
import string
import sys
import threading
import time
import traceback
import types
import urllib
import zlib

from google.appengine.api import (
  app_identity,
  datastore_errors,
  lib_config,
  mail,
  memcache,
  namespace_manager,
  taskqueue,
  urlfetch,
)
from google.appengine.ext import deferred, ndb
from google.appengine.ext.appstats import recording
from google.appengine.runtime import apiproxy_errors


# Global

EMAIL_TRIM_SIZE = 0x3000 #12kB
MAX_URLFETCH_DEADLINE = 60
NAMESPACE_KEY = "NAMESPACE"
ROOT_DIR_PATH = os.path.abspath(os.path.curdir)
TASKQUEUE_MAXSIZE = 1000
_memoize_cache = dict()


# Config

class ConfigDefaults(object):
  API = {
    #{<domain>: ((<path prefix>, <module name>[, <namespace>]),)}
  }
  APP = {
    #{<domain>: ((<path prefix>, <module name>[, <namespace>]),)}
  }
  APPSTATS_INCLUDE_ERROR_STATUS = True
  ASSOCIATE_TAG = "gaetap-22"
  BACKEND_NAME = "backend"
  BANG_REDIRECTOR = "http://goo.gl/"
  CORS_Access_Control_Max_Age = "3628800" # 30d
  CSRF_TIME = 60
  DEBUG = os.environ.get('SERVER_SOFTWARE', 'Dev').startswith('Dev')
  DEFERRED_HANDLE_OverQuotaError = True
  DRIVE_PROXY_UID = None
  DROPBOX_PROXY_UID = None
  ENSURE_FREE_SPACE = 0x3200000 # 50MB
  FANSTATIC = dict(
    base_url = "/static",
    minified = True,
    publisher_signature = "lib",
    versioning = True,
    versioning_use_md5 = True,
  )
  FEEDBACK_FORMKEY = None
  GA_ACCOUNT = None
  I18N_TRANSLATIONS_PATH = "locales"
  IMAGE_URL = ""
  IS_TEST = "unittest" in sys.modules.keys()
  JINJA2_COMPILED_PATH = ("site-packages/tap_templates_compiled.zip", "site-packages/templates_compiled.zip")
  JINJA2_TEMPLATE_PATH = ("tap/templates", "templates")
  JINJA2_FORCE_COMPILED = True
  JOB_EMAIL_RECIPIENT = None
  MEDIA_URL = ""
  RESPONSE_CACHE_SIZE = 0x10000 # 65536
  ROUTES = (
    (r"^/sitemap[^/]+\.xml$", "tap.ext.Sitemap"),
    (r"^/_ah/(start|stop|warmup)$", "tap.Dummy"),
    (r"^/_tap/generate_sitemap$", "tap.ext.GenerateSitemap"),
    (r"^/_tap/maintain_response$", "tap.ext.MaintainResponse"),
    (r"^/_tap/response_cache$", "tap.ext.ResponseCache"),
  )
  SECRET_KEY = None
  SESSION_MAX_AGE = 3600 # 1h
  SITEMAP_QUEUE = "sitemap"
  SITE_PACKAGES = "site-packages"
  URI_AUTHORITY = "localhost:8080" if DEBUG else "{0}.appspot.com".format(app_identity.get_application_id())
  WAIT_MAP_SIZE = 10
  WEBAPP2_CONFIG = None
config = lib_config.register("config", ConfigDefaults.__dict__)
config.LOCALE_PATH = os.path.join(ROOT_DIR_PATH, config.I18N_TRANSLATIONS_PATH)
if config.IS_TEST:
  config.SITE_PACKAGES = os.path.abspath(config.SITE_PACKAGES)


# fix sys.path
os.environ["SITE_PACKAGES"] = config.SITE_PACKAGES
from . import warmup


def execute_once(func):
  @wraps(func)
  def inner(_result=[None], *argv, **kwargv):
    if _result[0] is None:
      _result[0] = func(*argv, **kwargv)
      if _result[0] is None:
        raise ValueError("The return value must be not `None`.")
    return _result[0]
  return inner


try:
  from django.utils.functional import memoize as _memoize
except ImportError as e:
  if sys.argv[0].endswith("/endpointscfg.py"):
    pass
  else:
    logging.warning("{0}: {1}".format(e.__class__.__name__, e))
  def _memoize(func, *argv):
    return func
from webapp2_extras import routes
import webapp2


# Decorators

def logging_exception_traceback(func):

  @wraps(func)
  def wrapper(*args, **kwargv):
    try:
      return func(*args, **kwargv)
    except:
      logging.error(traceback.format_exc())
      raise

  return wrapper

def memoize(num_args=None, use_memcache=False):

  def decorator(func):
    if func.__code__.co_name == 'synctasklet_wrapper' and num_args is None:
      raise ValueError("A function that wrapped 'ndb.synctasklet' is required 'num_args'.")

    key = ".".join((func.__module__, func.__name__))

    @wraps(func)
    @ndb.synctasklet
    def wrapper(*args):
      if use_memcache is not True:
        result = func(*args)
        if isinstance(result, types.GeneratorType):
          raise TypeError("'generator' object is not allowed")
        raise ndb.Return(result)
      cache_key = ":".join(("memoize", key, args.__str__()))
      ctx = ndb.get_context()
      cache = yield ctx.memcache_get(cache_key, use_cache=True)
      if cache is not None:
        raise ndb.Return(loads(cache))
      result = func(*args)
      if isinstance(result, types.GeneratorType):
        raise TypeError("'generator' object is not allowed")
      ctx.memcache_set(cache_key, dumps(result), use_cache=True)
      raise ndb.Return(result)

    cache = _memoize_cache.get(key)
    if cache is None:
      with threading.Lock():
        cache = _memoize_cache.get(key)
        if cache is None:
          cache = _memoize_cache[key] = dict()
    memoized = _memoize(wrapper, cache, num_args or func.__code__.co_argcount)
    memoized._cache = cache
    memoized._func = func
    memoized._key = key
    return memoized

  return decorator

@ndb.tasklet
def memoize_clear(cache, key, args, use_memcache=False):
  if use_memcache:
    cache_key = ":".join(("memoize", key, args.__str__()))
    yield ndb.get_context().memcache_delete(cache_key)
  if args in cache:
    with threading.Lock():
      if args in cache:
        del cache[args]

def in_namespace(namespace):

  def decorator(func):

    @wraps(func)
    def wrapper(*args, **kwargv):
      old_namespace = namespace_manager.get_namespace()
      if callable(namespace):
        new_namespace = namespace()
      else:
        new_namespace = namespace
      namespace_manager.set_namespace(new_namespace)
      try:
        return func(*args, **kwargv)
      finally:
        namespace_manager.set_namespace(old_namespace)

    return wrapper

  return decorator

def parse_vars(arg_name, stack_level=2):
  """

  >>> @parse_vars("bar")
  ... def x(*argv, **kwargv):
  ...   return argv, kwargv
  >>> def f():
  ...   a = 0
  ...   b = "1"
  ...   c = locals()
  ...   return x(foo=(a,), bar=(b,))
  >>> f()
  ((), {'foo': (0,), 'bar': {'b': '1'}})
  """
  def wrapper(func):

    @wraps(func)
    def inner(*argv, **kwargv):
      args = kwargv.get(arg_name)
      if args:
        kwargv[arg_name] = get_vars_from_frame(args, stack_level)
      return func(*argv, **kwargv)

    return inner
  return wrapper

def set_urlfetch_deadline(deadline):

  def wrapper(func):

    @wraps(func)
    def inner(*argv, **kwargv):
      orig_deadline = urlfetch.get_default_fetch_deadline()
      urlfetch.set_default_fetch_deadline(deadline)
      try:
        return func(*argv, **kwargv)
      finally:
        urlfetch.set_default_fetch_deadline(orig_deadline)

    return inner

  return wrapper


# Context Managers

@contextmanager
def on_namespace(namespace):
  old_namespace = namespace_manager.get_namespace()
  namespace_manager.set_namespace(namespace)
  try:
    yield
  finally:
    namespace_manager.set_namespace(old_namespace)


# Functions

def base_decoder(alphabet):
  """

  >>> base32_decode = base_decoder("23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
  >>> base32_decode("36TE2QL")
  1234567890

  Note: will return 0 if given empty string
  >>> base32_decode("")
  0
  """
  reverse_base = dict((c, i) for i, c in enumerate(alphabet))
  length = len(reverse_base)

  def base_decode(string):
    num = 0
    for index, char in enumerate(reversed(string)):
      num += (length ** index) * reverse_base[char]
    return num

  return base_decode

def base_encoder(alphabet):
  """

  >>> base32_encode = base_encoder("23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
  >>> base32_encode(1234567890)
  '36TE2QL'
  """
  base = len(alphabet)

  def func(num):
    if num == 0:
      return alphabet[0]
    result = ""
    while num != 0:
      result = alphabet[num % base] + result
      num /= base
    return result

  return func

base62_decode = base_decoder(string.digits + string.letters)
base62_encode = base_encoder(string.digits + string.letters)

def config_to_dict(config):
  result = dict(config._defaults)
  result.update(config._overrides)
  return result

def divide(sequence, size):
  """ 3 times faster than idivide

  >>> [i for i in divide(range(10), 3)]
  [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
  """
  i = 0
  while sequence[i:i+1]:
    yield sequence[i:i+size]
    i += size

def idivide(iterable, size):
  """ Yields items from an iterator in iterable chunks

  >>> [list(i) for i in idivide(iter(xrange(10)), 3)]
  [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
  """
  iterable_next = iterable.next
  while True:
    yield chain([iterable_next()], islice(iterable, size-1))

def idivide2(iterable, size):
  """ 2 times faster than idivide

  >>> [i for i in idivide2(iter(xrange(10)), 3)]
  [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
  """
  return imap(None, *(iterable,) * size)

def dumps(value):
  return zlib.compress(pickle.dumps(value, pickle.HIGHEST_PROTOCOL))

def loads(data):
  return pickle.loads(zlib.decompress(data))

def encodeURI(data):
  return urllib.quote(data, safe="~@#$&()*!+=:;,.?/'")

def encodeURIComponent(data):
  return urllib.quote(data, safe="~()*!.'")

@execute_once
def get_api():
  import endpoints
  api_services = list()
  for api in config.API:
    module = webapp2.import_string(api)
    api_services.extend(module.api_services)
  return endpoints.api_server(api_services)

@execute_once
def get_app():
  config_dict = config_to_dict(config)
  config_dict.update({
    "webapp2_extras.jinja2": {
      "compiled_path": tuple([os.path.join(ROOT_DIR_PATH, path) for path in config.JINJA2_COMPILED_PATH]),
      "template_path": tuple([os.path.join(ROOT_DIR_PATH, path) for path in config.JINJA2_TEMPLATE_PATH]),
      "environment_args": {"extensions": ["jinja2.ext.i18n"]},
      "force_compiled": config.JINJA2_FORCE_COMPILED,
    },
    "webapp2_extras.sessions": {
      "cookie_name": "__s",
      "secret_key": config.SECRET_KEY,
      "session_max_age": config.SESSION_MAX_AGE,
    },
  })
  config_WEBAPP2_CONFIG = config_dict.pop("WEBAPP2_CONFIG")
  if config_WEBAPP2_CONFIG is not None:
    config_dict.update(config_WEBAPP2_CONFIG)
  routes_list = list()
  routes_list.extend(config.ROUTES)
  routes_list.extend((
    webapp2.Route("/oauth/signout", handler="tap.ext.OAuth:_signout", name="oauth_signout"),
    webapp2.Route("/oauth/<provider>", handler="tap.ext.OAuth:_simple_auth", name="oauth_signin"),
    webapp2.Route("/oauth/<provider>/callback", handler="tap.ext.OAuth:_auth_callback", name="oauth_callback"),
    webapp2.Route("/_tap/i18n/<domain>.<language>.js", "tap.ext.I18Njs", name="I18Njs"),
  ))
  if config.BANG_REDIRECTOR:
    routes_list.append(webapp2.Route("/!<key:[^/]+>", "tap.ext.BangRedirector", name="bang-redirector"))
  for domain, values in config.APP.viewitems():
    app_routes_by_domain = list()
    for value in values:
      prefix, app, namespace = (value + (None,))[:3]
      module = webapp2.import_string(app)
      if hasattr(module, "routes"):
        app_routes = module.routes
      else:
        logging.warning("{0} has not `routes`".format(module))
        continue
      if namespace is not None:
        setattr(module, NAMESPACE_KEY, namespace)
      if prefix:
        app_routes = [routes.PathPrefixRoute(prefix, app_routes)]
      app_routes_by_domain.extend(app_routes)
    if domain:
      app_routes_by_domain = [routes.DomainRoute(domain, app_routes_by_domain)]
    elif not config.IS_TEST: #TODO: remove
      raise ValueError("domain is required by {values}".format(values=values))
    routes_list.extend(app_routes_by_domain)
  if config.DRIVE_PROXY_UID is not None:
    routes_list.append(routes.DomainRoute(r"<domain:^.+?\.[a-zA-Z]{2,5}$>", [webapp2.Route(r"<path:.*>", "tap.ext.DriveProxy")]))
  elif config.DROPBOX_PROXY_UID is not None:
    routes_list.append(routes.DomainRoute(r"<domain:^.+?\.[a-zA-Z]{2,5}$>", [webapp2.Route(r"<path:.*>", "tap.ext.DropboxProxy")]))
  return webapp2.WSGIApplication(routes=routes_list, debug=config.DEBUG, config=config_dict)

@memoize()
def get_namespaced_secret_key(namespace):
  return "".join((config.SECRET_KEY, namespace))

@ndb.tasklet
def get_keys_only(query):
  """ Fallback when be limited Datastore Small Operations
  """
  try:
    key = yield query.get_async(keys_only=True)
    raise ndb.Return(key)
  except apiproxy_errors.OverQuotaError:
    result = yield query.get_async()
    if result:
      raise ndb.Return(result.key)

def get_vars_from_frame(args, stack_level=1):
  """

  >>> def f(arg1, arg2=None):
  ...   local_value1 = "val1"
  ...   local_value2 = "val2"
  ...   local_value3 = local_value1
  ...   local_value4 = locals()
  ...   return get_vars_from_frame((local_value1, arg1))
  >>> sorted(f("a", "b").items())
  [('arg1', 'a'), ('local_value1', 'val1'), ('local_value3', 'val1')]
  """
  id_list = [id(i) for i in args]
  return dict((k,v) for k,v in inspect.currentframe(stack_level).f_locals.items() if id(v) in id_list)

def html_escape(value):
  return saxutils.escape(value, {"\'":"&apos;", "\"":"&quot;"})

@ndb.tasklet
def fetch_keys_only(query, limit=None):
  """ Fallback when be limited Datastore Small Operations
  """
  try:
    keys = yield query.fetch_async(limit, keys_only=True)
    raise ndb.Return(keys)
  except apiproxy_errors.OverQuotaError:
    entities = yield query.fetch_async(limit)
    raise ndb.Return([entity.key for entity in entities])

@ndb.tasklet
def fetch_page_async(query, page=10, cursor_string=None, cursor=None, keys_only=False):
  if cursor_string is None:
    cursor_string = ""
  if cursor is None:
    try:
      cursor = ndb.Cursor.from_websafe_string(cursor_string)
    except datastore_errors.BadValueError:
      cursor = ndb.Cursor.from_websafe_string("")
  results, cursor, more = yield query.fetch_page_async(page, start_cursor=cursor, keys_only=keys_only)
  raise ndb.Return(results, cursor, more)

def make_synctasklet(tasklet):

  @wraps(tasklet)
  @ndb.synctasklet
  def synctasklet(*argv, **kwargv):
    result = yield tasklet(*argv, **kwargv)
    raise ndb.Return(result)

  return synctasklet

def set_trace():
  pdb.Pdb(stdin=sys.__stdin__, stdout=sys.__stdout__).set_trace(sys._getframe().f_back)

def send_exception_report():
  if not config.DEBUG and config.JOB_EMAIL_RECIPIENT:
    to = config.JOB_EMAIL_RECIPIENT
    subject = "[Exception] {0}".format(traceback.format_exception_only(*sys.exc_info()[:2])[0].split(":")[0])
    stacktrace = "".join(traceback.format_exception(*sys.exc_info()))
    body = "\n\n".join((stacktrace, pprint.pformat(dict(**os.environ))))
    mail.send_mail_to_admins(to, subject, body[:EMAIL_TRIM_SIZE])

def wait_each(futures):
  while futures:
    future = ndb.Future.wait_any(futures)
    futures.remove(future)
    yield future

def wait_map(func, *sequences):
  isequences = izip(*sequences)
  futures = [func(*isequences.next()) for i in xrange(config.WAIT_MAP_SIZE)]
  while futures:
    future = ndb.Future.wait_any(futures)
    futures.remove(future)
    try:
      futures.append(func(*isequences.next()))
    except StopIteration:
      pass
    yield future


# Classes

class ChainMap(UserDict.DictMixin):
  """Combine multiple mappings for sequential lookup.

  http://code.activestate.com/recipes/305268/
  For example, to emulate Python's normal lookup sequence:

  >>> cm = ChainMap({'a':1, 'b':2}, {'a':3, 'd':4})
  >>> assert cm['a'] == 1
  >>> assert cm['b'] == 2
  >>> assert cm['d'] == 4
  >>> cm.get('f')
  """

  def __init__(self, *maps):
    self._maps = maps

  def __getitem__(self, key):
    for mapping in self._maps:
      try:
        return mapping[key]
      except KeyError:
        pass
    raise KeyError(key)

class Queue(object):
  queue_name = "queue"
  queue = taskqueue.Queue(queue_name)
  tag = None
  lease_seconds = 600 # 10m

  def __init__(self, tag):
    self.tag = tag

  def put(self, *values):
    if len(values):
      self.queue.add([taskqueue.Task(payload=dumps(value), method="PULL", tag=self.tag) for value in values])

  def collect(self, lease_seconds=None):
    if lease_seconds is None:
      lease_seconds = self.lease_seconds
    while True:
      delete_tasks = list()
      try:
        for task in self.queue.lease_tasks_by_tag(lease_seconds, TASKQUEUE_MAXSIZE, self.tag):
          yield loads(task.payload)
          delete_tasks.append(task)
      finally:
        self.queue.delete_tasks(delete_tasks)
        if len(delete_tasks) < TASKQUEUE_MAXSIZE:
          return

class RingBuffer(object):
  queue_name = "ringbuffer"
  queue = taskqueue.Queue(queue_name)
  size = TASKQUEUE_MAXSIZE - 1
  tag = None

  def __init__(self, tag, size=None):
    if size is not None:
      if 0 < size < TASKQUEUE_MAXSIZE:
        self.size = size
      else:
        raise ValueError("'size' must be 1-{0}".format(TASKQUEUE_MAXSIZE - 1))
    self.tag = tag

  @classmethod
  @ndb.toplevel
  @ndb.synctasklet
  def clean(cls, tag, size):
    buf = cls.queue.lease_tasks_by_tag(0, TASKQUEUE_MAXSIZE, tag)
    overflow = len(buf) - size
    if overflow > 0:
      cls.queue.delete_tasks(buf[:overflow])
    cache = cls._get._cache
    key = cls._get._key
    args = (cls.queue_name, tag, size)
    yield memoize_clear(cache, key, args)

  @ndb.tasklet
  def clear(self):
    self.queue.delete_tasks(self.queue.lease_tasks_by_tag(0, TASKQUEUE_MAXSIZE, self.tag))
    cache = self._get._cache
    key = self._get._key
    args = (self.queue_name, self.tag, self.size)
    yield memoize_clear(cache, key, args)

  @staticmethod
  @memoize()
  def _get(queue_name, tag, size):
    try:
      buf = taskqueue.Queue(queue_name).lease_tasks_by_tag(0, TASKQUEUE_MAXSIZE, tag)
    except taskqueue.TransientError:
      return
    if len(buf) >= size:
      deferred.defer(RingBuffer.clean, tag, size)
    return [loads(task.payload) for task, _i in zip(reversed(buf), xrange(size))]

  def get(self):
    return self._get(self.queue_name, self.tag, self.size)

  def put(self, *values):
    if len(values):
      self.queue.add([taskqueue.Task(payload=dumps(value), method="PULL", tag=self.tag) for value in values])
    deferred.defer(self.__class__.clean, self.tag, self.size)

class TokenBucket(object):
  prefix = ""

  def __init__(self, rate, size, prefix=None):
    if size % rate != 0:
      raise ValueError("'size' must be multipule of 'rate'")
    self.rate = rate
    self.size = size
    self.period = size / rate
    if prefix is not None:
      self.prefix = prefix

  def base_key(self, key=None):
    elements = ["TokenBucket", self.prefix]
    if key is not None:
      elements.append(key)
    return ":".join(elements)

  @ndb.tasklet
  def is_acceptable_async(self, key=None):
    ctx = ndb.get_context()
    key_prefix = "{0}:".format(self.base_key(key))
    now = int(time.time()) / 60 * 60
    keys = [str(now - i * 60) for i in xrange(self.period)]
    bucket_key = "".join((key_prefix, keys[0]))
    if self.period == 1:
      result = yield ctx.memcache_get(bucket_key, use_cache=True)
      buckets = dict()
      if result is not None:
        buckets[keys[0]] = result
    else:
      buckets = yield memcache.Client().get_multi_async(keys, key_prefix=key_prefix)
    if sum(buckets.itervalues()) >= self.size:
      raise ndb.Return(False)
    elif buckets.get(keys[0]) is None:
      ctx.memcache_set(bucket_key, 1, time=self.period * 60)
    else:
      ctx.memcache_incr(bucket_key)
    raise ndb.Return(True)


# Task Decorators

def exception_report(func):
  @wraps(func)
  def inner(*argv, **kwargv):
    try:
        return func(*argv, **kwargv)
    except Exception:
      send_exception_report()
      raise
  return inner

def no_retry(func):
  @wraps(func)
  def inner(*argv, **kwargv):
    if int(os.environ.get("HTTP_X_APPENGINE_TASKRETRYCOUNT", 1)) <= 0:
      try:
        return func(*argv, **kwargv)
      except Exception as e:
        raise deferred.PermanentTaskFailure(e)
    logging.warning("Aborted, because this task is set no-retry.")
  return inner


# View Classes

class Dummy(webapp2.RequestHandler):
  def get(self, *argv, **kwargv):
    pass


# APPSTATS

def end_recording(status, firepython_set_extension_data=None):
  rec = recording.recorder_proxy.get_for_current_request()
  recording.recorder_proxy.clear_for_current_request()
  if recording.config.DEBUG:
    logging.debug('Cleared recorder')
  if rec is not None:
    try:
      if save_record(status):
        rec.record_http_status(status)
        rec.save()
      if (firepython_set_extension_data and
          (os.getenv('SERVER_SOFTWARE', '').startswith('Dev') or
           recording.users.is_current_user_admin())):
        logging.info('Passing data to firepython')
        firepython_set_extension_data('appengine_appstats', rec.json())
    finally:
      memcache.delete(recording.lock_key(), namespace=recording.config.KEY_NAMESPACE)

def save_record(status):
  """

  >>> save_record("200")
  True
  >>> save_record("500")
  False
  """
  if isinstance(status, basestring) and status.isalnum() :
    status = int(status)
  return status < 500

if not config.APPSTATS_INCLUDE_ERROR_STATUS:
  recording.end_recording = end_recording


# Deferred

def deferred_run(data):
  try:
    func, args, kwds = pickle.loads(data)
  except Exception as e:
    raise deferred.PermanentTaskFailure(e)
  else:
    try:
      return func(*args, **kwds)
    except apiproxy_errors.OverQuotaError:
      now = datetime.now()
      hours = 8
      if now.hour >= hours:
        hours += 24
      kwds["_eta"] = datetime(*tuple(now.timetuple())[:3]) + timedelta(hours=hours)
      deferred.defer(func, args, kwds)

if config.DEFERRED_HANDLE_OverQuotaError:
  deferred.run = deferred_run


# Applications

api = get_api()
app = get_app()


# Returns a Jinja2 renderer cached in the app registry.
def new_jinja2():
  from webapp2_extras import jinja2
  import tap.ext
  return jinja2.get_jinja2(factory=tap.ext.Jinja2Factory, app=app)

@execute_once
def jinja2():
  return new_jinja2()
