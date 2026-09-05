SHELL := /bin/bash

.PHONY: test validate doctor backend-once install-local bindings clean package

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

validate:
	./scripts/validate.sh

doctor:
	./scripts/doctor.sh

backend-once:
	python3 scripts/telemetry.py --once --interval 0.25 | python3 -m json.tool

install-local:
	./scripts/install-local.sh

bindings:
	./scripts/print-bindings.sh

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

package: clean
	cd .. && zip -r omarchy-tactical-display.zip omarchy-tactical-display -x 'omarchy-tactical-display/.git/*'
