from __future__ import absolute_import

import os
import string

from google.appengine.api import (
  namespace_manager,
  oauth,
)

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

  def _get_user(self):
    return get_user_from_endpoints_service(self)

  def _get_user_key_id(self):
    import tap
    user_key_id =  get_user_id_from_endpoints_service()
    return tap.base62_encode(int(user_key_id))
