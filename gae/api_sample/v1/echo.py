from google.appengine.ext import ndb
import endpoints
import tap.endpoints

from . import api
from . import message

@api.api_class(resource_name="echo", path="echo")
class Echo(tap.endpoints.CRUDService):

  @endpoints.method(message.Echo, message.Echo)
  @ndb.toplevel
  @tap.endpoints.rate_limit(rate=50, size=50, key=lambda self:self.request_state.remote_address, tag="echo.api")
  def echo(self, request):
    raise ndb.Return(message.Echo(
      message = request.message,
    ))
