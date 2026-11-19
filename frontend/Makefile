.DEFAULT_GOAL := help

NPM ?= npm

.PHONY: help env install dev run build preview type-check test test-unit test-watch check clean

help: ## Show available frontend commands
	@awk 'BEGIN {FS = ":.*## "; printf "\nFrontend targets:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Create .env from env.template if it does not exist
	@if [ ! -f .env ]; then cp env.template .env && echo "Created .env from env.template"; else echo ".env already exists"; fi

install: ## Install npm dependencies
	$(NPM) install

dev: ## Start Vite development server (:5173)
	$(NPM) run dev

run: dev ## Alias for dev

build: ## Build production bundle
	$(NPM) run build

preview: ## Preview production build locally
	$(NPM) run preview

type-check: ## Run TypeScript type checking (vue-tsc)
	$(NPM) run type-check

test: ## Run frontend unit tests (Vitest)
	$(NPM) run test:unit

test-unit: test ## Alias for test

test-watch: ## Run frontend unit tests in watch mode
	$(NPM) run test:watch

check: type-check test build ## Run type-check, unit tests, and production build

clean: ## Remove build output
	rm -rf dist
