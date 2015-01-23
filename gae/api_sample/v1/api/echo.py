# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import endpoints
import tap.endpoints

from .. import (
  api,
  define,
  message,
)

@api.api_class(resource_name="echo", path="echo")
class Echo(tap.endpoints.CRUDService):

  @endpoints.method(message.Echo, message.Echo)
  @ndb.toplevel
  @define.rate_limit
  def echo(self, request):
    raise ndb.Return(message.Echo(
      message = request.message,
    ))
