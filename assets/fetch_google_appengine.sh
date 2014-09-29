#!/bin/bash
v=10
max=$v+10
while [[ v -ne $max ]]; do
  url=https://storage.googleapis.com/appengine-sdks/featured/google_appengine_1.9.$((v++)).zip
  echo testing... $url
  if curl -f -I -s $url >/dev/null; then
    echo use $url
    curl -s -o google_appengine.zip $url
    exit 0
  fi
done
exit 1
