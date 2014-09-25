import tests.util

from google.appengine.api import taskqueue

class AppTest(tests.util.TestCase):

  def test_app(self):
    taskqueue.Queue("cache").lease_tasks(0, 1000)
