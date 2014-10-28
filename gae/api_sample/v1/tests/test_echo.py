# -*- coding: utf-8 -*-

import tests.util

import endpoints

from .. import api

class APITest(tests.util.TestCase):
  application = api

  def test(self):
    response = self.app.post_json(self.endpoints_uri("Echo.echo"), {
      "message": "hello",
    })
    assert response.json["message"] == "hello"
