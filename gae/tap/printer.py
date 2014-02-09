#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shell

import os
import sys

import webapp2

sys.path.append(os.curdir)
print(webapp2.import_string(sys.argv[1]))
