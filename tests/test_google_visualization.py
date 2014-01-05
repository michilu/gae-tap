#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import unittest

import atom.http
import atom.service
import pytest

import tests.util
import tap

from google.appengine.ext import ndb
from minimock import mock, restore

class AuthResponse(object):
  status = 200

  def read(self):
    return ""

class EndpointResponse(object):
  status = 200

  def read(self):
    return """google.visualization.Query.setResponse({"version":"0.6","reqId":"0","status":"ok","sig":"1766578678","table":{"cols":[{"id":"A","label":"","type":"string","pattern":""},{"id":"D","label":"Population Density","type":"number","pattern":"#0.###############"}],"rows":[{"c":[{"v":"Japan"},{"v":339.0,"f":"339"}]}]}});"""

class ErrorResponse(object):
  status = 200

  def read(self):
    return """google.visualization.Query.setResponse({"version":"0.6","status":"error","errors":[{"reason":"invalid_query","message":"Invalid query","detailed_message":"Query parse error: Encountered..."}]});"""

class TestGoogleVisualization(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def setUp(self):
    super(TestGoogleVisualization, self).setUp()
    mock("tap.AppEngineHttpClient.request", returns=AuthResponse())
    mock("atom.service.AtomService.request", returns=EndpointResponse())

  def tearDown(self):
    restore()
    super(TestGoogleVisualization, self).tearDown()

  def test(self):
    gv = tap.GoogleVisualization(username="username", password="password", key="dummy")
    assert isinstance(gv, tap.GoogleVisualization)
    assert list(gv.query("select *")) == [{u'A': u'Japan', u'Population Density': 339.0}]

    mock("atom.service.AtomService.request", returns=ErrorResponse())
    assert list(gv.query("select *")) == []
    self.expected_logs = [('ERROR', 'gae/tap/__init__.py', 'query', "[{u'reason': u'invalid_query', u'detailed_message': u'Query parse error: Encountered...', u'message': u'Invalid query'}]")]

  def test_converter(self):
    gv = tap.GoogleVisualization()
    assert gv._converter("// Data table response\ngoogle.visualization.Query.setResponse({});") == {}
    assert gv._converter("// Data table response\n/*\n*/\nconsole.log(/*//*/{});//)") == {}

  def test_converter_raises(self):
    gv = tap.GoogleVisualization()
    with pytest.raises(ValueError):
      assert gv._converter("") == {}
    self.expected_logs = [('WARNING', 'gae/tap/__init__.py', '_converter', 'GoogleVisualization._converter: data is below.\n')]

class UrlfetchResult(object):
  content = ""
  headers = dict()
  status_code = 200

@ndb.tasklet
def urlfetch(*argv, **kwargv):
  raise ndb.Return(UrlfetchResult())

class TestAppEngineHttpClient(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def setUp(self):
    super(TestAppEngineHttpClient, self).setUp()
    mock("ndb.context.Context.urlfetch", mock_obj=urlfetch)

  def tearDown(self):
    restore()
    super(TestAppEngineHttpClient, self).tearDown()

  def test(self):
    client = tap.AppEngineHttpClient()
    assert client.request("GET", "", data=list("TEST"), headers={"TEST": "TEST"})
    assert client.request("POST", "", data="TEST")
    assert client.request("PUT", "")
    assert client.request("DELETE", "")
    assert client.request(None, "")
