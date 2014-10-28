from __future__ import absolute_import

from functools import wraps
import os
import string

from google.appengine.api import (
  namespace_manager,
  oauth,
)
from google.appengine.ext import (
  db,
  ndb,
)
from protorpc import (
  messages,
  remote,
)
from webapp2_extras import sessions
import endpoints
import webob

import tap

# Google Cloud Endpoints

def get_user_from_endpoints_service(endpoints_service):
  request_state = endpoints_service.request_state
  request_state.app = tap.get_app()
  request_state.cookies = webob.request.RequestCookies({
    "HTTP_COOKIE": request_state.headers.get("cookie"),
  })
  session_store = sessions.SessionStore(request_state)
  session_store.config["secret_key"] = tap.get_namespaced_secret_key(namespace_manager.get_namespace())
  return tap.User.load_from_session(session_store.get_session())

def get_user_id_from_endpoints_service(raises=True):
  current_user = endpoints.get_current_user()
  if current_user is None:
    if raises:
      raise endpoints.UnauthorizedException("Invalid token.")
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

def get_user_id(_self=None, raises=True):
  user_id = get_user_id_from_endpoints_service(raises)
  if user_id:
    return tap.base62_encode(int(user_id))

def get_user_id_or_ip(self=None):
  user_id = get_user_id_from_endpoints_service(raises=False)
  if user_id:
    return int(user_id)
  elif self:
    return self.request_state.remote_address

def rate_limit(rate, size, key=None, tag=None):

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
          if not isinstance(token_buket_key, basestring):
            token_buket_key = str(token_buket_key)
      is_acceptable = yield token_bucket.is_acceptable_async(key=token_buket_key)
      if is_acceptable:
        raise ndb.Return(func(self, *argv, **kwargv))
      else:
        raise endpoints.ForbiddenException("Too many requests")

    return inner

  return decorator

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

class ValidationError(endpoints.BadRequestException, messages.ValidationError, db.BadValueError, ValueError):
  pass

class EndpointsUserIDProperty(ndb.StringProperty):
  """A custom user property for interacting with user ID tokens.

  Uses the tools provided in the endpoints module to detect the current user.
  In addition, has an optional parameter raise_unauthorized which will return
  a 401 to the endpoints API request if a user can't be detected.
  """

  def __init__(self, *args, **kwargs):
    """Constructor for string property.

    NOTE: Have to pop custom arguments from the keyword argument dictionary
    to avoid corrupting argument order when sent to the superclass.

    Attributes:
      _raise_unauthorized: An optional boolean, defaulting to False. If True,
         the property will return a 401 to the API request if a user can't
         be deteced.
    """
    self._raise_unauthorized = kwargs.pop('raise_unauthorized', False)
    super(EndpointsUserIDProperty, self).__init__(*args, **kwargs)

  def _set_value(self, entity, value):
    """Internal helper to set value on model entity.

    If the value to be set is null, will try to retrieve the current user and
    will return a 401 if a user can't be found and raise_unauthorized is True.

    Args:
      entity: An instance of some NDB model.
      value: The value of this property to be set on the instance.
    """
    if value is None:
      value = get_user_id_from_endpoints_service(raises=self._raise_unauthorized)
    super(EndpointsUserIDProperty, self)._set_value(entity, value)

  def _fix_up(self, cls, code_name):
    """Internal helper called to register the property with the model class.

    Overrides the _set_attributes method on the model class to interject this
    attribute in to the keywords passed to it. Since the method _set_attributes
    is called by the model class constructor to set values, this -- in congress
    with the custom defined _set_value -- will make sure this property always
    gets set when an instance is created, even if not passed in.

    Args:
      cls: The model class that owns the property.
      code_name: The name of the attribute on the model class corresponding
          to the property.
    """
    original_set_attributes = cls._set_attributes

    def CustomSetAttributes(setattr_self, kwds):
      """Custom _set_attributes which makes sure this property is always set."""
      if self._code_name not in kwds:
        kwds[self._code_name] = None
      original_set_attributes(setattr_self, kwds)

    cls._set_attributes = CustomSetAttributes
    super(EndpointsUserIDProperty, self)._fix_up(cls, code_name)
