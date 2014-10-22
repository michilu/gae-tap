#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.util

import conf

import endpoints

from api_test.v1 import api

class ApiTest(tests.util.TestCase):
  application = api
  root_path = conf.root_path

  def test(self):
    response = self.app.post_json(self.endpoints_uri("Echo.echo"), {
      "message": "hello",
    })
    assert response.json["message"] == "hello"

  def test_with_oauth(self):
    self.endpoints_via_oauth("user@localhost")
    assert endpoints.get_current_user().user_id() == "371373237938074"
