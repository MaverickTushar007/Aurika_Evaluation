.PHONY: install test lint run build clean

# Python executable to use
PYTHON = python3
VENV = .venv
BIN = $(VENV)/bin/python

install:
	@echo "Installing backend dependencies..."
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd dashboard && npm ci
	@echo "Installing pre-commit hooks..."
	$(VENV)/bin/pip install pre-commit
	$(VENV)/bin/pre-commit install
	@echo "Installation complete."

test:
	@echo "Running backend unit tests..."
	$(BIN) -m unittest discover -s pilot/tests -v
	@echo "Running frontend tests..."
	cd dashboard && npm run test

lint:
	@echo "Running backend linters..."
	$(VENV)/bin/flake8 .
	$(VENV)/bin/black --check .
	$(VENV)/bin/isort --check-only .
	@echo "Running frontend linters..."
	cd dashboard && npm run lint

run:
	@echo "Starting Pilot Runtime & Dashboard..."
	# Starts python runner in background and dashboard in foreground
	$(BIN) -m pilot.scripts.run_pilot_deployment &
	cd dashboard && npm run dev

build:
	@echo "Building production dashboard bundle..."
	cd dashboard && npm run build

clean:
	@echo "Cleaning caches and virtual environments..."
	rm -rf $(VENV)
	rm -rf dashboard/node_modules
	rm -rf dashboard/dist
	find . -type d -name "__pycache__" -exec rm -r {} +
	@echo "Clean complete."
