PYTHON ?= .venv/bin/python

.PHONY: validate

validate:
	$(PYTHON) scripts/validate_public_truth.py
	$(PYTHON) scripts/validate_api_stability.py
	$(PYTHON) scripts/validate_documentation_antidrift.py
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy govengine
	$(PYTHON) -m pytest -q
