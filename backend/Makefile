.DEFAULT_GOAL := help

PORT ?= 8000
UV ?= uv

.PHONY: help env install migrate makemigrations run dev test test-unit test-integration test-cov lint format typecheck check clean

help: ## Show available backend commands
	@awk 'BEGIN {FS = ":.*## "; printf "\nBackend targets:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Create .env from env.template if it does not exist
	@if [ ! -f .env ]; then cp env.template .env && echo "Created .env from env.template"; else echo ".env already exists"; fi

install: ## Install Python dependencies with uv
	$(UV) sync

migrate: ## Apply Django database migrations
	$(UV) run python manage.py migrate

makemigrations: ## Generate new Django migrations
	$(UV) run python manage.py makemigrations

run: ## Start Django development server (PORT=8000)
	$(UV) run python manage.py runserver $(PORT)

dev: run ## Alias for run

test: ## Run all backend tests (unit + integration)
	$(UV) run pytest src/tests -v

test-unit: ## Run backend unit tests only
	$(UV) run pytest src/tests/unit -v

test-integration: ## Run backend integration tests only
	$(UV) run pytest src/tests/integration -v

test-cov: ## Run backend tests with coverage report
	$(UV) run pytest src/tests -v --cov=src/domain --cov=src/shared --cov=src/usecases --cov-report=term-missing

lint: ## Run ruff linter on src/
	$(UV) run ruff check src

format: ## Format Python code with ruff
	$(UV) run ruff format src

typecheck: ## Run mypy static type checker (requires mypy in environment)
	$(UV) run mypy src

check: lint test ## Run linter, format check, bytecode check, and test suite
	$(UV) run ruff format --check src
	$(UV) run python -m compileall -q src

clean: ## Remove Python caches and coverage artifacts
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	find src -type d -name "__pycache__" -exec rm -rf {} +
