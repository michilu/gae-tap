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
RUN bundle install --quiet --jobs `grep processor /proc/cpuinfo|wc -l`

COPY package.json /tmp/package.json
RUN npm install --silent --color false

COPY packages.txt /tmp/packages-gae.txt
RUN pip install --quiet -r packages-gae.txt

COPY packages.txt /tmp/packages.txt
RUN pip install --quiet -r packages.txt

COPY gae/tap/endpoints.patch /tmp/endpoints.patch
RUN \
  curl -s -o google_appengine.zip https://storage.googleapis.com/appengine-sdks/featured/google_appengine_1.9.10.zip &&\
  unzip -q google_appengine.zip -d / &&\
  patch -d /google_appengine/lib/endpoints-1.0/endpoints -p0 -i /tmp/endpoints.patch &&\
  rm -rf /tmp/*
