config_APP = {
  #{<domain>: ((<path prefix>, <module name>[, <namespace>]),)}
  "": (
    ("/sample", "app_test1"),
    ("/test", "app_test", "namespace"),
  ),
  r"<subdomain:(?!www\.)[^.]+>.localhost": (("", "app_test2", lambda:"localhost"),),
}

config_APPSTATS_INCLUDE_ERROR_STATUS = False
config_CORS_Access_Control_Max_Age = "1"
config_DROPBOX_PROXY_UID = 0
config_GA_ACCOUNT = "test"
config_JINJA2_FORCE_COMPILED = False
config_RESPONSE_CACHE_SIZE = 0
config_SECRET_KEY = "SECRET_KEY"
config_URI_AUTHORITY = "localhost"
config_WEBAPP2_CONFIG = {}
