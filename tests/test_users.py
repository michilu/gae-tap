#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import unittest

import pytest

import tests.util
import utils

class UserTest(unittest.TestCase):
  def test_user(self):
    user = utils.User()
    with pytest.raises(AssertionError):
      user.user_id()
    user = utils.User(data={"id": u"ID", u"locale": u"ja"}, provider="google")
    assert user._provider is None
    assert user.nickname() is None
    assert user.email() is None
    assert user.user_id() == u"google:ID"
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
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"
  use_cookie = True

  def test_users(self):
    self.app.post("/test/users")
    self.app.get("/test/users")
