#!/usr/bin/env python
# -*- coding: utf-8 -*-

from doctest import testmod
import sys

import tests.util
import utils

if testmod(utils).failed:
  sys.exit(1)
