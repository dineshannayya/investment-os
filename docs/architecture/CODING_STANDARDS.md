# Coding Standards

**Project:** Investment OS

**Document Version:** 1.0

**Status:** Draft

**Owner:** Architecture Team

**Last Updated:** 2026-07-25

---

# 1. Purpose

This document defines the coding standards, conventions, and engineering practices for Investment OS.

Its objectives are to:

* ensure code consistency
* improve readability
* simplify maintenance
* reduce defects
* improve code review quality
* support long-term scalability

All contributors should follow these standards unless an approved architectural decision specifies otherwise.

---

# 2. Scope

These standards apply to:

* Backend code
* AI modules
* Database access
* API development
* Test code
* Utility modules
* Build scripts
* Automation scripts

Frontend coding standards may be documented separately.

---

# 3. Engineering Principles

Every implementation should strive to be:

* Simple
* Readable
* Modular
* Testable
* Maintainable
* Secure
* Performant
* Well documented

Readability should generally take precedence over clever or overly compact code.

---

# 4. Python Standards

## Supported Version

* Python 3.12 or later

## Style Guide

* Follow PEP 8
* Follow PEP 257 for docstrings
* Use Black for formatting
* Use Ruff for linting

## Maximum Line Length

* 100 characters

## Indentation

* Four spaces
* Do not use tabs

---

# 5. Naming Conventions

## Packages

* Lowercase
* Short and descriptive

Example:

```text
app/services
app/repositories
```

## Modules

* snake_case

Example:

```text
startup_service.py
investment_repository.py
```

## Classes

* PascalCase

Example:

```python
class StartupService:
    ...
```

## Functions

* snake_case

Example:

```python
def calculate_score():
    ...
```

## Variables

* snake_case

Example:

```python
investment_score
startup_name
```

## Constants

* UPPER_CASE

Example:

```python
DEFAULT_PAGE_SIZE = 50
```

---

# 6. Project Structure Rules

Every feature should follow the project architecture defined in ADR-0001.

Typical module layout:

```text
feature/

api.py
service.py
repository.py
schemas.py
models.py
exceptions.py
tests/
```

Responsibilities should not overlap across layers.

---

# 7. Import Standards

Import order:

1. Python standard library
2. Third-party packages
3. Project modules

Example:

```python
import logging

from fastapi import APIRouter

from app.services.startup_service import StartupService
```

Avoid:

* wildcard imports
* circular dependencies
* unused imports

---

# 8. Type Hints

Type hints are required for all public APIs.

Example:

```python
def create_startup(data: StartupCreate) -> Startup:
    ...
```

Use explicit return types.

Avoid untyped public functions.

---

# 9. Documentation Standards

Every public module should include:

* module docstring
* purpose

Public classes and functions should include concise docstrings describing:

* purpose
* parameters
* return value
* raised exceptions (where meaningful)

---

# 10. Error Handling

* Raise domain-specific exceptions.
* Avoid generic `Exception`.
* Do not silently ignore errors.
* Preserve exception context where useful.
* Centralize exception handling through the application's error framework.

---

# 11. Logging Standards

Use the shared logging framework.

Do not use `print()` for application logging.

Choose log levels appropriately:

* DEBUG
* INFO
* WARNING
* ERROR
* CRITICAL

Sensitive information must never be logged.

---

# 12. Configuration Standards

Configuration should be accessed through the centralized settings object.

Do not call `os.getenv()` directly from application code.

Configuration values should be:

* typed
* validated
* documented

---

# 13. API Development Standards

API endpoints should:

* validate requests
* delegate business logic to services
* return defined response schemas
* avoid direct database access

Business rules belong in the service layer.

---

# 14. Service Layer Standards

Services are responsible for:

* business logic
* orchestration
* validation beyond schema validation
* interaction with repositories and external systems

Services should not perform presentation logic.

---

# 15. Repository Standards

Repositories should:

* encapsulate data access
* expose clear persistence operations
* avoid business logic

Keep persistence concerns separate from application workflows.

---

# 16. Database Standards

* Use parameterized queries or ORM abstractions.
* Avoid raw SQL unless justified.
* Manage schema changes through migrations.
* Keep transactions explicit and well scoped.

---

# 17. Testing Standards

Every new feature should include automated tests.

Recommended structure:

```text
tests/
├── api/
├── services/
├── repositories/
├── integration/
└── fixtures/
```

Tests should be:

* isolated
* deterministic
* repeatable
* fast

---

# 18. Security Standards

Developers should:

* validate inputs
* sanitize outputs where appropriate
* avoid exposing sensitive data
* protect secrets
* use approved authentication mechanisms

Security-related changes should reference the appropriate security ADRs.

---

# 19. Performance Guidelines

Prefer:

* clear algorithms
* efficient data access
* bounded memory usage

Optimize only after identifying measurable bottlenecks.

---

# 20. Dependency Management

Before adding a dependency:

* evaluate maintenance status
* review licensing
* assess security posture
* check for existing alternatives within the project

Significant technology additions may require a new ADR.

---

# 21. Code Review Checklist

Reviewers should verify:

* architecture compliance
* naming consistency
* readability
* test coverage
* documentation updates
* error handling
* logging
* security considerations
* formatting and linting

---

# 22. Pull Request Requirements

Every pull request should:

* build successfully
* pass automated tests
* pass linting
* be formatted
* update documentation when applicable
* include related issue or ADR references where relevant

---

# 23. Anti-Patterns

Avoid:

* God classes
* duplicate logic
* hard-coded configuration
* hidden side effects
* excessive nesting
* long methods
* unused code
* commented-out code
* premature optimization

Refactor when these patterns emerge.

---

# 24. Related Documents

* ADR-0001 – Project Structure & Modular Architecture
* ADR-0002 – Coding Standards & Engineering Conventions
* ADR-0003 – Configuration Management Strategy
* ADR-0004 – Logging & Observability Strategy
* ADR-0005 – Testing Strategy & Quality Assurance
* SYSTEM_ARCHITECTURE.md
* TECHNOLOGY_STACK.md

---

# 25. Revision History

| Version | Date       | Description                       |
| ------- | ---------- | --------------------------------- |
| 1.0     | 2026-07-25 | Initial coding standards handbook |

