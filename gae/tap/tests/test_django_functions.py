#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

import tests.util
import tap
import tap.utils

import pytest

class TestDjangoFunctions(unittest.TestCase):
  def test_salted_hmac(self):
    assert tap.utils.salted_hmac("A", "B").hexdigest() == "ac954315453e48bf2b2e92988b1fefe5ffb2cdc8"

  def test_get_random_string(self):
    assert len(tap.get_random_string()) == 12

  @pytest.mark.skipif("tap.using_sysrandom == False")
  def test_get_random_string_2(self):
    import random
    origin_using_sysrandom = tap.using_sysrandom
    origin_random = tap.random
    tap.using_sysrandom = False
    tap.random = random
    try:
      assert len(tap.get_random_string()) == 12
    finally:
      tap.using_sysrandom = origin_using_sysrandom
      tap.random = origin_random
