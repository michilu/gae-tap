include Makefile.in

all: css js test test_utils

test_utils=

test_utils: $(GAE_LIB_PACKAGES_DIR) template $(FANSTATIC_DIR)
	@py.test $(GAE_DIR)/tap/tests/test*.py --doctest-modules --with-gae --gae-path=$(GAE_PATH) --gae-project-path=`pwd`/$(GAE_DIR) --cov-report=html --cov=$(GAE_DIR) $(test_utils)
	rm -rf /tmp/dev_appserver.test_datastore
