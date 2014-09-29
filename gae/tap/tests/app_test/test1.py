from datetime import datetime

from google.appengine.ext import ndb
import webapp2

import tap.ext

class Index(tap.ext.RequestHandler):
  i18n = True
  i18n_domain = "sample"

  @tap.ext.head("js.angular.angular_cookies", "js.angular.angular_resource", "js.bootstrap.bootstrap")
  @tap.ext.cache(60, expire=datetime(2012, 1, 1))
  def get(self, subdomain=None):
    i18n_ = _("Python")
    i18n_gettext = gettext("Anaconda")
    self.render_response("sample.html", locals())

class ForMobile(tap.ext.RequestHandler):
  @tap.ext.cache(60)
  def get(self):
    yield ndb.get_context().memcache_get("sample")
    self.render_response("mob/sample.xhtml", locals(), featurephone=True)

routes = [
  webapp2.Route("/", Index),
  webapp2.Route("/index.html", ForMobile),
]
