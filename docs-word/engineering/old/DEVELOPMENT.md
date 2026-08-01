Investment OS Development Guide
1. Overview

Investment OS follows a Docker-first development model.

Developers only need:

    Docker

    Docker Compose

    Git

    Make

Python is never installed directly on the host.
2. First-Time Setup

Clone the repository.

Generate the dependency lock file (only needed if it is not already present):

make bootstrap

Build the containers:

make docker-build

Start the development environment:

make docker-up

Verify:

make status

3. Daily Workflow

Start services:

make docker-up

Open a backend shell:

make backend-shell

Run tests:

make test

Run quality checks:

make quality

Stop services:

make docker-down

4. Adding Dependencies

Install a package:

docker compose exec backend uv add pandas

Install a development dependency:

docker compose exec backend uv add --dev pytest-xdist

Commit:

    pyproject.toml

    uv.lock

Rebuild:

make docker-build

5. Docker Philosophy
Rebuild required

Rebuild the backend image when any of these change:

    Dockerfile.dev

    pyproject.toml

    uv.lock

    Python version

    OS packages

Otherwise, simply restart the containers if needed:

make docker-up

6. Source Code Changes

Application code is bind-mounted into the backend container.

Editing Python files does not require rebuilding the image. FastAPI's reload mechanism will pick up changes automatically.
7. Project Bootstrap

bootstrap is only intended for:

    creating a new repository

    regenerating a missing uv.lock

It is not part of the normal development workflow.
8. Quality Gate

Every commit should pass:

make format
make lint
make typecheck
make test

or simply:

make quality

9. Immutable Dockerfile Principle

Dockerfile.dev is infrastructure.

It should change only when:

    the Python runtime changes,

    the operating system packages change,

    or the build tooling changes.

It should not be modified for routine application development or when adding Python dependencies. Dependency changes belong in pyproject.toml and uv.lock, followed by rebuilding the image.
Final recommendation

all developer documentation are in docs/engineering/ directory 

docs/
└── engineering/
    ├── DEVELOPMENT.md
    ├── CODING_STANDARDS.md
    ├── ARCHITECTURE.md
    ├── TESTING.md
    ├── DATABASE.md
    └── RELEASE.md
