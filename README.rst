.. image:: https://travis-ci.org/MiCHiLU/gae-tap.svg?branch=master
    :target: https://travis-ci.org/MiCHiLU/gae-tap
.. image:: https://app.wercker.com/status/72878e11dca6d30f174e95253d766075/s/master
    :target: https://app.wercker.com/project/bykey/72878e11dca6d30f174e95253d766075
.. image:: https://landscape.io/github/MiCHiLU/gae-tap/master/landscape.png
    :target: https://landscape.io/github/MiCHiLU/gae-tap/master

A full stack framework for the Google App Engine -based
=======================================================

Let's finish the work quickly and go TAP BEER!

.. image:: http://farm5.staticflickr.com/4114/4809856899_e889084816.jpg
  :align: center
  :alt: Man's Beautiful Creation by Idoknow19, on Flickr
  :height: 281
  :width: 500

Looking for sponsors:

#. `$120 - I will get 30L barrel beer!!!  <https://www.gittip.com/MiCHiLU/>`_
#. `$60 - I will get 15L barrel beer!!    <https://www.gittip.com/MiCHiLU/>`_
#. `$12 - I will get 1 pint beer!         <https://www.gittip.com/MiCHiLU/>`_
#. `$6 - I will get 1/2 pint beer!        <https://www.gittip.com/MiCHiLU/>`_

Status
------

* `Travis CI <https://travis-ci.org/MiCHiLU/gae-tap>`_
* `Wercker CI <https://app.wercker.com/project/bykey/72878e11dca6d30f174e95253d766075>`_
* `Code Health <https://landscape.io/github/MiCHiLU/gae-tap/master>`_

Features
--------

Supports:

* Google App Engine / Python 2.7

  * Appstats
  * Google Cloud Endpoints API
  * NDB Asynchronous Operation
  * Python Module Configuration

* Google Analytics for feature phone
* I18N / Python, HTML and JavaScript
* Japanese han-kaku characters / 半角
* OAuth login / gae-simpleauth
* Google OAuth authentication-based Users API (alternate of Google App Engine Users API)
* generating sitemaps
* sessions
* Google Cloud Endpoints API as a CRUD, avoid method naming conflict in implemented with multiple classes
* endpoints-proto-datastore

Low cost operating:

* Google Drive Spreadsheets as a database via Google Visualization API
* Google Drive Form-based feedback system
* hosting as a proxy
  * DropBox
  * Google Drive
* hostname-based multitenancy
  * supports robots.txt
* just a few costs permanent caching and key-value store via taskqueue API
* minimum OAuth accounting
* redirecting to Google URL Shortener

Performance:

* pre-compiling jinja2 templates
* uglify-js

Coding:

* CoffeeScript
* HAML
* SASS / compass

Development:

* AngularJS
* Jinja2
* Twitter bootstrap
* webapp2

* file system event-based automation building on Mac OS X 10.7+
* Docker

Testing:

* coverage of tests
* karma
* py.test

Utils:

* CORS
* CSRF guard
* HMAC
* e-mail reports of errors
* fanstatic
* handling taskqueue
* managing cache records
* memoize
* ring buffer
* token bucket

Continuous Integration Supports:

* Travis CI
* Wercker CI

Set up
------

::

    $ git clone https://github.com/MiCHiLU/gae-tap.git
    $ cd gae-tap
    $ bundle install
    $ npm install
    $ mkvirtualenv --python=`which ptyhon2.7` gae-tap
    (gae-tap)$ pip install -r requirements.txt
    (gae-tap)$ pip install -r requirements-gae.txt

If you want to start a new project with `make scaffold`, as below::

    $ make scaffold
    your app-id, default 'gae-tap': <type your app-id>
    your github user name, default 'MiCHiLU': <type your github user name>

Set environ
-----------

It need the `GOOGLE_APPENGINE` environ args. Default `GOOGLE_APPENGINE` as below::

    GOOGLE_APPENGINE=$HOME/google-cloud-sdk/platform/google_appengine

If you want to set other path, define `GOOGLE_APPENGINE` in environ as below::

    $ GOOGLE_APPENGINE=<path to your gae> make

Docker
------

or, Quickly set up environment via Docker:

    $ docker pull michilu/gae-tap

Build and Test
--------------

::

    (gae-tap)$ make

Run development server
----------------------

::

    (gae-tap)$ make runserver

then access to:

* admin server: http://localhost:8000
* instance server: http://localhost:8080

Deploy
------

::

    (gae-tap)$ make deploy

How to update core library
--------------------------

#. Download `gaetap-<release-number>.zip` file from https://github.com/MiCHiLU/gae-tap/releases
#. Then replace with files and directories in your repository.

Dependencies
------------

* Bundler
* GNU Make
* Python 2.7
* npm

LICENSE
-------

Licensed under the terms of the MIT.

Copyright (c) 2013 ENDOH takanao
