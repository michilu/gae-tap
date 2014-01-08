#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import tests.util

import conf

class SessionsTest(tests.util.TestCase):
  root_path = conf.root_path
  use_cookie = True

  def test_sessions(self):
    self.app.get("/test/sessions")
    assert len(self.app.cookiejar) == 0
    self.app.post("/test/sessions")
    assert len(self.app.cookiejar) == 0
    self.app.put("/test/sessions")
    assert len(self.app.cookiejar) == 1
    for cookie in self.app.cookiejar:
      if cookie.name == "__s":
        assert cookie.value is not None
        value = cookie.value
        break
      else:
        raise
    self.app.post("/test/sessions")
    assert len(self.app.cookiejar) == 1
    for cookie in self.app.cookiejar:
      if cookie.name == "__s":
        assert cookie.value is not None
        assert cookie.value == value
        break
      else:
        raise
    self.app.delete("/test/sessions")
    assert len(self.app.cookiejar) == 1
    for cookie in self.app.cookiejar:
      if cookie.name == "__s":
        assert cookie.value is not None
        assert cookie.value != value
        break
      else:
        raise
