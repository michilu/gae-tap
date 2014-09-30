#!/bin/sh

random=`od -An -N1 -tu1 < /dev/urandom`
timeout_sec=`expr 12 + 8 \* ${random} / 255`

echo set timeout ${timeout_sec}s...

timeout ${timeout_sec}s $GOOGLE_APPENGINE/dev_appserver.py --skip_sdk_update_check=yes --dev_appserver_log_level=error gae/app.yaml 2>log
if [ `grep -c -v ^INFO log` != 0 ]; then
  cat log;
  exit 1;
fi
