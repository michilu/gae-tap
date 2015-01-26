import webapp2

from . import app

prefixed = lambda s: "{0}.app.{1}".format(__package__, s)

routes = [
  webapp2.Route("/", prefixed("Index")),
  webapp2.Route("/index.html", app.ForMobile),
]
