import utils

from google.appengine.api import namespace_manager
from js.bootstrap import bootstrap
import webapp2

class Index(utils.RequestHandler):
  i18n = True
  i18n_domain = "sample"

  @utils.head(bootstrap)
  def get(self, subdomain=None):
    self.render_response("sample.html", locals())

class Namespace(utils.RequestHandler):
  def get(self, subdomain=None):
    self.response.write(namespace_manager.get_namespace())

routes = [
  webapp2.Route("/", Index),
  webapp2.Route("/namespace", Namespace),
]
