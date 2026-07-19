Investment OS Development Guide v1.0
1. Development Philosophy

Investment OS follows a Docker-first development model.

The host machine is responsible only for:

Docker Engine
Docker Compose
Git
VS Code (or preferred IDE)

No local Python installation is required. All development tools execute inside the backend container.

2. Project Layout
investment-os/
│
├── backend/
│   ├── Dockerfile.dev
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── app/
│   ├── tests/
│   └── requirements/          # Optional during migration
│
├── frontend/
│
├── docker-compose.yml
│
└── Makefile
3. Technology Stack
Component	Technology
Language	Python 3.12
Package Manager	uv
API	FastAPI
ASGI Server	Uvicorn
ORM	SQLAlchemy
Migration	Alembic
Database	PostgreSQL
Cache	Redis
Testing	Pytest
Lint	Ruff
Formatter	Black
Type Check	MyPy
4. Development Workflow
One-time bootstrap
make docker-build
make docker-up

This creates the development environment.

Daily development
make docker-up

Open a shell:

make docker-backend

Run tests:

make test

Run lint:

make lint

Format:

make format
5. Dependency Management

All dependencies are managed by uv.

Add a package
docker compose exec backend uv add pandas
Add a development package
docker compose exec backend uv add --dev pytest-xdist
Remove a package
docker compose exec backend uv remove pandas

This updates both:

pyproject.toml
uv.lock

Commit both files.

6. Docker Rules
Rebuild Docker only when:
Dockerfile changes
OS packages change
Python version changes
pyproject.toml changes
uv.lock changes

Otherwise:

make docker-up

is sufficient.

7. Makefile Responsibilities

The Makefile should only provide convenient shortcuts.

Examples:

make docker-build
make docker-up
make docker-down

make test
make lint
make format

make backend-shell

Avoid embedding business logic in the Makefile.

8. Coding Standards
Python 3.12
Black formatting
Ruff linting
MyPy type checking
Pytest unit tests
Feature branches
Pull Request reviews
9. Dependency Update Workflow

Normal development:

pyproject.toml
        │
        ▼
uv add/remove
        │
        ▼
uv.lock
        │
        ▼
git commit
        │
        ▼
docker build

uv.lock is treated as a source-controlled artifact and should always be committed alongside pyproject.toml.

10. Docker Image Lifecycle
Dockerfile.dev
        │
        ▼
docker build
        │
        ▼
Docker Image
        │
        ▼
docker compose up
        │
        ▼
Running Container

Changing the Dockerfile or dependency files requires rebuilding the image before recreating the container.
