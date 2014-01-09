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

Low cost operating:

* Google Drive Spreadsheets as a database via Google Visualization API
* Google Drive Spreadsheets-based feedback form
* hosting DropBox as a proxy
* hostname-based multitenancy
* just a few costs permanent caching
* minimum OAuth accounting
* redirecting to Google URL Shortener

Performance:

* pre-compiling templates
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

Set up
------

::

    $ git clone https://github.com/MiCHiLU/gae-tap.git
    $ cd gae-tap
    $ bundle install
    $ npm install
    $ mkvirtualenv --python=`which ptyhon2.7` gae-tap
    (gae-tap)$ pip install -r packages.txt

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
