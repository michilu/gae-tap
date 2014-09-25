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
  if base_path not in sys.path and os.path.exists(base_path):
    sys.path.append(base_path)
  if os.path.exists(base_path):
    packages_path = os.path.join(base_path, "packages")
    if packages_path not in sys.path:
      sys.path.append(packages_path)
    if os.path.exists(packages_path):
      for zipfile in os.listdir(packages_path):
        if zipfile.endswith(".zip"):
          zipfile_path = os.path.join(packages_path, zipfile)
          if zipfile_path not in sys.path:
            sys.path.append(zipfile_path)
  return True
sys_path_append()


@execute_once
def warmup():
  import webapp2
  return webapp2.WSGIApplication([
    ("/_ah/warmup", lambda request: None),
  ])

app = warmup()
