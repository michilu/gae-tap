from __future__ import absolute_import

from functools import wraps
import os
import string

from google.appengine.api import (
  namespace_manager,
  oauth,
)
from google.appengine.ext import ndb

from protorpc import remote
from webapp2_extras import sessions
import webob

# Google Cloud Endpoints

def get_user_from_endpoints_service(endpoints_service):
  import tap
  request_state = endpoints_service.request_state
  request_state.app = tap.get_app()
  request_state.cookies = webob.request.RequestCookies({
    "HTTP_COOKIE": request_state.headers.get("cookie"),
  })
  session_store = sessions.SessionStore(request_state)
  session_store.config["secret_key"] = tap.get_namespaced_secret_key(namespace_manager.get_namespace())
  return tap.User.load_from_session(session_store.get_session())

def get_user_id_from_endpoints_service(raises=True):
  import tap
  import endpoints
  current_user = endpoints.get_current_user()
  if current_user is None:
    if raises:
      raise endpoints.UnauthorizedException()
    else:
      return
  user_id = current_user.user_id()

  # for dev_appserver
  # http://stackoverflow.com/questions/16661109
  if user_id is None:
    oauth_user = oauth.get_current_user(os.getenv("OAUTH_LAST_SCOPE"))
    if oauth_user is None or oauth_user.user_id() is None:
      if raises:
        raise endpoints.UnauthorizedException()
      else:
        return
    user_id = oauth_user.user_id()

  return user_id

class CRUDServiceClass(remote._ServiceClass):

  @staticmethod
  def __add_prefix(name, dct):
    new_dct = dict()
    for key, value in dct.iteritems():
      if not key.startswith("_"):
        key = "_{0}_{1}".format(name, key)
      new_dct[key] = value
    return new_dct

  def __new__(cls, name, bases, dct):
    new_dct = CRUDServiceClass.__add_prefix(name, dct)
    return super(CRUDServiceClass, cls).__new__(cls, name, bases, new_dct)

  def __init__(cls, name, bases, dct):
    new_dct = CRUDServiceClass.__add_prefix(name, dct)
    super(CRUDServiceClass, cls).__init__(name, bases, new_dct)

class CRUDService(remote.Service):

  __metaclass__ = CRUDServiceClass

def get_user_id(_self=None):
  import tap
  user_id = get_user_id_from_endpoints_service()
  return tap.base62_encode(int(user_id))

def rate_limit(rate, size, key=None, tag=None):
  import tap
  import endpoints

  def decorator(func):
    prefix = tag
    if prefix is None:
      prefix = ".".join((func.__module__, func.__name__))
    token_bucket = tap.TokenBucket(rate, size, prefix=prefix)

    @wraps(func)
    @ndb.synctasklet
    def inner(self, *argv, **kwargv):
      token_buket_key = key
      if key is not None:
        if callable(key):
          token_buket_key = key(self)
      is_acceptable = yield token_bucket.is_acceptable_async(key=token_buket_key)
      if is_acceptable:
        raise ndb.Return(func(self, *argv, **kwargv))
      else:
        raise endpoints.ForbiddenException("Too many requests")

    return inner

  return decorator
