GAE_PATH=$(GAE_HOME)/
GAE_DIR=..
GAE_LIB=site-packages
GAE_LIB_DIR=$(GAE_DIR)/$(GAE_LIB)
GAE_LIB_PACKAGES_DIR=$(GAE_LIB_DIR)/packages
TEMPLATE_DIR_PATH=templates
TEMPLATES_COMPILED_ZIP=tap_templates_compiled.zip
TEMPLATES_COMPILED_ZIP_PATH=$(GAE_LIB_DIR)/$(TEMPLATES_COMPILED_ZIP)
JS_DIR=static/js
NODE_MODULES_BASE=../../node_modules
BIN_COFFEE=$(NODE_MODULES_BASE)/coffee-script/bin/coffee
BIN_UGLIFYJS=$(NODE_MODULES_BASE)/uglify-js/bin/uglifyjs
TEMPLATE_DIR=
BIN_PHANTOMJS=$(HOME)/local/bin/phantomjs
BIN_HAML=$(firstword $(HAML_PATH) haml)
VERSION_HTML=$(TEMPLATE_DIR_PATH)/tap/version.html
VERSION=$(shell git describe --tags --dirty=+)_$(shell git log -n1 --pretty=format:%ad --date=short)
RELEASE_ZIP=gaetap-$(VERSION).zip
RELEASE_FILES=$(sort\
	LICENSE\
	$(wildcard Makefile.*)\
	$(wildcard *.py)\
	$(HTML)\
	$(MOBHTML)\
	$(filter-out static/js/i18n%,$(MINJS) $(JS))\
	$(TEMPLATE_DIR_PATH)/tap/ads/analytics.html\
	$(VERSION_HTML)\
	endpoints.patch\
)

.SUFFIXES: .haml .html
.haml.html:
	@if which $(BIN_HAML) >/dev/null; then\
		echo $(BIN_HAML) -f html5 -t ugly $< $@;\
		$(BIN_HAML) -f html5 -t ugly $< $@;\
	else\
		echo haml is not exists: no build $<;\
	fi
HAML = $(wildcard $(TEMPLATE_DIR_PATH)/tap/*.haml)
HTML = $(HAML:.haml=.html)

.SUFFIXES: .haml .xhtml
.haml.xhtml:
	@if which $(BIN_HAML) >/dev/null; then\
		echo $(BIN_HAML) -f xhtml -t ugly $< $@;\
		$(BIN_HAML) -f xhtml -t ugly $< $@;\
	else\
		echo haml is not exists: no build $<;\
	fi
MOBHAML = $(wildcard $(TEMPLATE_DIR_PATH)/tap/mob/*.haml)
MOBHTML = $(MOBHAML:.haml=.xhtml)

.SUFFIXES: .coffee .js
.coffee.js:
	$(BIN_COFFEE) -b -c $<
.SUFFIXES: .js .min.js
.js.min.js:
	$(BIN_UGLIFYJS) --define PRODUCTION=0 -nc -m -r "$$" -o $@ $<
COFFEE = $(foreach dir,$(JS_DIR),$(wildcard $(dir)/*.coffee))
JS = $(COFFEE:.coffee=.js)
MINJS = $(JS:.js=.min.js)

all: $(MINJS) $(TEMPLATES_COMPILED_ZIP_PATH)

clean:
	find . -type d -name .cache |xargs rm -rf
	find . -type d -name __pycache__ |xargs rm -rf
	find . -type d -name htmlcov |xargs rm -rf
	find . -name "*.pyc" -delete
	find . -name "*.sw?" -delete
	find . -name .DS_Store -delete
	find . -name .coverage -delete
	find . -name "gaetap-*.zip" -delete
	find $(TEMPLATE_DIR_PATH) -name "*.py" -delete
	rm -f $(TEMPLATES_COMPILED_ZIP_PATH)
	rm -f $(HTML)
	rm -f $(MOBHTML)
	rm -f $(JS)
	rm -f $(MINJS)

$(VERSION_HTML):
	@if [ "$(VERSION)" != "$(strip $(shell [ -f $@ ] && cat $@))" ] ; then\
		echo 'echo $(VERSION) > $@' ;\
		echo $(VERSION) > $@ ;\
	fi;

template: $(MINJS) $(TEMPLATES_COMPILED_ZIP_PATH)

js: $(JS) $(MINJS)

$(GAE_LIB_DIR):
	mkdir -p $@

$(TEMPLATES_COMPILED_ZIP_PATH): $(GAE_LIB_DIR) $(HTML) $(MOBHTML) $(VERSION_HTML)
	jinja2precompiler -c $(TEMPLATE_DIR_PATH)
	zip -FS -j $(TEMPLATES_COMPILED_ZIP_PATH) $(TEMPLATE_DIR_PATH)/*.pyc

shell:
	@cd $(GAE_DIR); PYTHONPATH=$$GAE_HOME ./tap/shell.py

release: $(RELEASE_ZIP)

$(RELEASE_ZIP): $(RELEASE_FILES) $(TEMPLATES_COMPILED_ZIP_PATH)
	cd $(GAE_DIR); zip -FS tap/$@ $(foreach file,$(RELEASE_FILES),tap/$(file)) $(GAE_LIB)/$(TEMPLATES_COMPILED_ZIP)

.PHONY: all clean $(VERSION_HTML)
