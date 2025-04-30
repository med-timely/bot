# Makefile
SHELL := /bin/bash
VENV_PATH := $(shell pipenv --venv 2>/dev/null)

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Environment setup
.PHONY: setup
setup:  ## Initialize pipenv environment
	pipenv --python 3.11
	pipenv install --dev

.PHONY: install
install:  ## Install dependencies from Pipfile.lock
	pipenv install --dev

# Dependency management
.PHONY: lock
lock:  ## Update Pipfile.lock
	pipenv lock

.PHONY: add
add:  ## Add new package (e.g. make add pkg=requests)
	pipenv install $(pkg)

# Development
.PHONY: run
run:  ## Run the bot
	pipenv run python -m src.bot

.PHONY: migrate
migrate:  ## Create new migration
	pipenv run alembic revision --autogenerate -m "$(message)"

.PHONY: upgrade
upgrade:  ## Apply migrations
	pipenv run alembic upgrade head

# Celery
.PHONY: celery-worker celery-beat celery

celery-worker:  ## Start Celery worker
	pipenv run celery -A src.tasks.celery worker --loglevel=info

celery-beat:  ## Start Celery beat scheduler
	pipenv run celery -A src.tasks.celery beat --loglevel=info

celery:  ## Start both Celery worker and beat (background)
	pipenv run celery -A src.tasks.celery worker --loglevel=info --detach
	pipenv run celery -A src.tasks.celery beat --loglevel=info --detach

# Maintenance
.PHONY: clean
clean:  ## Remove virtual environment and cached files
	pipenv --rm
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +

.PHONY: clean-migrations
clean-migrations:  ## Remove all migrations
	rm -rf src/database/migrations/versions/*

# Testing
.PHONY: test
test:  ## Run tests with coverage
	pipenv run pytest tests/ -v --cov=src --cov-report=term-missing