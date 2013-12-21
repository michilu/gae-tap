from google.appengine.ext.appstats import recording

appstats_CALC_RPC_COSTS = True
appstats_RECORD_FRACTION = 0.1

config_APPS = {
  #{<domain>: ((<path prefix>, <module name>[, <namespace>]),)}
  "<:localhost|gae-tap.appspot.com>": (("", "app_sample"),),
  #r"<subdomain:(?!www\.)[^.]+>.local": (("/test", "app_sample"),),
}
#config_APPSTATS_INCLUDE_ERROR_STATUS = False
#config_GA_ACCOUNT = ""
#config_JOB_EMAIL_RECIPIENT = "email@example.com"
#config_FEEDBACK_FORMKEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

def webapp_add_wsgi_middleware(app):
  return recording.appstats_wsgi_middleware(app)

#GOOGLE_USERNAME = "email@example.com"
#GOOGLE_PASSWORD = "password"
