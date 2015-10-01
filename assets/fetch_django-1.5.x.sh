#!/bin/bash
target="$HOME/google-cloud-sdk/platform/google_appengine/lib/django-1.5"
mkdir -p "${target}"
pip install --no-dependencies -t "${target}" "django<1.6"
