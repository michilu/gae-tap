#!/usr/bin/env python
# -*- coding: utf-8 -*-

from doctest import testmod
import sys

import tests.util
import tap

if testmod(tap).failed:
  sys.exit(1)
