#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import unittest

import pytest

import tests.util
import tap

from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from minimock import mock, restore

class TestRingBuffer(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  @ndb.toplevel
  @ndb.synctasklet
  def test(self):
    with pytest.raises(ValueError):
      tap.RingBuffer(tag="tag", size=0)
    with pytest.raises(ValueError):
      tap.RingBuffer(tag="tag", size=1000)
    tap.RingBuffer(tag="tag", size=999)

    buf = tap.RingBuffer(tag="tag")
    assert list(buf.get()) == []
    self.execute_tasks("default")
    yield buf.clear()
    buf.put()
    self.execute_tasks("default")
    assert list(buf.get()) == []
    self.execute_tasks("default")
    buf.put(0)
    self.execute_tasks("default")
    buf.put(1, 2)
    self.execute_tasks("default")
    assert list(buf.get()) == [2, 1, 0]
    self.execute_tasks("default")

    queue = taskqueue.Queue("ringbuffer")
    buf = tap.RingBuffer(tag="tag", size=1)
    assert list(buf.get()) == [2]
    assert queue.fetch_statistics().tasks == 3
    assert [tap.loads(task.payload) for task in queue.lease_tasks(0, 1000)] == [0, 1, 2]
    self.execute_tasks("default")
    assert queue.fetch_statistics().tasks == 1
    assert list(buf.get()) == [2]
    self.execute_tasks("default")
    yield buf.clear()
    assert queue.fetch_statistics().tasks == 0
    assert list(buf.get()) == []
    self.execute_tasks("default")

    cache = buf._get._cache
    key = buf._get._key
    args = (buf.queue_name, buf.tag, buf.size)
    yield tap.memoize_clear(cache, key, args, use_memcache=True)

class TestTransientError(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def setUp(self):
    super(TestTransientError, self).setUp()
    mock("taskqueue.Queue.lease_tasks_by_tag", raises=taskqueue.TransientError)

  def tearDown(self):
    restore()
    super(TestTransientError, self).tearDown()

  def test(self):
    args = ("ringbuffer", "tag", "999")
    assert list(tap.RingBuffer(tag="tag")._get._func(*args)) == []
