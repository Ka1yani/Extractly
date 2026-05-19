.PHONY: install test lint run scout extract clean

install:
	pip install -e ".[dev]"

test:
	pytest tests/ --cov=extractly --cov-report=term-missing --cov-branch -v

lint:
	ruff check src/ tests/
	mypy src/

run:
	python -m extractly run --help

scout:
	python -m extractly scout --sample input_docs/Raloxifene_Master_Sample.pdf

extract:
	python -m extractly extract --input-dir input_docs/

clean:
	rm -rf output/*.xlsx output/html/*.html
	rm -rf __pycache__ .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
