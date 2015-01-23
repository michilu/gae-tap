#!/bin/sh

echo > gae/site-packages/packages-no-deps.txt
echo > gae/site-packages/packages.txt

rm -f gae/app_sample.py
rm -f gae/site-packages/uamobile.py
rm -f gae/tap/tests/test_web.py
rm -f gae/tap/tests/test_web_bugs.py

rm -rf gae/locales
rm -rf gae/oauth_config
rm -rf gae/static
rm -rf gae/static_root
rm -rf gae/templates

if [ `uname` == "Darwin" ]; then
  sed -i "" "/app_sample/d" gae/appengine_config.py;
else
  sed -i "/app_sample/d" gae/appengine_config.py;
fi
