import webapp2

from . import app

routes = [
  webapp2.Route("/", app.Index),
  webapp2.Route("/index.html", app.ForMobile),
]
