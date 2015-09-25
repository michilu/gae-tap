#!/usr/bin/env ipython -i
# -*- coding: utf-8 -*-

from functools import wraps
import os
import sys

from IPython import get_ipython

get_ipython().magic("%doctest_mode")

# Search Path

def execute_once(func):

  @wraps(func)
  def inner(_result=[None], *argv, **kwargv):
    if _result[0] is None:
      _result[0] = func(*argv, **kwargv)
      if _result[0] is None:
        raise ValueError("The return value must be not `None`.")
    return _result[0]

  return inner

@execute_once
def sys_path_append():
  import google
  base = os.path.join(os.path.dirname(google.__file__), "../lib/")
  for webapp2 in ["webapp2-2.5.2"]:
    path = os.path.join(base, webapp2)
    if os.path.exists(path):
      sys.path.insert(0, path)
      break
  else:
    raise
  for path in ["django-1.5", "endpoints-1.0", "protorpc-1.0", "jinja2-2.6"]:
    path = os.path.join(base, path)
    if os.path.exists(path):
      sys.path.insert(0, path)
    else:
      raise
  return True
sys_path_append()

try:
  import warmup
except ImportError:
  import tap.warmup

import tap
