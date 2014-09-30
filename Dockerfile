FROM michilu/fedora-zero

WORKDIR /tmp
ENV GOOGLE_APPENGINE /google_appengine

RUN yum install --quiet -y \
  git \
  make \
  npm \
  patch \
  python-devel \
  python-lxml \
  python-pip \
  ruby-devel \
  rubygem-bundler \
  unzip \
  && yum clean all

COPY Gemfile /tmp/Gemfile
RUN bundle install --quiet --jobs 4

COPY package.json /tmp/package.json
RUN npm install --silent --color false

COPY requirements.txt /tmp/requirements-gae.txt
RUN pip install --quiet -r requirements-gae.txt

COPY requirements.txt /tmp/requirements.txt
RUN pip install --quiet -r requirements.txt

COPY gae/tap/endpoints.patch /tmp/endpoints.patch
COPY assets/fetch_google_appengine.sh /tmp/fetch_google_appengine.sh
RUN \
  /tmp/fetch_google_appengine.sh &&\
  unzip -q google_appengine.zip -d / &&\
  patch -d /google_appengine/lib/endpoints-1.0/endpoints -p0 -i /tmp/endpoints.patch &&\
  rm -rf /tmp/*
