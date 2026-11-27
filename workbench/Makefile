.PHONY: run test browser-test
run:
	./run.sh

test:
	PYTHONPATH="$$PWD:$$PWD/.site:$${SURFIT_BIN:-}" \
	SURFIT_BIN="$${SURFIT_BIN:-$$PWD/../build-ci/bin}" \
	python3 tests/test_app.py

browser-test:
	PLAYWRIGHT_BROWSERS_PATH="$$PWD/.pw-browsers" node tests/browser_check.js
