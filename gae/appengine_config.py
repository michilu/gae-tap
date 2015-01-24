# -*- coding: utf-8 -*-

# Application settings of Google App Engine / Python


# START of settings for gae-tap

# settings for Google Cloud Endpoints from this below
config_API = (
  #(<module name>,)
  "api_sample.v1",
)

# settings for webapp2 from this below
config_APP = {
  #{<domain>: ((<path prefix>, <module name>[, <namespace>]),)}
  "<:localhost|(.*-dot-)?gae-tap.appspot.com>": (("", "app_sample.v1"),),
  #r"<subdomain:(?!www\.)[^.]+>.local": (("/test", "app_sample"),),
}

#config_FEEDBACK_FORMKEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
#config_GA_ACCOUNT = ""
#config_JOB_EMAIL_RECIPIENT = "email@example.com"
#config_WEBAPP2_CONFIG = {}

# settings for Google Cloud Endpoints and webapp2 from this below

#config_APPSTATS_INCLUDE_ERROR_STATUS = False

# This is a session secret key used by webapp2 framework.
# Get 'a random and long string' from here:
# http://clsc.net/tools/random-string-generator.php
# or execute this from a python shell: import os; os.urandom(64)
config_SECRET_KEY = "a very long and secret session key goes here"

# END of settings for gae-tap


# START of settings for appstats
# To use the appstats only dev_appserver.
# https://cloud.google.com/appengine/docs/python/tools/appstats
# If you want to use this feature on production, please setting the Cloud Trace instead.
# https://cloud.google.com/tools/cloud-trace

from google.appengine.ext.appstats import recording

appstats_CALC_RPC_COSTS = True
appstats_RECORD_FRACTION = 0.1

def webapp_add_wsgi_middleware(app):
  import tap
  if tap.config.DEBUG:
    return recording.appstats_wsgi_middleware(app)
  else:
    return app

# END of settings for appstats
