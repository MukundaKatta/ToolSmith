.PHONY: install test lint typecheck fmt clean all

all: install lint typecheck test

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

typecheck:
	mypy src/toolsmith/

fmt:
	ruff format src/ tests/

clean:
	rm -rf dist build *.egg-info .pytest_cache .mypy_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
