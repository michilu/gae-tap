import os

root_path = os.path.dirname(os.path.abspath(os.path.dirname(os.path.dirname( __file__ ) + "/../..")))
assert root_path.endswith("/gae")
assert os.path.exists(root_path)
