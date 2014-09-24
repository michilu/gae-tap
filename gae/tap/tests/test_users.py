#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

import pytest

import tests.util
import tap.ext

import conf

class UserTest(unittest.TestCase):
  def test_user(self):
    user = tap.ext.User()
    with pytest.raises(AssertionError):
      user.user_id()
    user = tap.ext.User(data={"id": u"ID", u"locale": u"ja"}, provider="google")
    assert user._provider is None
    assert user.nickname() is None
    assert user.email() is None
    assert user.user_id() == u"ID"
    user._provider = "test"
    assert user.user_id() == u"test:ID"
    assert user.locale == u"ja"
    with pytest.raises(AttributeError):
      user.gender
    with pytest.raises(AttributeError):
      del user.gender
    user.gender = "female"
    assert user.gender == "female"
    del user.gender
    with pytest.raises(AttributeError):
      user.gender
    del user._id

class UsersTest(tests.util.TestCase):
  root_path = conf.root_path
  use_cookie = True

  def test_users(self):
    self.app.post("/test/users")
    self.app.get("/test/users")

  def test_login_required(self):
    self.app.get("/test/login_required")
