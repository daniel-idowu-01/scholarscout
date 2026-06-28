.PHONY: help install dev prod migrate migrate-create test lint format typecheck clean \
        docker-up docker-down docker-build docker-logs docker-ps \
        crawl-university index-opportunities seed

PYTHON := python
PYTEST := pytest
UV := uv
ALEMBIC := alembic
DOCKER_COMPOSE := docker compose

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────────────

install: ## Install all dependencies
	$(UV) sync --all-extras

install-playwright: ## Install Playwright browsers
	$(PYTHON) -m playwright install chromium firefox
	$(PYTHON) -m playwright install-deps

dev-setup: install install-playwright ## Full dev environment setup
	cp -n .env.example .env || true
	pre-commit install

# ── Docker ─────────────────────────────────────────────────

docker-up: ## Start all services
	$(DOCKER_COMPOSE) up -d

docker-up-infra: ## Start only infrastructure services
	$(DOCKER_COMPOSE) up -d postgres redis minio minio-setup opensearch

docker-down: ## Stop all services
	$(DOCKER_COMPOSE) down

docker-destroy: ## Stop and remove all volumes
	$(DOCKER_COMPOSE) down -v

docker-build: ## Build application images
	$(DOCKER_COMPOSE) build api worker-crawler worker-extraction worker-notifications

docker-logs: ## Tail logs (specify SERVICE=api for specific service)
	$(DOCKER_COMPOSE) logs -f $(SERVICE)

docker-ps: ## Show running containers
	$(DOCKER_COMPOSE) ps

# ── Database ───────────────────────────────────────────────

migrate: ## Run pending migrations
	$(ALEMBIC) upgrade head

migrate-create: ## Create a new migration (set MSG="description")
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	$(ALEMBIC) downgrade -1

migrate-history: ## Show migration history
	$(ALEMBIC) history

migrate-current: ## Show current migration
	$(ALEMBIC) current

db-shell: ## Open psql shell
	$(DOCKER_COMPOSE) exec postgres psql -U scholarscout -d scholarscout

# ── Application ────────────────────────────────────────────

run: ## Run the API server (development)
	uvicorn scholarscout.main:app --reload --host 0.0.0.0 --port 8000

run-worker-crawler: ## Run the crawler worker
	celery -A scholarscout.contexts.crawler.workers.celery_app worker \
		--queues=crawl.high,crawl.normal,crawl.low \
		--concurrency=4 --loglevel=info

run-worker-extraction: ## Run the extraction worker
	celery -A scholarscout.contexts.crawler.workers.celery_app worker \
		--queues=extraction.high,extraction.normal \
		--concurrency=2 --loglevel=info

run-beat: ## Run the Celery beat scheduler
	celery -A scholarscout.contexts.crawler.workers.celery_app beat --loglevel=info

run-flower: ## Run Celery Flower monitoring
	celery -A scholarscout.contexts.crawler.workers.celery_app flower --port=5555

# ── Data Operations ────────────────────────────────────────

seed: ## Seed initial university data
	$(PYTHON) -m scholarscout.scripts.seed_universities

crawl-university: ## Crawl a university (set DOMAIN=mit.edu)
	$(PYTHON) -m scholarscout.scripts.crawl_university --domain $(DOMAIN)

index-rebuild: ## Rebuild OpenSearch indexes
	$(PYTHON) -m scholarscout.scripts.rebuild_index

# ── Code Quality ───────────────────────────────────────────

test: ## Run all tests
	$(PYTEST) tests/ -v

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/ -v

test-integration: ## Run integration tests (requires running infra)
	$(PYTEST) tests/integration/ -v

test-coverage: ## Run tests with coverage report
	$(PYTEST) tests/ --cov=src/scholarscout --cov-report=html --cov-report=term

lint: ## Lint code
	ruff check src/ tests/

lint-fix: ## Lint and auto-fix
	ruff check --fix src/ tests/

format: ## Format code
	ruff format src/ tests/

typecheck: ## Run type checking
	mypy src/

quality: lint typecheck ## Run all quality checks

# ── Maintenance ────────────────────────────────────────────

clean: ## Remove build artifacts and cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ dist/ build/

generate-secret: ## Generate a secure secret key
	$(PYTHON) -c "import secrets; print(secrets.token_urlsafe(64))"
