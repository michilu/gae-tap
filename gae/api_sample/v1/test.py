# -*- coding: utf-8 -*-

import tests.util

import endpoints

import api_sample.v1

class APITest(tests.util.TestCase):
  application = api_sample.v1.api

  def test(self):
    response = self.app.post_json(self.endpoints_uri("Echo.echo"), {
      "message": "hello",
    })
    assert response.json["message"] == "hello"
