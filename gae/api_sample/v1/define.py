# -*- coding: utf-8 -*-

import sys

from google.appengine.api import (
  lib_config,
  taskqueue,
)

import tap.endpoints

class Defaults(object):
  rate_limit  = tap.endpoints.rate_limit(rate=100, size=100, key=lambda self:self.request_state.remote_address, tag="echo.api")
  queue       = taskqueue.Queue("queue")

sys.modules[__name__] = lib_config.register("echo", Defaults.__dict__)
