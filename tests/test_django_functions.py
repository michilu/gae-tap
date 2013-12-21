#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

import tests.util
import utils

import pytest

class TestDjangoFunctions(unittest.TestCase):
  def test_salted_hmac(self):
    assert utils.salted_hmac("A", "B").hexdigest() == "ac954315453e48bf2b2e92988b1fefe5ffb2cdc8"
    assert utils.salted_hmac("A", "B", "C").hexdigest() == "07caa07de37ee6606843a99c898189e7ed90910a"

  def test_get_random_string(self):
    assert len(utils.get_random_string()) == 12

  @pytest.mark.skipif("utils.using_sysrandom == False")
  def test_get_random_string_2(self):
    import random
    origin_using_sysrandom = utils.using_sysrandom
    origin_random = utils.random
    utils.using_sysrandom = False
    utils.random = random
    try:
      assert len(utils.get_random_string()) == 12
    finally:
      utils.using_sysrandom = origin_using_sysrandom
      utils.random = origin_random

  def test_constant_time_compare(self):
    assert utils.constant_time_compare("A", "") == False
    assert utils.constant_time_compare("A", "B") == False
    assert utils.constant_time_compare("A", "A") == True
