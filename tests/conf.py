import os

root_path = None

if root_path is None:
  root_path = os.path.dirname(os.path.dirname( __file__ )) + "/gae"
  assert os.path.exists(root_path)
