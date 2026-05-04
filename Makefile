UV ?= uv
PYTHON ?= python3
SRC := ./earnings_calendar
TESTS := ./tests

.PHONY: default
default: check

.PHONY: setup
setup:
	$(UV) sync --all-extras --dev
	$(UV) run pre-commit install

.PHONY: format
format:
	$(UV) run ruff format $(SRC) $(TESTS)
	$(UV) run ruff check --fix $(SRC) $(TESTS)

.PHONY: lint
lint:
	$(UV) run ruff format --check $(SRC) $(TESTS)
	$(UV) run ruff check $(SRC) $(TESTS)

.PHONY: check
check:
	$(UV) run pyrefly check
	$(UV) run bandit -r $(SRC)
	$(UV) run pytest $(TESTS)

.PHONY: clean
clean:
	$(UV) run ruff clean
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache build dist *.egg-info
