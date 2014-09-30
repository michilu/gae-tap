import tap.ext

from google.appengine.api import namespace_manager
import webapp2

class Index(tap.ext.RequestHandler):
  i18n = True
  i18n_domain = "sample"

  @tap.ext.head("js.bootstrap.bootstrap")
  def get(self, subdomain=None):
    self.render_response("sample.html", locals())

class Namespace(tap.ext.RequestHandler):
  def get(self, subdomain=None):
    self.response.write(namespace_manager.get_namespace())

routes = [
  webapp2.Route("/", Index),
  webapp2.Route("/namespace", Namespace),
]
