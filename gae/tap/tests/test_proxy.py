#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.util

from google.appengine.api import urlfetch, urlfetch_stub
from minimock import mock, restore

import conf

def Dummy_RetrieveURL(self, url, payload, method, headers, request, response,
                      follow_redirects, deadline, validate_certificate):
  response.set_statuscode(200)
  header_proto = response.add_header()
  header_proto.set_key("content-length")
  header_proto.set_value("0")

class ProxyTest(tests.util.TestCase):
  root_path = conf.root_path

  def setUp(self):
    super(ProxyTest, self).setUp()
    mock("urlfetch_stub.URLFetchServiceStub._RetrieveURL", mock_obj=Dummy_RetrieveURL)

  def tearDown(self):
    restore()
    super(ProxyTest, self).tearDown()

  def test_proxy(self):
    self.app.get("/test/proxy", status=404)
    self.app.get("/test/proxy?http://test")

  def test_proxy_invalid_url(self):
    self.app.get("/test/proxy?test", status=404)
    self.expected_logs = [
      ('ERROR', 'google/appengine/api/urlfetch_stub.py', '_Dynamic_Fetch', 'Invalid protocol: '),
      ('WARNING', 'google/appengine/ext/ndb/tasklets.py', '_help_tasklet_along', 'suspended generator urlfetch(context.py:...) raised InvalidURLError(Invalid request URL: test)')
    ]

class ProxyErrorTest(tests.util.TestCase):
  root_path = conf.root_path

  def setUp(self):
    super(ProxyErrorTest, self).setUp()
    mock("urlfetch.make_fetch_call", raises=urlfetch.Error)

  def tearDown(self):
    restore()
    super(ProxyErrorTest, self).tearDown()

  def test(self):
    self.app.get("/test/proxy?http://test", status=502)
    self.expected_logs = [
        ('WARNING', 'google/appengine/ext/ndb/tasklets.py', '_help_tasklet_along', 'initial generator urlfetch(context.py:...) raised Error()')
    ]
