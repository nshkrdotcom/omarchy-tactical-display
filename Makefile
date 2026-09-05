SHELL := /bin/bash
.PHONY: test validate doctor preview bindings backend-once
test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
	node --test --test-reporter=spec tests/js/*.test.js
validate:
	bash scripts/validate.sh
doctor:
	bash scripts/doctor.sh
preview:
	node scripts/render-fixtures.js --out /tmp/tactical-display-fixtures
bindings:
	bash scripts/print-bindings.sh
backend-once:
	python3 scripts/telemetry.py --once --instrument all | python3 -m json.tool
