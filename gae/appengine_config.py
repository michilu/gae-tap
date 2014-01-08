from google.appengine.ext.appstats import recording

appstats_CALC_RPC_COSTS = True
appstats_RECORD_FRACTION = 0.1

config_APPS = {
  #{<domain>: ((<path prefix>, <module name>[, <namespace>]),)}
  "<:localhost|(.*-dot-)?gae-tap.appspot.com>": (("", "app_sample"),),
  #r"<subdomain:(?!www\.)[^.]+>.local": (("/test", "app_sample"),),
}

# This is a session secret key used by webapp2 framework.
# Get 'a random and long string' from here:
# http://clsc.net/tools/random-string-generator.php
# or execute this from a python shell: import os; os.urandom(64)
config_SECRET_KEY = "a very long and secret session key goes here"

#config_APPSTATS_INCLUDE_ERROR_STATUS = False
#config_FEEDBACK_FORMKEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
#config_GA_ACCOUNT = ""
#config_JOB_EMAIL_RECIPIENT = "email@example.com"
#config_WEBAPP2_CONFIG = {}

def webapp_add_wsgi_middleware(app):
  return recording.appstats_wsgi_middleware(app)
