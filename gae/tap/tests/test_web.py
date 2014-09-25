#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

import tests.util

from google.appengine.api import taskqueue

import conf

class AppTest(tests.util.TestCase):
  root_path = conf.root_path

  def test_status(self):
    self.app.head("/", status=404)
    self.app.get("/_ah/start")
    self.app.get("/_ah/stop")
    self.app.post("/_tap/response_cache", status=403)

  def test_app_test1(self):
    self.app.get("/sample/?q")
    response = self.app.get("/sample/")
    response.mustcontain("Sample")

  def test_cache(self):
    queue_name = "cache"
    queue = taskqueue.Queue(queue_name)
    assert queue.fetch_statistics().tasks == 0

    response = self.app.get("/sample/")
    assert queue.fetch_statistics().tasks == 1
    cache = queue.lease_tasks(0, 1)[0]

    assert self.app.get("/sample/").body == response.body
    assert queue.fetch_statistics().tasks == 1
    assert int(queue.lease_tasks(0, 1)[0].name[:10]) - int(cache.name[:10]) in (0, 1)

  def test_csrf(self):
    response = self.app.get("/_tap/response_cache?path=/")
    assert response.forms[1]["csrf"].value != ""
    csrf = response.forms[1]["csrf"].value
    self.app.post("/_tap/response_cache", {"csrf": csrf})
    self.app.post("/_tap/response_cache", {"csrf": "fake"}, status=403)

  def test_domain_routing(self):
    self.app.get("http://www.localhost/", status=404)
    self.app.get("http://foo.localhost/").mustcontain("foo")

  def test_featurephone(self):
    headers = {"User-Agent": "Googlebot-Mobile"}
    response = self.app.get("/sample/", headers=headers, status=302)
    response = response.follow()
    assert response.headers.get("Content-Type") == "application/xhtml+xml;charset=Shift_JIS"
    response = self.app.get("/sample/?q", headers=headers, status=302)
    assert response.headers.get("Location") == "http://localhost/sample/index.html?q"

  def test_fetch_page(self):
    self.app.get("/test/fetch_page?test")

  def test_namespace(self):
    self.app.get("/test/namespace").mustcontain("namespace")
    self.app.get("http://foo.localhost/namespace").mustcontain("localhost")

  def test_response_cache(self):
    response = self.app.get("/_tap/response_cache")
    assert len(response.forms) == 1
    response = self.app.get("/_tap/response_cache?path=/")
    assert len(response.forms) == 2
    response.mustcontain("Do you want to delete it from caches?")

    queue_name = "cache"
    path = "/sample/"

    queue = taskqueue.Queue(queue_name)
    assert queue.fetch_statistics().tasks == 0
    self.app.get(path)
    self.app.get("{0}?test".format(path))
    assert queue.fetch_statistics().tasks == 2

    csrf = response.forms[1]["csrf"].value
    response = self.app.post("/_tap/response_cache?host={0}&path={1}".format("localhost:80", path), {"csrf": csrf})
    response.mustcontain("Deleted the key from caches.")
    assert "Do you want to delete it from caches?" not in response.body
    assert queue.fetch_statistics().tasks == 1

  def test_OverQuotaError(self):
    message = "will move to the top page after 30 seconds..."
    error_message = "Sorry, a server error has occurred. Display the top page."
    queue = taskqueue.Queue("cache")

    assert [i.tag for i in queue.lease_tasks(0, 1000)] == []
    response = self.app.get("/test/test.html", headers={"User-Agent": "bot"}, status=503)
    assert response.headers.get("Retry-After") == "86400"
    response = self.app.get("/test/test.html", status=500)
    response.mustcontain(message)
    response.mustcontain("<meta content='30; url=/' http-equiv='refresh'>")
    assert error_message not in response

    self.app.get("/sample/")
    self.execute_tasks("default")
    caches = queue.lease_tasks_by_tag(0, 1000, tag="localhost:80/sample/")
    assert len(caches) == 1
    payload = caches[0].payload
    queue.add(taskqueue.Task(method="PULL", tag="/index.html", payload=payload))
    queue.delete_tasks(caches)
    assert [i.tag for i in queue.lease_tasks(0, 1000)] == ["/index.html"]
    response = self.app.get("/test/test.html", status=500)
    response.mustcontain(message)
    response.mustcontain("<meta content='30; url=/' http-equiv='refresh'>")
    assert error_message not in response

    queue.add(taskqueue.Task(method="PULL", tag="/", payload=payload))
    assert [i.tag for i in queue.lease_tasks(0, 1000)] == ["/index.html", "/"]
    response = self.app.get("/test/test.html", status=500)
    assert message not in response
    response.mustcontain(error_message)

  def test_OverQuotaError_for_featurephone(self):
    message = u"Go to the top page".encode("Shift_JIS")
    error_message = u"Sorry, a server error has occurred. Display the top page.".encode("Shift_JIS")
    queue = taskqueue.Queue("cache")

    assert [i.tag for i in queue.lease_tasks(0, 1000)] == []
    response = self.app.get("/test/test.html", headers={"User-Agent": "MOT-bot"}, status=503)
    assert response.headers.get("Retry-After") == "86400"
    response = self.app.get("/test/test.html", headers={"User-Agent": "MOT-"}, status=500)
    response.mustcontain(message)
    assert error_message not in response

    self.app.get("/sample/")
    self.execute_tasks("default")
    caches = queue.lease_tasks_by_tag(0, 1000, tag="localhost:80/sample/")
    assert len(caches) == 1
    payload = caches[0].payload
    queue.add(taskqueue.Task(method="PULL", tag="localhost:80/", payload=payload))
    queue.delete_tasks(caches)
    assert [i.tag for i in queue.lease_tasks(0, 1000)] == ["localhost:80/"]
    response = self.app.get("/test/test.html", headers={"User-Agent": "MOT-"}, status=500)
    response.mustcontain(message)
    assert error_message not in response

    queue.add(taskqueue.Task(method="PULL", tag="/index.html", payload=payload))
    assert [i.tag for i in queue.lease_tasks(0, 1000)] == ["localhost:80/", "/index.html"]
    response = self.app.get("/test/test.html", headers={"User-Agent": "MOT-"}, status=500)
    assert message not in response
    response.mustcontain(error_message)

  def test_mobile(self):
    self.app.get("/test/index.html", headers={"User-Agent": "MOT-"})
    self.expected_logs = [
      ('WARNING', 'site-packages/packages/ga.py', '_google_analytics_tracking', "GoogleAnalyticsMixin._google_analytics_tracking: http://www.google-analytics.com/__utm.gif?utmac=test..., {'Accepts-Language': '', 'User-Agent': 'MOT-'}"),
    ]

  def test_maintain_response(self):
    response = self.app.get("/_tap/maintain_response")
    response.mustcontain("MaintainResponse: 0 entities deleted")
    self.app.get("/sample/")
    response = self.app.get("/_tap/maintain_response")
    response.mustcontain("MaintainResponse: 1 entities deleted")

  def test_internal_server_error(self):
    message = "will move to the top page after 30 seconds..."

    with tests.util.set_config(DEBUG=False):
      response = self.app.get("/test/error.html", status=500)
      response.mustcontain(message)
    self.expected_logs = [('ERROR', 'gae/tap/ext.py', 'dispatch', 'AssertionError: assert False')]

  def test_head(self):
    self.app.get("/test/head")

  def test_cors(self):
    response = self.app.options("/test/cors")
    assert response.headers.get("Access-Control-Allow-Credentials") is None
    assert response.headers.get("Access-Control-Max-Age") == "1"
    response = self.app.options("/test/cors", headers=[("Referer", "http://localhost/test")])
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost"
    response = self.app.options("/test/cors", headers=[("Origin", "http://localhost")])
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost"
    response = self.app.options("/test/cors", headers=[("Access-Control-Request-Method", "test")])
    assert response.headers.get("Access-Control-Allow-Methods") == "test"
    response = self.app.options("/test/cors", headers=[("Access-Control-Request-Headers", "test")])
    assert response.headers.get("Access-Control-Allow-Headers") == "test"
    response = self.app.get("/test/cors", headers=[("Origin", "http://localhost")])
    assert response.headers.get("Access-Control-Allow-Origin") == "test"

  def test_rate_limit(self):
    self.app.get("/test/rate_limit")
    self.app.post("/test/rate_limit")
    self.app.get("/test/rate_limit", status=403)
    self.app.put("/test/rate_limit")
    self.app.put("/test/rate_limit", status=403)

  def test_cache_temporary(self):
    response = self.app.get("/test/cache_temporary")
    assert self.app.get("/test/cache_temporary").body == response.body

  def test_bang_redirector(self):
    response = self.app.get("/!TEST", status=301)
    assert response.headers.get("Location") == "http://goo.gl/TEST"

  def test_use_zipfile(self):
    self.app.get("/test/zipfile")

  def test_translation(self):
    response = self.app.get("/test/translation")
    response.mustcontain("""
<script>
window.gettext=function(t){return t},window.ngettext=function(t,n,e){return 1===e?t:n};
</script>
<script src="/_tap/i18n/sample.en.js"></script>
""")
    response.mustcontain("<li>Python</li>\n<li>Anaconda</li>\n<li>Boa</li>\n<li>Cobra</li>")
    response = self.app.get("/test/translation", headers=[("Accept-Language", "ja-JP,ja;q=0.8")], status=302)
    assert response.headers.get("Location") == "http://localhost/test/translation?l=ja"
    response = self.app.get("/test/translation?l=ja")
    response.mustcontain("""
<script>
window.gettext=function(t){return t},window.ngettext=function(t,n,e){return 1===e?t:n};
</script>
<script src="/_tap/i18n/sample.ja.js"></script>
""")
    response.mustcontain("<li>ニシキヘビ</li>\n<li>アナコンダ</li>\n<li>ボア</li>\n<li>コブラ</li>")
    self.app.get("/test/translation?test", headers=[("Accept-Language", "ja-JP,ja;q=0.8")], status=302)

  def test_i18n_js(self):
    response = self.app.get("/_tap/i18n/sample.en.js")
    response.mustcontain(";translation={},")
    response = self.app.get("/_tap/i18n/sample.ja.js")
    response.mustcontain(';translation={"catalog": {"Dumeril": "\u30c7\u30e5\u30e1\u30ea\u30eb"}, "plural": "0", "fallback": null},')
