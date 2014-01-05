#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import cPickle as pickle
import os
import re
import unittest
import urlparse
import zlib

from google.appengine.api import taskqueue
import pytest

import tests.util
from tap import SitemapMixin
import tap

class Sitemap(tap.SitemapMixin):
  changefreq = "daily"
  priority = 0.5

  def get_absolute_url(self):
    return "/loc"

class TestSitemapMixin(unittest.TestCase):
  def test_sitemap_to_xml(self):
    assert SitemapMixin.to_sitemap_xml("http://example.com", False) == "<url><loc>http://example.com</loc></url>"
    assert SitemapMixin.to_sitemap_xml("http://example.com").startswith("<url><loc>http://example.com</loc><lastmod>")
    assert "<lastmod>2012-01-01</lastmod>" in SitemapMixin.to_sitemap_xml("http://example.com", datetime(2012,1,1))
    assert "<changefreq>daily</changefreq>" in SitemapMixin.to_sitemap_xml("http://example.com", False, "daily")
    assert "<priority>1.0</priority>" in SitemapMixin.to_sitemap_xml("http://example.com", False, priority=1.0)

  def test_sitemap_escaping(self):
    """ http://www.sitemaps.org/protocol.html#escaping
    """
    assert SitemapMixin.to_sitemap_xml("http://example.com/&\'\"><", False) == "<url><loc>http://example.com/&amp;&apos;&quot;&gt;&lt;</loc></url>"

  def test_attributes(self):
    with pytest.raises(NotImplementedError):
      SitemapMixin().loc

class AppTest(tests.util.TestCase):
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"

  def test_sitemapindex(self):
    self.app.get("/sitemapindex.xml", status=410)

    Sitemap()._post_put_hook(None)
    self.app.get("/_tap/generate_sitemap")

    response = self.app.get("/sitemapindex.xml")
    assert response.headers["Content-Type"] == "text/xml"
    assert response.body != ""
    url = urlparse.urlsplit(re.findall(r"<loc>(.+?)</loc>", response.body)[0])[2]
    assert re.match(r"^/sitemap_\d{8}-\d{6}\.xml$", url)
    queue_name = "sitemap"
    queue = taskqueue.Queue(queue_name)
    tasks = queue.lease_tasks(0, 1000)
    assert len(tasks) == 2
    assert tasks[0].tag == url
    response = self.app.get(url)
    assert response.headers["Content-Type"] == "text/xml"
    assert response.body != ""

  def test_generate_sitemap(self):
    queue_name = "sitemap"
    queue = taskqueue.Queue(queue_name)

    Sitemap()._post_put_hook(None)
    tasks = queue.lease_tasks(0, 1000)
    assert len(tasks) == 1
    assert tasks[0].tag == "url"
    assert len(tasks[0].payload) == 125
    assert tasks[0].payload.startswith("<url><loc>http://localhost/loc</loc><lastmod>")
    assert tasks[0].payload.endswith("</lastmod><changefreq>daily</changefreq><priority>0.5</priority></url>")

    self.app.get("/_tap/generate_sitemap")

    sitemaps = queue.lease_tasks(0, 1000)
    assert len(sitemaps) == 2
    cache = sitemaps[0]
    assert len(cache.tag) == 28
    assert cache.tag.startswith("/sitemap_")
    assert cache.tag.endswith(".xml")
    blob = pickle.loads(zlib.decompress(cache.payload))
    assert blob["headerlist"] == [('Content-Type', 'text/xml')]
    assert len(blob["body"]) == 233
    assert blob["body"].startswith("<?xml version='1.0' encoding='UTF-8'?>\n<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>http://localhost/loc</loc><lastmod>")
    assert blob["body"].endswith("</lastmod><changefreq>daily</changefreq><priority>0.5</priority></url></urlset>")

    cache = sitemaps[1]
    assert cache.tag == "/sitemapindex.xml"
    blob = pickle.loads(zlib.decompress(cache.payload))
    assert blob["headerlist"] == [('Content-Type', 'text/xml')]
    assert len(blob["body"]) == 194
    assert blob["body"].startswith("<?xml version='1.0' encoding='UTF-8'?>\n<sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><sitemap><loc>http://localhost/sitemap_")
    assert blob["body"].endswith(".xml</loc></sitemap></sitemapindex>")

    Sitemap()._post_put_hook(None)
    self.app.get("/_tap/generate_sitemap")
    tasks = queue.lease_tasks(0, 1000)
    assert len(tasks) == 3
    assert not filter(lambda x: (x != "/sitemapindex.xml") and not re.match(r"^/sitemap_\d{8}-\d{6}\.xml$", x), [i.tag for i in tasks])
    cache = queue.lease_tasks_by_tag(0, 1, "/sitemapindex.xml")[0]
    blob = pickle.loads(zlib.decompress(cache.payload))
    assert blob["body"] != ""
    assert re.match(r"^http://localhost/sitemap_\d{8}-\d{6}\.xml\shttp://localhost/sitemap_\d{8}-\d{6}\.xml$", " ".join(re.findall(r"<loc>(.+?)</loc>", blob["body"])))
