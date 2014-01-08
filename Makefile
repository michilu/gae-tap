include Makefile.in

all: css js test test_utils

TAP_TEMPLATE_DIR=tap/templates
TAP_TEMPLATE_DIR_PATH=$(GAE_DIR)/$(TAP_TEMPLATE_DIR)
TAP_TEMPLATES_COMPILED_ZIP=tap_templates_compiled.zip
TAP_TEMPLATES_COMPILED_ZIP_PATH=$(GAE_LIB_DIR)/$(TAP_TEMPLATES_COMPILED_ZIP)
JS_DIR=$(GAE_DIR)/static/js $(GAE_DIR)/static/tap/js
test_utils=

TAP_HAML = $(wildcard $(TAP_TEMPLATE_DIR_PATH)/*.haml)
TAP_HTML = $(TAP_HAML:.haml=.html)
TAP_MOBHAML = $(wildcard $(TAP_TEMPLATE_DIR_PATH)/mob/*.haml)
TAP_MOBHTML = $(MOBHAML:.haml=.xhtml)

$(TAP_TEMPLATES_COMPILED_ZIP_PATH): $(GAE_LIB_DIR) $(TAP_HTML) $(TAP_MOBHTML)
	jinja2precompiler -c $(TAP_TEMPLATE_DIR_PATH)
	zip -FS -j $(TAP_TEMPLATES_COMPILED_ZIP_PATH) $(TAP_TEMPLATE_DIR_PATH)/*.pyc

template: $(MINJS) mo $(GAE_LIB_PACKAGES_DIR) $(TEMPLATES_COMPILED_ZIP_PATH) $(TAP_TEMPLATES_COMPILED_ZIP_PATH)

test_utils: $(GAE_LIB_PACKAGES_DIR) template $(FANSTATIC_DIR)
	@py.test $(GAE_DIR)/tap/tests/test*.py --doctest-modules --with-gae --gae-path=$(GAE_PATH) --gae-project-path=`pwd`/$(GAE_DIR) --cov-report=html --cov=$(GAE_DIR) $(test_utils)
	rm -rf /tmp/dev_appserver.test_datastore
