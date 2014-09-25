basePath = "../"
files = [
  JASMINE,
  JASMINE_ADAPTER,
  "static/lib/jquery/*/jquery.min.js",
  "static/lib/bootstrap/*/js/bootstrap.min.js",
  "static/lib/angularjs/*/angular.js",
  "static/lib/angularjs/*/angular-cookies.js",
  "static/lib/angularjs/*/angular-resource.js",
  "static/lib/angularjs/*/angular-mocks.js",
  "static/js/**/*.js",
  "tests/**/test_*.spec.js",
]
exclude = [
  "static/js/**/*.min.js",
]
reporter = "progress"
colors = true
logLevel = LOG_INFO
autoWatch = true
browsers = ["PhantomJS"]
singleRun = false
junitReporter =
  outputFile: "test_out/unit.xml"
  suite: "unit"
