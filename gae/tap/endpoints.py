from google.appengine.api import (
  namespace_manager,
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
