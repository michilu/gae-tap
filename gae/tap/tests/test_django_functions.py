#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

import tests.util
import tap.ext
import tap.utils

import pytest

class TestDjangoFunctions(unittest.TestCase):
  def test_salted_hmac(self):
    assert tap.utils.salted_hmac("A", "B").hexdigest() == "ac954315453e48bf2b2e92988b1fefe5ffb2cdc8"

  def test_get_random_string(self):
    assert len(tap.ext.get_random_string()) == 12
