
#------------------------------------------------------------------------------
# Investment OS Backend Makefile
#------------------------------------------------------------------------------
# | Target        | Purpose                                          |
# | ------------- | ------------------------------------------------ |
# | `make sync`   | Install/synchronize dependencies from `uv.lock`  |
# | `make update` | Upgrade dependencies and regenerate the lockfile |
# | `make check`  | Run all quality checks                           |
# | `make run`    | Start the application                            |
#-------------------------------------------------------------------------------
# At every commit, the following should succeed:
# make format
# make lint
# make fix
# make test
# -----------------------------------------------------------------------------
# Docker command
#   If there is any change in Dockerfile, then rebuild using: docker-build
# -----------------------------------------------------------------------------
#
# After editing pyproject.toml
# docker compose run --rm backend uv lock
# 
# # Update the running venv
# docker compose exec backend uv sync
# docker compose build --no-cache backend
# docker compose up -d backend
#  ----------------------------------------------------------------------------


PYTHON := 3.12
DOCKER := docker compose exec backend
#UV := uv
UV ?= $(DOCKER) uv

.PHONY: help bootstrap sync update run cov lint fix format typecheck \
        verify  check ci clean shell freeze precommit db-up db-down \
        docker-up docker-down docker-build docker-logs docker-ps \
        backend-shell frontend-shell db-shell docker-rebuild docker-status docker-clean \
        test test-config

help:
	@echo "Available targets:"
	@echo "  install     Install project dependencies"
	@echo "  sync        Sync environment using uv"
	@echo "  update      Update dependencies"
	@echo "  run         Start FastAPI development server"
	@echo "  test        Run unit tests"
	@echo "  cov         Run tests with coverage"
	@echo "  lint        Run Ruff"
	@echo "  format      Format using Black"
	@echo "  typecheck   Run MyPy"
	@echo "  check       Run lint + typecheck + tests"
	@echo "  clean       Remove caches"
	@echo "  shell       Open uv shell"


# This needed for git repo which does not have prebit uv.lock file
bootstrap:
	@echo "Generating uv.lock..."
	docker run --rm \
		-v $(PWD)/backend:/workspace \
		-w /workspace \
		python:3.12-slim \
		bash -c "pip install -q uv && uv lock"
	@echo "Bootstrap complete."

sync:
	$(UV) sync

update:
	$(UV) lock --upgrade
	$(UV) sync

run:
	$(UV) run uvicorn app.main:app --reload

cov:
	$(UV) run pytest --cov=app --cov-report=term-missing

lint:
	$(UV) run ruff check .

fix:
	$(UV) run ruff check . --fix
	$(UV) run black .

format:
	$(UV) run black .

format-check:
	$(UV) run black --check .

typecheck:
	$(UV) run mypy app tests

verify :
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

check: format-check lint typecheck test

ci: check cov

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov
	rm -rf .coverage.*

shell:
	$(UV) run python

# -----------------------------------------------
# Alembic commands 
# Proposed Alembic update sequence 
#   initial_schema
#   add_permissions_table
#   add_user_roles_table
#   add_role_permissions_table
#
# To generate : make revision "initial_schema"
# 1. Generate migration
# make alembic_revision MSG="initial_schema"
# make alembic_revision MSG="add_permissions_table"
# make alembic_revision MSG="add_user_roles_table"
# make alembic_revision MSG="add_role_permissions_table"
# 
# 2. Review the generated migration
# vim alembic/versions/*.py
# 
# 3. Apply it
# make alembic_upgrade
# 
# 4. Verify current revision
# make alembic_current
# 
# 5. Run the test suite
# docker compose exec backend pytest tests -v
# 
# ----------------------------------------------

alembic_migrate:
	docker compose exec backend alembic upgrade head

alembic_revision:
	@test -n "$(MSG)" || (echo "Usage: make alembic_revision MSG=\"create_roles_table\"" && exit 1)
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

alembic_upgrade:
	docker compose exec backend alembic upgrade head

alembic_downgrade:
	docker compose exec backend alembic downgrade -1

alembic_current:
	docker compose exec backend alembic current

alembic_history:
	docker compose exec backend alembic history

alembic_heads:
	docker compose exec backend alembic heads

alembic_check:
	docker compose exec backend alembic check

# -------------------------------------
# Tests
# -------------------------------------

# make test-config → quick configuration tests
test-config:
	$(DOCKER) pytest tests -v

# make test → full backend test suite with coverage
test:
	$(DOCKER) pytest tests -v --cov=app --cov-report=term-missing


test-unit:
	$(DOCKER) pytest tests/models tests/core tests/config -v

test-api:
	$(DOCKER) pytest tests/api -v

test-all:
	$(DOCKER) pytest tests -v --cov=app

# --------------------------------
# Database
# --------------------------------

db-revision:
	$(UV) run alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	$(UV) run alembic upgrade head

db-downgrade:
	$(UV) run alembic downgrade -1

# Docker

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# After editing pyproject.toml
docker-rebuild:
	docker compose run --rm backend uv lock
	docker compose exec backend uv sync
	docker compose build --no-cache backend
	docker compose up -d backend


docker-build:
	docker compose build

docker-logs:
	docker compose logs -f

docker-ps:
	docker compose ps

backend-shell:
	docker compose exec backend bash

frontend-shell:
	docker compose exec frontend bash

db-shell:
	docker compose exec postgres psql -U investment investment_os


docker-status:
	docker compose ps

docker-clean:
	docker compose down -v


# -------------------
docx2md:
	python3 scripts/convert_docs.py \
	    --input docs-word \
	    --output docs

# coverage
coverage-html:
	$(DOCKER) pytest tests --cov=app --cov-report=html
