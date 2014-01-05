#!/usr/bin/env ipython -i
# -*- coding: utf-8 -*-

from functools import wraps
import os
import sys


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
  base_path = os.environ.get("SITE_PACKAGES", "site-packages")
  base_path = os.path.abspath(base_path)
  path = base_path
  if path not in sys.path and os.path.exists(path):
    sys.path.append(path)
  if os.path.exists(base_path):
    path = os.path.join(base_path, "packages")
    if path not in sys.path:
      sys.path.append(path)
    if os.path.exists(path):
      for zipfile in os.listdir(path):
        if zipfile.endswith(".zip"):
          zipfile_path = os.path.join(path, zipfile)
          if zipfile_path not in sys.path:
            sys.path.append(zipfile_path)
  import google
  base = os.path.join(os.path.dirname(google.__file__), "../lib/")
  for webapp2 in ["webapp2-2.5.2", "webapp2"]:
    path = os.path.join(base, webapp2)
    if os.path.exists(path):
      sys.path.append(path)
      break
  for path in ["endpoints-1.0", "protorpc-1.0", "jinja2"]:
    sys.path.append(os.path.join(base, path))
  return True
sys_path_append()

if __name__ == "__main__":
  try:
    get_ipython().magic("doctest_mode")
  except NameError:
    pass
