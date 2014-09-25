#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

import tests.util
import tap

from google.appengine.api import taskqueue
from google.appengine.ext import ndb

import conf

class TestQueue(tests.util.TestCase):
  root_path = conf.root_path

  @ndb.toplevel
  @ndb.synctasklet
  def test(self):
    queue = tap.Queue(tag="tag")
    assert list(queue.collect()) == []
    self.execute_tasks("default")
    queue.put()
    self.execute_tasks("default")
    assert list(queue.collect()) == []
    self.execute_tasks("default")
    queue.put(0)
    self.execute_tasks("default")
    queue.put(1, 2)
    self.execute_tasks("default")
    assert list(queue.collect(lease_seconds=0)) == [0, 1, 2]
    self.execute_tasks("default")
