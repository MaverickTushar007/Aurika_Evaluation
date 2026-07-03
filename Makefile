# Makefile
.PHONY: setup test benchmark train docker-build clean help

setup:
	pip install -r requirements.txt
	pip install -e .
	pip install pytest

test:
	PYTHONPATH=. ./venv/bin/python -m pytest tests/

benchmark:
	./venv/bin/python benchmark/run_benchmark.py --config configs/benchmark.yaml

train:
	./venv/bin/python training/run_retraining.py --epochs 50

docker-build:
	docker build -f deployment/Dockerfile -t restaurant-analytics:v2.0.0 .

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

help:
	@echo "Available commands:"
	@echo "  setup         Install packages and test dependencies"
	@echo "  test          Run automated unit/integration tests"
	@echo "  benchmark     Execute performance benchmark suite"
	@echo "  train         Trigger detector training (Run B: 50 epochs)"
	@echo "  docker-build  Build production Docker container image"
	@echo "  clean         Remove compile and testing caches"
