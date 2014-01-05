#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import tests.util

from google.appengine.api import urlfetch_stub
from minimock import mock, restore

import conf

def Dummy_RetrieveURL(self, url, payload, method, headers, request, response,
                      follow_redirects, deadline, validate_certificate):
  response.set_statuscode(404)
  header_proto = response.add_header()
  header_proto.set_key("content-length")
  header_proto.set_value("0")

class DropboxProxyTest(tests.util.TestCase):
  root_path = conf.root_path

  def setUp(self):
    super(DropboxProxyTest, self).setUp()
    mock("urlfetch_stub.URLFetchServiceStub._RetrieveURL", mock_obj=Dummy_RetrieveURL)

  def tearDown(self):
    restore()
    super(DropboxProxyTest, self).tearDown()

  def test_dropbox_proxy(self):
    self.app.get("http://example.com/", status=404)
