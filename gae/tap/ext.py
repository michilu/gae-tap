# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import wraps
from urlparse import urlparse
import base64
import gettext
import hashlib
import inspect
import json
import logging
import os
import re
import string
import time
import urllib
import uuid

from google.appengine.api import (
  app_identity,
  memcache,
  modules,
  namespace_manager,
  oauth,
  taskqueue,
  urlfetch,
)
from google.appengine.ext import ndb, zipserve
from google.appengine.runtime import apiproxy_errors
import tap

try:
  from django.utils.crypto import get_random_string
except ImportError as e:
  logging.warning("{0}: {1}".format(e.__class__.__name__, e))
try:
  from gdata.spreadsheet.service import SpreadsheetsService
  import gdata.alt.appengine
except ImportError:
  gdata = None
from webapp2_extras import jinja2, routes, security, sessions
import webapp2
import webob

try:
  from simpleauth import SimpleAuthHandler
except ImportError:
  class SimpleAuthHandler(object):
    def _auth_callback(self, *argv, **kwargv): raise NotImplementedError
    def _simple_auth(self, *argv, **kwargv): raise NotImplementedError


# Global

AHEAD_HTML5 = "<!DOCTYPE html>\n<html>"
METHOD_NAMES = tuple(webapp2._normalize_handler_method(method_name) for method_name in webapp2.WSGIApplication.allowed_methods)
RE_JS_Comments = re.compile(r"//.*$")
RE_JS_MultiLineComments = re.compile(r"/\*.*\*/", re.DOTALL)
_ = gettext.gettext


# Search Modules

try:
  import uamobile
except ImportError as _e:
  class uamobile(object):
    @staticmethod
    def is_featurephone(x):
      return False
try:
  import zenhan
except ImportError as _e:
  zenhan = None

class GoogleAnalyticsMixin(object):
  def _google_analytics_tracking(*argv, **kwargv):
    pass
if tap.config.GA_ACCOUNT:
  try:
    from ga import GoogleAnalyticsMixin
  except ImportError as e:
    logging.warning("{0}: {1}".format(e.__class__.__name__, e))


# Functions

@tap.memoize()
def get_resource_code(resources):
  try:
    import fanstatic
  except ImportError:
    return ""
  needed = fanstatic.NeededResources(**tap.config.FANSTATIC)
  for resource in resources:
    if isinstance(resource, basestring):
      resource = webapp2.import_string(resource, silent=True)
      if resource is None:
        continue
    needed.need(resource)
  return needed.render_inclusions(needed.resources())

@tap.memoize()
def get_translation(domain, languages, fallback, format):
  try:
    translation = gettext.translation(domain, tap.config.LOCALE_PATH, languages=languages, fallback=fallback, codeset="utf-8")
  except IOError:
    if format == "json":
      return "{}"
  else:
    if format == "json":
      return translations_to_json(translation)
    return translation

def translations_to_dict(translations):
    """Convert a GNUTranslations object into a dict for jsonifying.

    Args:
        translations: GNUTranslations object to be converted.

    Returns:
        A dictionary representing the GNUTranslations object.
    """
    plural = None
    n_plural = 2
    if '' in translations._catalog:
      for l in translations._catalog[''].split('\n'):
        if l.startswith('Plural-Forms:'):
          plural = l.split(':', 1)[1].strip()
    if plural is not None:
      for raw_element in plural.split(';'):
        element = raw_element.strip()
        if element.startswith('nplurals='):
          n_plural = int(element.split('=', 1)[1])
        elif element.startswith('plural='):
          plural = element.split('=', 1)[1]
    else:
      n_plural = 2
      plural = '(n == 1) ? 0 : 1'

    translations_dict = {'plural': plural, 'catalog': {}, 'fallback': None}
    if translations._fallback is not None:
       translations_dict['fallback'] = translations_to_dict(translations._fallback)
    for key, value in translations._catalog.items():
      if key == '':
        continue
      if isinstance(key, basestring):
        translations_dict['catalog'][key] = value
      elif isinstance(key, tuple):
        if not key[0] in translations_dict['catalog']:
          translations_dict['catalog'][key[0]] = [''] * n_plural
        translations_dict['catalog'][key[0]][int(key[1])] = value
    return translations_dict

def translations_to_json(translations):
  return json.dumps(translations_to_dict(translations))


# Classes

class Jinja2Factory(jinja2.Jinja2):
  def __init__(self, app, jinja2_config=None):
    self.config = jinja2_config = app.config.load_config(self.config_key,
      default_values=jinja2.default_config, user_values=jinja2_config,
      required_keys=None)
    kwargs = jinja2_config["environment_args"].copy()

    if "loader" not in kwargs:
      template_path = jinja2_config["template_path"]
      compiled_path = jinja2_config["compiled_path"]
      use_compiled = jinja2_config["force_compiled"]

      if compiled_path and use_compiled:
        kwargs["loader"] = jinja2.jinja2.ModuleLoader(compiled_path)
      else:
        kwargs["loader"] = jinja2.jinja2.FileSystemLoader(template_path)

    env = jinja2.jinja2.Environment(**kwargs)

    if jinja2_config["globals"]:
      env.globals.update(jinja2_config["globals"])

    if jinja2_config["filters"]:
      env.filters.update(jinja2_config["filters"])

    self.environment = env

class User(object):
  _auth_info = _data = _id = _provider = None
  _session_key = "_u"
  _save_attributes = {
    "_id": "i",
    "_provider": "p",
  }
  default_provider = "google"
  save_attributes = {
    "name": "n",
  }

  def __init__(self, data=None, auth_info=None, provider=None):
    if data is None:
      data = dict()
    if provider == self.default_provider:
      provider = None
    self._auth_info = auth_info
    self._data = data
    self._id = data.get("id")
    self._provider = provider

  def __getattribute__(self, name):
    try:
      return super(User, self).__getattribute__(name)
    except AttributeError as e:
      try:
        return self._data[name]
      except KeyError:
        raise AttributeError(e)

  def __setattr__(self, name, value):
    try:
      super(User, self).__getattribute__(name)
    except AttributeError:
      self._data[name] = value
    else:
      super(User, self).__setattr__(name, value)

  def __delattr__(self, name):
    try:
      super(User, self).__getattribute__(name)
    except AttributeError as e:
      try:
        del self._data[name]
      except KeyError:
        raise AttributeError(e)
    else:
      super(User, self).__delattr__(name)

  @classmethod
  def load_from_session(cls, session):
    session_u = session.get(cls._session_key)
    if session_u is None:
      return
    user = cls()
    for attribute_name, session_key in user._save_attributes.items():
      value = session_u.get(session_key)
      if value is not None:
        setattr(user, attribute_name, value)
    for data_key, session_key in user.save_attributes.items():
      value = session_u.get(session_key)
      if value is not None:
        user._data[data_key] = value
    return user

  def set_to_session(self, session):
    session_u = session.get(self._session_key, dict())
    for data_key, session_key in self.save_attributes.items():
      value = self._data.get(data_key)
      if value is None and session_u.has_key(session_key):
        del session_u[session_key]
      else:
        session_u[session_key] = value
    for attribute_name, session_key in self._save_attributes.items():
      value = getattr(self, attribute_name, None)
      if value is None and session_u.has_key(session_key):
        del session_u[session_key]
      else:
        session_u[session_key] = value
    session[self._session_key] = session_u

  def nickname(self):
    return self._data.get("name")

  def email(self):
    return self._data.get("email")

  def user_id(self):
    assert self._id
    if self._provider:
      return ":".join((self._provider, self._id))
    else:
      return self._id

class Users(object):
  def __init__(self, app):
    self._app = app

  def create_login_url(self, provider="google"):
    return webapp2.uri_for("oauth_signin", _request= self._app.request, provider=provider)

  def create_logout_url(self):
    return self._create_logout_url

  def get_current_user(self):
    return self._get_current_user

  @webapp2.cached_property
  def _create_logout_url(self):
    return webapp2.uri_for("oauth_signout", _request= self._app.request)

  @webapp2.cached_property
  def _get_current_user(self):
    return User.load_from_session(self._app.session)


# Model Mixins

class CacheMixin(object):
  queue = "default"

  @property
  def value(self):
    raise NotImplementedError

  def get_origin(self):
    raise NotImplementedError

  def is_expired(self, expire=None):
    if expire is None:
      expire = str(time.time()).split(".", 1)[0]
    return self.expire <= expire

  def store_origin(self):
    self.get_origin()
    self.put()

  @staticmethod
  def get_key_name(*argv):
    key = "".join((str(i) for i in argv))
    if not 22 >= len(key) > 0:
      digest = hashlib.md5(key).digest()
      key = base64.urlsafe_b64encode(digest).replace("=", "")
    return key

  @classmethod
  @ndb.toplevel
  @ndb.synctasklet
  def for_async_store_origin(cls, key):
    entity = yield key.get_async()
    entity.store_origin()

  @classmethod
  def get_by_query(cls, query, queue=None):
    key_name = cls.get_key_name(*query)
    entity = cls.get_by_id(key_name)
    if queue is None:
      queue = cls.queue
    if entity is None:
      entity = cls.new(key_name, query)
      entity.put()
      deferred.defer(cls.for_async_store_origin, entity.key, _queue=queue)
    elif entity.is_expired():
      deferred.defer(cls.for_async_store_origin, entity.key, _queue=queue)
    return entity.value

  @classmethod
  def get_key_by_query(cls, query):
    return ndb.Key(cls, cls.get_key_name(*query))

  @classmethod
  def new(cls, key_name, query):
    return cls(key=ndb.Key(cls, key_name), queries=query)

class SitemapMixin(object):
  queue_name = tap.config.SITEMAP_QUEUE
  lastmod = None
  changefreq = None
  priority = None

  def _post_put_hook(self, future):
    self.sitemap_add_queue()

  @property
  def loc(self):
    return "http://{0}{1}".format(tap.config.URI_AUTHORITY, self.get_absolute_url())

  def get_absolute_url(self):
    raise NotImplementedError

  @staticmethod
  def to_sitemap_xml(loc, lastmod=None, changefreq=None, priority=None):
    elements = list()
    elements.append("<loc>{0}</loc>".format(tap.html_escape(loc)))
    if lastmod is None:
      lastmod = datetime.now()
    if lastmod is not False:
      elements.append("<lastmod>{0}</lastmod>".format(lastmod.strftime("%Y-%m-%d")))
    if changefreq is not None:
      elements.append("<changefreq>{0}</changefreq>".format(changefreq))
    if priority is not None:
      elements.append("<priority>{0}</priority>".format(priority))
    return "<url>{0}</url>".format("".join(elements))

  def sitemap_add_queue(self, payload=None):
    if payload is None:
      payload = self.to_sitemap_xml(self.loc, lastmod=self.lastmod, changefreq=self.changefreq, priority=self.priority)
    queue = taskqueue.Queue(self.queue_name)
    queue.add([taskqueue.Task(payload=payload, method="PULL", tag="url")])


# Model Classes

class CacheModelBase(CacheMixin):
  #key: query
  expire = ndb.ComputedProperty(lambda self: str(time.mktime((datetime.now() + timedelta(seconds=self.period)).timetuple())).split(".", 1)[0], indexed=False)
  period = ndb.IntegerProperty(default=2592000, indexed=False) #default: 30d
  queries = ndb.JsonProperty(required=True, indexed=False, compressed=True)


# View Decorators

def head(*packages):
  def decorator(func):
    @wraps(func)
    def inner(self, *argv, **kwargv):
      ndb.toplevel(func)(self, *argv, **kwargv)
      if self.response._app_iter is None:
        index = 0
      else:
        index = len(self.response._app_iter)
      self.response.write(AHEAD_HTML5)
      if len(packages):
        self.response.write(get_resource_code(packages))
        if self.response._app_iter is not None:
          self.response._app_iter = self.response._app_iter[index:] + self.response._app_iter[:index]
    return inner
  return decorator

def cache(period=None, expire=None, temporary=None, empty=False):
  if expire is not None and isinstance(expire, datetime):
    expire = time.mktime(expire.timetuple())

  def decorator(func):

    @wraps(func)
    @ndb.synctasklet
    def inner(self, *argv, **kwargv):
      if modules.get_current_module_name() != tap.config.BACKEND_NAME:
        cache = yield self.has_cache_async(expire, temporary=temporary)
        if cache:
          return
      ndb.toplevel(func)(self, *argv, **kwargv)
      if self.response.status_int == 200:
        if empty or len(self.response.body) > 0:
          self.put_cache(period, temporary=temporary)

    return inner

  return decorator

def cors(origin=None):

  def decorator(func):

    @wraps(func)
    def inner(self, *argv, **kwargv):
      ndb.toplevel(func)(self, *argv, **kwargv)
      if origin is None:
        allow_origin = self.request.headers.get("Origin")
        if allow_origin is None and self.request.referer:
          allow_origin = "{0}://{1}".format(*urlparse(self.request.referer)[:2])
      else:
        if callable(origin):
          allow_origin = origin()
      if allow_origin:
        self.response.headers["Access-Control-Allow-Origin"] = allow_origin
      if security.compare_hashes(self.request.method, "OPTIONS"):
        self.response.headers["Access-Control-Max-Age"] = tap.config.CORS_Access_Control_Max_Age
        method = self.request.headers.get("Access-Control-Request-Method")
        if method:
          self.response.headers["Access-Control-Allow-Methods"] = method
        headers = self.request.headers.get("Access-Control-Request-Headers")
        if headers:
          self.response.headers["Access-Control-Allow-Headers"] = headers

    return inner

  return decorator

def csrf(func):
  namespace = "csrf"

  @wraps(func)
  @ndb.tasklet
  def inner(self, *argv, **kwargv):
    if security.compare_hashes(self.request.method, "GET"):
      token = uuid.uuid4().get_hex()
      with tap.on_namespace(namespace):
        ndb.get_context().memcache_set(token, "", time=tap.config.CSRF_TIME)
      self.context["csrf"] = token
    elif self.request.method in ("POST", "PUT", "DELETE"):

      def set_403():
        self.response.set_status(403, "Invalid CSRF token")
        self.response.write("<h1>Invalid CSRF token</h1>\n<p>Please reload the form page</p>\n")

      token = self.request.POST.get("csrf")
      if not token:
        set_403()
        return
      with tap.on_namespace(namespace):
        result = yield ndb.get_context().memcache_delete(token)
      if result != memcache.DELETE_SUCCESSFUL:
        set_403()
        return
    func(self, *argv, **kwargv)

  return inner

def rate_limit(rate, size, key=None, tag=None):

  def decorator(func):
    prefix = tag
    if prefix is None:
      prefix = ".".join((func.__module__, func.__name__))
    token_bucket = tap.TokenBucket(rate, size, prefix=prefix)

    @wraps(func)
    @ndb.tasklet
    def inner(self, *argv, **kwargv):
      token_buket_key = key
      if key is not None:
        if callable(key):
          token_buket_key = key(self)
      is_acceptable = yield token_bucket.is_acceptable_async(key=token_buket_key)
      if is_acceptable:
        func(self, *argv, **kwargv)
      else:
        self.error(403)

    return inner

  return decorator

def same_domain_referer(func):

  @wraps(func)
  @ndb.tasklet
  def inner(self, *argv, **kwargv):
    referer = self.request.referer
    if referer is not None and referer.startswith(self.request.host_url):
      func(self, *argv, **kwargv)
    else:
      self.error(401)

  return inner

def session(func):

  @wraps(func)
  def inner(self, *argv, **kwargv):
    self.set_session_store()
    try:
      ndb.toplevel(func)(self, *argv, **kwargv)
    finally:
      self.session_store.save_sessions(self.response)

  return inner

def session_read_only(func):

  @wraps(func)
  def inner(self, *argv, **kwargv):
    self.set_session_store()
    ndb.toplevel(func)(self, *argv, **kwargv)

  return inner

def login_required(func):

  @wraps(func)
  def inner(self, *argv, **kwargv):
    self.session_store = sessions.get_store(request=self.request)
    self.session_store.config["secret_key"] = tap.get_namespaced_secret_key(namespace_manager.get_namespace())
    user = self.users.get_current_user()
    if user is None:
      try:
        user = oauth.get_current_user()
      except oauth.InvalidOAuthTokenError as e:
        explanation = "invalid token"
      except oauth.OAuthRequestError as e:
        explanation = "invalid header"
      except oauth.OAuthServiceFailureError as e:
        explanation = "service failure"
      if user is None:
        logging.info(e)
        self.abort(401, explanation=explanation)
    func(self, *argv, **kwargv)

  return inner


# View Classes

class RequestHandler(webapp2.RequestHandler, GoogleAnalyticsMixin):
  context = {
    'DEBUG': tap.config.DEBUG,
    'ASSOCIATE_TAG': tap.config.ASSOCIATE_TAG,
    'MEDIA_URL': tap.config.MEDIA_URL,
    'IMAGE_URL': tap.config.IMAGE_URL,
    'CURRENT_VERSION_ID': os.environ.get('CURRENT_VERSION_ID'),
    'FEEDBACK_FORMKEY': tap.config.FEEDBACK_FORMKEY,
    "NULL_GETTEXT": lambda x:x,
    "URI_FOR": webapp2.uri_for,
  }
  default_language = "en"
  i18n = False
  i18n_redirect = False
  urlfetch_deadline = tap.MAX_URLFETCH_DEADLINE
  use_zipfile = False
  with_google_analytics_tracking = False

  def __init__(self, *argv, **kwargv):
    for method_name in METHOD_NAMES:
      method = getattr(self, method_name, None)
      if method:
        method = ndb.toplevel(method)
        setattr(self, method_name, method)
    super(RequestHandler, self).__init__(*argv, **kwargv)
    if self.use_zipfile:
      setattr(self.response, "flush", self._response_flush)
      setattr(self.response, "tell", self._response_tell)
    self.dispatch = tap.set_urlfetch_deadline(self.urlfetch_deadline)(self.dispatch)
    namespace = inspect.getmodule(self).__dict__.get(tap.NAMESPACE_KEY)
    if namespace is not None:
      self.dispatch = tap.in_namespace(namespace)(self.dispatch)
    self.context["USERS"] = self.users = Users(self)


  # for WebOb.Response

  def _response_flush(self):
    pass

  def _response_tell(self):
    if self.response._app_iter is None:
      return 0
    return sum([len(str(chunk)) for chunk in self.response._app_iter])


  @property
  def is_bot(self):
    return "bot" in self.request.headers.get("User-Agent", "").lower()

  @property
  def jinja2(self):
    if self.i18n:
      jinja2 = tap.new_jinja2()
      jinja2.environment.install_gettext_translations(self.translation)
      return jinja2
    else:
      return tap.jinja2()

  @property
  def language(self):
    return self.request.GET.get("l", self.default_language)

  @webapp2.cached_property
  def session(self):
    try:
      return self.session_store.get_session()
    except AttributeError:
      return

  def set_session_store(self):
    if not hasattr(self, "session_store"):
      self.session_store = sessions.get_store(request=self.request)
      self.session_store.config["secret_key"] = tap.get_namespaced_secret_key(namespace_manager.get_namespace())

  @property
  def translation(self):
    translation = get_translation("{0}.py".format(self.i18n_domain), (self.language,), True, None)
    translation.install(unicode=True, names=["gettext", "ngettext"])
    return translation

  def bang_redirector_for(self, key):
    return bang_redirector_for(key)

  def dispatch(self):
    is_featurephone = uamobile.is_featurephone(self.request.headers.get('User-Agent', ""))

    if is_featurephone:
      path_info = self.request.path_info
      if not path_info.endswith(".html"):
        if path_info.endswith("/"):
          path_info = "{0}index".format(path_info)
        if self.request.query_string:
          location = ".html?".join((path_info, self.request.query_string))
        else:
          location = "{0}.html".format(path_info)
        return self.redirect(location)

    if self.i18n:
      if self.i18n_redirect and not self.request.GET.get("l"):
        mofile_path = gettext.find("{0}.py".format(self.i18n_domain), localedir=tap.config.LOCALE_PATH,
            languages=webob.acceptparse.AcceptLanguage(self.request.headers.get("Accept-Language", "")))
        if mofile_path:
          language = mofile_path.split(tap.config.LOCALE_PATH, 1)[1].split(os.sep, 2)[1]
          if self.request.query_string:
            location = "{0}&l={1}".format(self.request.path_qs, language)
          else:
            location = "{0}?l={1}".format(self.request.path_qs, language)
          return self.redirect(location)
      else:
        self.set_session_store()
      self.translation

    try:
      super(RequestHandler, self).dispatch()
    except webob.exc.HTTPGone:
      self.error(410)
      message = _(u"Not found. Display the top page.")
    except apiproxy_errors.OverQuotaError:
      if self.is_bot:
        self.abort(503, headers=[("Retry-After", "86400")])
      self.response.set_status(500, "Status: 503 Service Unavailabl")
      message = _(u"Sorry, a server error has occurred. Display the top page.")
    except Exception as e:
      if tap.config.DEBUG:
        raise
      if self.is_bot or tap.config.DEBUG:
        self.abort(500)
      logging.error("{0}: {1}".format(e.__class__.__name__, e))
      tap.send_exception_report()
      self.error(500)
      message = _(u"Sorry, a server error has occurred. Display the top page.")
    else:
      if (200 <= self.response.status_int < 400
          and tap.config.GA_ACCOUNT
          and not self.is_bot
          and is_featurephone
          or self.with_google_analytics_tracking):
        self._google_analytics_tracking(account=tap.config.GA_ACCOUNT, debug=tap.config.DEBUG)
      return

    if is_featurephone:
      if zenhan:
        message = zenhan.z2he(message)
      message = message.encode("Shift_JIS", "xmlcharrefreplace")
      index = "/index.html"
      template_path = "tap/mob/error.xhtml"
    else:
      index = "/"
      template_path = "tap/error.html"
      self.i18n = True
      self.i18n_domain = "tap"
      self.response.write(AHEAD_HTML5)
      try:
        self.response.write(get_resource_code(("js.bootstrap.bootstrap",)))
      except ImportStringError:
        pass

    index_cache = self.get_cache(cache_key=index)
    if index_cache:
      self.response.write(message)
      self.from_blob(index_cache)
    else:
      self.render_response(template_path, featurephone=is_featurephone)

  def head(self, *argv, **kwargv):
    if hasattr(self, "get"):
      self.get(*argv, **kwargv)
      self.response.clear()
    else:
      self.error(405)

  @webapp2.cached_property
  def cache_key(self):
    query = "".join((self.request.host, self.request.path_info))
    if self.request.query_string:
      query = "?".join((query, self.request.query_string))
    return self.to_cache_key(query)

  @staticmethod
  def to_cache_key(query):
    assert isinstance(query, basestring)
    if 22 >= len(query) > 0:
      result = query
    else:
      result = base64.urlsafe_b64encode(hashlib.md5(query).digest()).replace("=", "")
    return result

  def get_cache(self, cache_key=None, expire=None, queue_name=None):
    if cache_key is None:
      cache_key = self.cache_key
    if queue_name is None:
      queue_name = "cache"
    while True:
      try:
        caches = taskqueue.Queue(queue_name).lease_tasks_by_tag(0, 1, cache_key)
      except taskqueue.TransientError:
        pass
      else:
        break
    if caches and (expire is None or expire < caches[0].name[:10]):
      result = caches[0].payload
    else:
      result = None
    return result

  @ndb.tasklet
  def get_caches_async(self, cache_key=None, temporary=None):
    if cache_key is None:
      cache_key = self.cache_key
    if temporary is None:
      while True:
        try:
          caches = taskqueue.Queue("cache").lease_tasks_by_tag(0, 1000, cache_key)
        except taskqueue.TransientError:
          pass
        else:
          raise ndb.Return(caches)
    else:
      cache = yield ndb.get_context().memcache_get(cache_key, use_cache=True)
      if cache is not None:
        raise ndb.Return([cache])

  @ndb.tasklet
  def has_cache_async(self, expire=None, temporary=None):
    caches = yield self.get_caches_async(temporary=temporary)
    if not caches:
      return
    cache = caches[-1]
    has_cache = False
    if temporary:
      has_cache = True
      self.from_blob(cache)
    else:
      queue = taskqueue.Queue("cache")
      now = time.mktime(datetime.now().timetuple())
      period = cache.name[:10]
      period_int = int(period)
      if (expire is None and now < period_int) or (expire > now < period_int):
        has_cache = True
        self.from_blob(cache.payload)
        name = "".join((period, get_random_string(3, string.printable[:62])))
        queue.add(taskqueue.Task(method="PULL", tag=cache.tag, payload=cache.payload, name=name))
      queue.delete_tasks(caches)
    if has_cache is True:
      raise ndb.Return(True)

  @staticmethod
  def unpack_blob(blob):
    try:
      return tap.loads(blob)
    except Exception as e:
      logging.error("{0}: {1}".format(e.__class__.__name__, e))

  def from_blob(self, blob):
    values = self.unpack_blob(blob)
    if values:
      for key, value in values.get("headerlist", list()):
        self.response.headers[str(key)] = str(value)
      self.response.write(values.get("body", ""))

  def put_cache(self, period=None, temporary=None):
    if temporary is None:
      if period is None:
        period = 0
      queue = taskqueue.Queue("cache")
      caches = queue.lease_tasks_by_tag(0, 1000, self.cache_key)
      name = "".join((str(int(time.time()) + period), get_random_string(3, string.printable[:62])))
      queue.add(taskqueue.Task(method="PULL", tag=self.cache_key, payload=self.blob, name=name))
      if caches:
        queue.delete_tasks(caches)
    else:
      kwargv = dict()
      if period is not None:
        kwargv["time"] = period
      ndb.get_context().memcache_set(self.cache_key, self.blob, use_cache=True, **kwargv)

  @property
  def blob(self):
    return self.to_blob(self.response.headerlist, self.response.body)

  @staticmethod
  def to_blob(headerlist, body):
    blob = dict(headerlist=[(k,v) for k,v in headerlist if not security.compare_hashes(k, "Content-Length")],
                body=body)
    return tap.dumps(blob)

  @tap.parse_vars("args")
  def render_response(self, *argv, **kwargv):
    body, headers = self.render_template(*argv, **kwargv)
    self.response.write(body)
    self.response.headers.update(headers)

  def render_template(self, template_path, dictionary=None, args=None, context=None,
                      mimetype="text/html", charset=None, featurephone=None):
    if dictionary is None:
      dictionary = dict()
    if args is not None:
      dictionary.update(args)
    if context is None:
      context = self.context
    for key, value in context.items():
      dictionary.setdefault(key, value)
    if self.i18n:
      dictionary["I18N"] = True
      dictionary["I18N_DOMAIN"] = self.i18n_domain
      dictionary["LANGUAGE"] = self.language
    if "self" in dictionary:
      del dictionary["self"]
    body = self.jinja2.render_template(template_path, **dictionary)
    if featurephone:
      charset = "Shift_JIS"
      mimetype = "application/xhtml+xml;charset=Shift_JIS"
      if zenhan:
        body = zenhan.z2he(body)
    if charset:
      body = body.encode(charset, "xmlcharrefreplace")
    headers = (("Content-Type", mimetype),)
    return body, headers

  def fetch_page_async(self, query, page=10, cursor_string=None, cursor=None, keys_only=False):
    if cursor_string is None:
      cursor_string = self.request.query_string
    return tap.fetch_page_async(query, page, cursor_string, cursor, keys_only)

  @ndb.synctasklet
  def proxy(self, url=None, payload=None, method=None, headers=None):
    if url is None:
      url = self.request.query_string
      if not url:
        self.abort(404)
    if payload is None:
      payload = self.request.body
    if method is None:
      method = self.request.method
    if headers is None:
      headers = self.request.headers
      del headers["Host"]
    kwargv = dict(
      url = url,
      payload = payload,
      method = method,
      headers = headers,
    )
    try:
      response = yield ndb.get_context().urlfetch(**kwargv)
    except urlfetch.InvalidURLError:
      self.abort(404)
    except urlfetch.Error:
      self.abort(502)
    if "content-length" in response.headers:
      del response.headers["content-length"]
    self.response.set_status(response.status_code)
    self.response.headers.update(response.headers)
    self.response.write(response.content)


# sitemap views

class Sitemap(RequestHandler):
  def get(self):
    cache = self.get_cache(cache_key=self.request.path_info, queue_name=tap.config.SITEMAP_QUEUE)
    if cache:
      self.from_blob(cache)
    else:
      self.error(410)

# Redirect service views

def bang_redirector_for(key):
  try:
    return webapp2.uri_for("bang-redirector", key=key, _full=True).replace("/%21", "/!", 1)
  except AssertionError:
    logging.info("tap.bang_redirector_for: Could not be retrieved URI for `{0}`.".format(key))
    raise

class BangRedirector(RequestHandler):
  _redirect_to = tap.config.BANG_REDIRECTOR

  def get(self, key):
    self.response.status_int = 301
    self.response.headers.add("Location", "".join((self._redirect_to, key)))

# dropbox proxy views

class DropboxProxy(RequestHandler):
  _dropbox_url_base = "https://dl.dropboxusercontent.com/u/{uid}/{domain}{path}"
  cache_time = 60 #1min
  dropbox_uid = tap.config.DROPBOX_PROXY_UID or ""

  @classmethod
  def __new__(cls, *argv, **kwargv):
    cls.get = cache(cls.cache_time)(cls.get)
    return super(DropboxProxy, cls).__new__(*argv, **kwargv)

  def get(self, path, domain):
    url = self._dropbox_url_base.format(uid=self.dropbox_uid, domain=domain, path=path)
    if url.endswith("/"):
      url = url + "index.html"
    self.proxy(url=url)
    if self.response.status_code >= 400:
      self.response.body = ""

# OAuth views

class OAuth(RequestHandler, SimpleAuthHandler):
  """Authentication handler for OAuth 2.0, 1.0(a) and OpenID."""
  """
  copy AuthHandler from simpleauth

  https://github.com/crhym3/simpleauth/blob/ed342a572b357bacd08ef4cea9fdee43716b3ce8/example/handlers.py
  ed342a572b357bacd08ef4cea9fdee43716b3ce8 (Oct 29, 2013)
  """

  OAUTH2_CSRF_STATE = True

  USER_ATTRS = {
    'facebook' : {
      'id'     : lambda id: ('avatar_url',
        'http://graph.facebook.com/{0}/picture?type=large'.format(id)),
      'name'   : 'name',
      'link'   : 'link'
    },
    'google'   : {
      'picture': 'avatar_url',
      'name'   : 'name',
      'profile': 'link'
    },
    'windows_live': {
      'avatar_url': 'avatar_url',
      'name'      : 'name',
      'link'      : 'link'
    },
    'twitter'  : {
      'profile_image_url': 'avatar_url',
      'screen_name'      : 'name',
      'link'             : 'link'
    },
    'linkedin' : {
      'picture-url'       : 'avatar_url',
      'first-name'        : 'name',
      'public-profile-url': 'link'
    },
    'linkedin2' : {
      'picture-url'       : 'avatar_url',
      'first-name'        : 'name',
      'public-profile-url': 'link'
    },
    'foursquare'   : {
      'photo'    : lambda photo: ('avatar_url', photo.get('prefix') + '100x100' + photo.get('suffix')),
      'firstName': 'firstName',
      'lastName' : 'lastName',
      'contact'  : lambda contact: ('email',contact.get('email')),
      'id'       : lambda id: ('link', 'http://foursquare.com/user/{0}'.format(id))
    },
    'openid'   : {
      'id'      : lambda id: ('avatar_url', '/img/missing-avatar.png'),
      'nickname': 'name',
      'email'   : 'link'
    }
  }

  @session
  def _auth_callback(self, *argv, **kwargv):
    return super(OAuth, self)._auth_callback(*argv, **kwargv)

  @session
  def _simple_auth(self, *argv, **kwargv):
    referer = self.request.referer
    if referer:
      self.session.add_flash(referer)
    return super(OAuth, self)._simple_auth(*argv, **kwargv)

  def _on_signin(self, data, auth_info, provider):
    for referer, _label in self.session.get_flashes():
      if referer:
        referer = referer.encode("utf-8")
        break
    else:
      referer = "/"
    UserClass = getattr(self.oauth_config, "User", User)
    if hasattr(self.oauth_config, "on_signin"):
      self.oauth_config.on_signin(self, data, auth_info, provider)
    else:
      UserClass(data, auth_info, provider).set_to_session(self.session)
    self.redirect(referer)

  @same_domain_referer
  @session
  def _signout(self):
    if hasattr(self.oauth_config, "on_signout"):
      self.oauth_config.on_signout(self)
    self.session.clear()
    self.redirect(self.request.referer or "/")

  def _callback_uri_for(self, provider):
    return self.uri_for('oauth_callback', provider=provider, _full=True)

  def _get_consumer_info_for(self, provider):
    return self.oauth_config.AUTH_CONFIG[provider]

  @webapp2.cached_property
  def oauth_config(self):
    try:
      oauth_config = webapp2.import_string("oauth_config.{0}".format(self.request.host.replace(":", "_")))
    except webapp2.ImportStringError:
      try:
        oauth_config = webapp2.import_string("oauth_config.{0}".format(self.request.host.split(":", 1)[0]))
      except webapp2.ImportStringError as e:
        logging.warning(e)
        from oauth_config import default as oauth_config
    return oauth_config

# admin console views

class ResponseCache(RequestHandler):
  angular = "js.angular.angular"
  bootstrap = "js.bootstrap.bootstrap"

  @head(angular, bootstrap)
  @csrf
  def get(self):
    template_args = list()
    host = self.request.GET.get("host", "")
    path = self.request.GET.get("path")
    if path:
      cache_key = self.to_cache_key("".join((host, path)))
      template_args.append(cache_key)
    app_id = app_identity.get_application_id()
    self.render_response("tap/response_cache.html",
                         args=template_args + [host, path, app_id])

  @head(angular, bootstrap)
  @csrf
  def post(self):
    template_args = list()
    host = self.request.GET.get("host", "")
    path = self.request.GET.get("path")
    if path:
      cache_key = self.to_cache_key("".join((host, path)))
      template_args.append(cache_key)
      queue = taskqueue.Queue("cache")
      while True:
        caches = queue.lease_tasks_by_tag(0, 1000, cache_key)
        if caches:
          queue.delete_tasks(caches)
        if len(caches) < 1000:
          break
    app_id = app_identity.get_application_id()
    message = "Deleted the key from caches."
    self.render_response("tap/response_cache.html",
                         args=template_args + [host, path, app_id, message])


# i18n.js views

class I18Njs(RequestHandler):
  @cache(60)
  def get(self, domain, language):
    translation = get_translation("{0}.js".format(domain), (language,), False, "json")
    self.render_response("tap/i18n_js.html", args=[translation], mimetype="text/javascript")


# cron job views

class GenerateSitemap(RequestHandler):
  def get(self):
    head = "<?xml version='1.0' encoding='UTF-8'?>\n"
    urlset_head = "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
    urlset_tail = "</urlset>"
    urlset = list()
    sitemapindex_head = "<sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
    sitemapindex_tail = "</sitemapindex>"
    sitemapindex = list()
    sitemap_queue = taskqueue.Queue(tap.config.SITEMAP_QUEUE)
    while True:
      urls = sitemap_queue.lease_tasks_by_tag(lease_seconds=600, max_tasks=1000, tag="url")
      for url in urls:
        urlset.append(url.payload)
      if urls:
        sitemap_queue.delete_tasks(urls)
      if len(urls) < 1000:
        break
    if urlset:
      urlset[0:0] = [head, urlset_head]
      urlset.append(urlset_tail)
      blob = self.to_blob(headerlist=[("Content-Type", "text/xml")], body="".join(urlset))
      sitemap = "/sitemap_{0}.xml".format(datetime.now().strftime("%Y%m%d-%H%M%S"))
      sitemap_queue.add(taskqueue.Task(method="PULL", tag=sitemap, payload=blob))
      sitemapindex.append("<sitemap><loc>http://{0}{1}</loc></sitemap>".format(tap.config.URI_AUTHORITY, sitemap))
    if sitemapindex:
      sitemapindex_tag = "/sitemapindex.xml"
      sitemapindexs = sitemap_queue.lease_tasks_by_tag(0, 1000, sitemapindex_tag)
      if sitemapindexs:
        sitemapindex.insert(0, self.unpack_blob(sitemapindexs[-1].payload)["body"].rsplit(sitemapindex_tail, 1)[0])
      else:
        sitemapindex[0:0] = [head, sitemapindex_head]
      sitemapindex.append(sitemapindex_tail)
      blob = self.to_blob(headerlist=[("Content-Type", "text/xml")], body="".join(sitemapindex))
      sitemap_queue.add(taskqueue.Task(method="PULL", tag=sitemapindex_tag, payload=blob))
      sitemap_queue.delete_tasks(sitemapindexs)
    self.response.write("OK")

class MaintainResponse(RequestHandler):
  def get(self):
    queue = taskqueue.Queue("cache")
    statistics = queue.fetch_statistics()
    delete_count = statistics.tasks - tap.config.RESPONSE_CACHE_SIZE
    count = 0
    while delete_count > 0:
      max_tasks = delete_count if delete_count < 1000 else 1000
      tasks = queue.lease_tasks(0, max_tasks)
      tasks_len = len(tasks)
      queue.delete_tasks(tasks)
      count += tasks_len
      delete_count -= tasks_len
    message = "MaintainResponse: {0} entities deleted".format(count)
    logging.info(message)
    self.response.write(message + "<br>")
    self.response.write("OK")

class MaintainCacheBase(RequestHandler):
  query = None

  def get(self):

    def callback(entity):
      if entity.is_expired():
        try:
          entity.store_origin()
        except Exception as e:
          logging.error("{0}: {1}, {2}".format(e.__class__.__name__, entity.key.id(), e))
        else:
          return entity.key

    count = 0
    limit = 1024
    try:
      message = "MaintainCache: query is {0}".format(self.query)
      logging.info(message)
      self.response.write(message + "<br>")
      while count < 1024:
        try:
          results = self.query.map(callback, limit=limit)
        except apiproxy_errors.OverQuotaError:
          if limit == 1:
            break
          limit = limit / 2
        else:
          if results:
            count += len(filter(lambda x: x is not None, results))
          else:
            break
    except Exception as e:
      logging.error("{0}: {1}".format(e.__class__.__name__, e))
    finally:
      message = "MaintainCache: {0} entities updated".format(count)
      logging.info(message)
      self.response.write(message + "<br>")
    self.response.write("OK")


# static root

def make_zip_handler(zipfilename):

  class ZipHandler(zipserve.ZipHandler):
    def get(self, name):
      name = "static_root/{0}/{1}".format(self.request.host.split(":", 1)[0], name)
      self.ServeFromZipFile(zipfilename, name)

  return ZipHandler

@tap.execute_once
def get_static_root():
  routes_list = [("/(.*)", make_zip_handler("static_root.zip"))]
  return webapp2.WSGIApplication(routes=routes_list, debug=tap.config.DEBUG)


# Applications

app_static_root = get_static_root()


# Google Visualization API

class AppEngineHttpClientPatch(object):
  @ndb.synctasklet
  def request(self, operation, url, data=None, headers=None):
    all_headers = self.headers.copy()
    if headers:
      all_headers.update(headers)
    data_str = data
    if data:
      if isinstance(data, list):
        converted_parts = [gdata.alt.appengine._convert_data_part(x) for x in data]
        data_str = ''.join(converted_parts)
      else:
        data_str = gdata.alt.appengine._convert_data_part(data)
    if data and 'Content-Length' not in all_headers:
      all_headers['Content-Length'] = str(len(data_str))
    if 'Content-Type' not in all_headers:
      all_headers['Content-Type'] = 'application/atom+xml'
    if operation is None:
      method = None
    elif security.compare_hashes(operation, 'GET'):
      method = urlfetch.GET
    elif security.compare_hashes(operation, 'POST'):
      method = urlfetch.POST
    elif security.compare_hashes(operation, 'PUT'):
      method = urlfetch.PUT
    elif security.compare_hashes(operation, 'DELETE'):
      method = urlfetch.DELETE
    else:
      method = None
    result = yield ndb.get_context().urlfetch(url=str(url), payload=data_str,
        method=method, headers=all_headers, follow_redirects=False,
        deadline=self.deadline)
    raise ndb.Return(gdata.alt.appengine.HttpResponse(result))

if gdata:
  class AppEngineHttpClient(AppEngineHttpClientPatch, gdata.alt.appengine.AppEngineHttpClient):
    pass

class GoogleVisualization(object):
  """
  https://developers.google.com/chart/interactive/docs/querylanguage
  """

  _endpoint = "https://spreadsheets.google.com/tq"

  def __init__(self, username=None, password=None, key=None):
    if key is not None:
      self.key = key
    self.client = SpreadsheetsService(email=username, password=password)
    self.client.http_client = AppEngineHttpClient()
    if username and password:
      self.client.ProgrammaticLogin()

  def _converter(self, raw):
    logging.debug("GoogleVisualization._converter: raw is below.\n{0}".format(raw))
    s = RE_JS_Comments.sub("", RE_JS_MultiLineComments.sub("", raw))
    data = s[s.find("{"):s.rfind("}")+1]
    try:
      return json.loads(data)
    except ValueError as e:
      message = "GoogleVisualization._converter: data is below.\n{0}".format(data)
      logging.warning(message)
      if tap.config.IS_TEST:
        print(message)
      raise e

  def query(self, query_string, key=None):
    uri = "?".join((self._endpoint, urllib.urlencode({"key": key or self.key, "tq": query_string})))
    result = self.client.GetWithRetries(uri, converter=self._converter, logger=logging.getLogger())
    if security.compare_hashes(result["status"], "error"):
      logging.error(result["errors"])
      return
    cols = tuple([col["label"] or col["id"] for col in result["table"]["cols"]])
    for row in result["table"]["rows"]:
      yield dict(zip(cols, [c["v"] for c in row["c"]]))
