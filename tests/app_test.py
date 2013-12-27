from random import random
import zipfile
import utils

from google.appengine.api import namespace_manager
from google.appengine.ext import ndb
from google.appengine.runtime import apiproxy_errors
import webapp2

class Model(ndb.Model):
  pass

class FetchPage(utils.RequestHandler):
  def get(self):
    self.fetch_page_async(Model.query())

class Translation(utils.RequestHandler):
  i18n = True
  i18n_domain = "sample"
  i18n_redirect = True

  def get(self):
    i18n_ = _("Python")
    i18n_gettext = gettext("Anaconda")
    self.render_response("sample.html", locals())

class ForMobile(utils.RequestHandler):
  @utils.cache(60)
  def get(self):
    ndb.get_context().memcache_get("sample")
    self.render_response("sample.html", locals(), featurephone=True)

class OverQuotaError(utils.RequestHandler):
  def get(self):
    raise apiproxy_errors.OverQuotaError

class InternalServerError(utils.RequestHandler):
  def get(self):
    assert False

class Head(utils.RequestHandler):
  @utils.head()
  def get(self):
    self.response._app_iter = []

class CORS(utils.RequestHandler):
  @utils.cors()
  def options(self):
    pass

  @utils.cors(origin=lambda:"test")
  def get(self):
    pass

rate_limit = utils.rate_limit(rate=1, size=2, key=lambda self: self.request.remote_addr, tag="RateLimit")
class RateLimit(utils.RequestHandler):
  @rate_limit
  def get(self):
    pass

  @rate_limit
  def post(self):
    pass

  @utils.rate_limit(rate=1, size=1)
  def put(self):
    pass

class CacheTemporary(utils.RequestHandler):
  @utils.cache(temporary=True)
  def get(self):
    self.response.write(random())

class Proxy(utils.RequestHandler):
  def get(self):
    self.proxy()

class Sessions(utils.RequestHandler):
  def get(self):
    assert self.session is None

  @utils.session_read_only
  def post(self):
    self.session["TEST"] = "POST"

  @utils.session
  def put(self):
    self.session["TEST"] = "PUT"

  @utils.session
  def delete(self):
    self.session["TEST"] = "DELETE"

class Users(utils.RequestHandler):
  @utils.session_read_only
  def get(self):
    assert self.users.create_login_url() == "/oauth/google"
    assert self.users.create_logout_url() == "/oauth/signout"
    user = self.users.get_current_user()
    assert user is not None
    assert user.user_id() == u"ID"
    assert getattr(user, "locale", None) is None

  @utils.session
  def post(self):
    assert utils.User.load_from_session(self.session) is None
    user = utils.User(data={"id": u"ID", u"locale": u"ja"})
    assert user is not None
    user.set_to_session(self.session)

class Namespace(utils.RequestHandler):
  def get(self):
    self.response.write(namespace_manager.get_namespace())

class ZipFile(utils.RequestHandler):
  use_zipfile = True

  def get(self):
    assert self.response.tell() == 0
    writer = zipfile.ZipFile(self.response, "w")
    writer.writestr("zinfo_or_arcname", b"test")
    writer.close()
    assert self.response.tell() == 134

routes = [
  webapp2.Route("/fetch_page", FetchPage),
  webapp2.Route("/translation", Translation),
  webapp2.Route("/index.html", ForMobile),
  webapp2.Route("/test.html", OverQuotaError),
  webapp2.Route("/error.html", InternalServerError),
  webapp2.Route("/head", Head),
  webapp2.Route("/cors", CORS),
  webapp2.Route("/rate_limit", RateLimit),
  webapp2.Route("/cache_temporary", CacheTemporary),
  webapp2.Route("/proxy", Proxy),
  webapp2.Route("/sessions", Sessions),
  webapp2.Route("/users", Users),
  webapp2.Route("/namespace", Namespace),
  webapp2.Route("/zipfile", ZipFile),
]
