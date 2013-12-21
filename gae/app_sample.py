from datetime import datetime

import utils

from google.appengine.ext import ndb

from js.angular import angular_cookies, angular_resource
from js.bootstrap import bootstrap
import webapp2

class Index(utils.RequestHandler):
  i18n = True
  i18n_domain = "sample"

  @utils.head(angular_cookies, angular_resource, bootstrap)
  @utils.cache(60, expire=datetime(2012, 1, 1))
  def get(self, subdomain=None):
    i18n_ = _("Python")
    i18n_gettext = gettext("Anaconda")
    self.render_response("sample.html", locals())

class ForMobile(utils.RequestHandler):
  @utils.cache(60)
  def get(self):
    yield ndb.get_context().memcache_get("sample")
    self.render_response("mob/sample.xhtml", locals(), featurephone=True)

routes = [
  webapp2.Route("/", Index),
  webapp2.Route("/index.html", ForMobile),
]
