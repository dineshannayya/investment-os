# ADR-0002: Coding Standards & Engineering Conventions

**ADR ID:** ADR-0002

**Title:** Coding Standards & Engineering Conventions

**Status:** Accepted

**Date:** 2026-07-25

**Authors:** Investment OS Engineering Team

**Phase:** Phase 1 – Backend Foundation

**Supersedes:** None

**Related Documents:**

* `PROJECT_BIBLE.md`
* `ADR-0001-Project-Structure.md`
* `CODING_STANDARDS.md`

---

# 1. Context

Investment OS is expected to evolve over many development phases and eventually involve multiple contributors.

Without common engineering standards, the project risks:

* inconsistent coding styles
* reduced readability
* difficult code reviews
* higher maintenance costs
* architectural drift

To ensure long-term maintainability, a common engineering standard is required.

---

# 2. Decision

Investment OS adopts a common set of engineering conventions covering:

* source code organization
* naming conventions
* formatting
* documentation
* testing
* API development
* dependency management
* code review expectations

These standards apply to all source code in the repository.

---

# 3. Objectives

The standards aim to:

* improve readability
* reduce review effort
* simplify onboarding
* maintain architectural consistency
* reduce technical debt
* improve code quality

---

# 4. General Engineering Principles

All code should be:

* readable
* maintainable
* testable
* modular
* deterministic
* well documented

Code should optimize for clarity before optimization.

---

# 5. Python Standards

Target Python Version

```text
Python 3.12+
```

Coding Style

* Follow PEP 8
* Follow PEP 257
* Use Black formatting
* Use Ruff linting

Maximum Line Length

```text
100 characters
```

Indentation

```text
4 spaces
```

Tabs are not permitted.

---

# 6. Type Hints

Type hints are mandatory for all public interfaces.

Example

```python
def create_startup(startup: StartupCreate) -> Startup:
    ...
```

Avoid untyped public functions.

---

# 7. Naming Conventions

## Variables

```python
startup_name
investment_score
```

snake_case

---

## Functions

```python
calculate_score()
generate_report()
```

snake_case

---

## Classes

```python
StartupService
FounderRepository
```

PascalCase

---

## Constants

```python
MAX_UPLOAD_SIZE
DEFAULT_PAGE_SIZE
```

UPPER_CASE

---

## Modules

```text
startup_service.py
report_generator.py
```

snake_case

---

## Packages

Lowercase only.

---

# 8. Project Layering

Each layer has a single responsibility.

```text
API
↓

Services
↓

Repositories
↓

Database
```

Business logic must remain inside Services.

Repositories perform persistence only.

---

# 9. API Standards

API routes should:

* validate input
* call services
* return schemas

Routes should not contain business logic.

Example

Good

```python
return startup_service.create(request)
```

Bad

```python
# SQL queries inside API route
```

---

# 10. Repository Standards

Repositories:

* CRUD operations
* queries
* transactions

Repositories should not:

* calculate business scores
* call AI
* perform workflow orchestration

---

# 11. Service Standards

Services contain:

* business rules
* workflows
* orchestration
* validation beyond schema validation

Services coordinate repositories and external integrations.

---

# 12. Schema Standards

Use Pydantic models for:

* requests
* responses
* validation

Never expose ORM models directly through APIs.

---

# 13. Documentation Standards

Every public module should include:

* module docstring
* purpose
* ownership

Public functions should include concise docstrings describing:

* purpose
* parameters
* return value
* exceptions (when significant)

---

# 14. Logging Standards

Use structured logging.

Do not use:

```python
print()
```

Always use the shared logger.

Log levels:

* DEBUG
* INFO
* WARNING
* ERROR
* CRITICAL

Sensitive information must never be logged.

---

# 15. Error Handling

Raise domain-specific exceptions.

Avoid generic:

```python
raise Exception(...)
```

Errors should be meaningful and actionable.

---

# 16. Testing Standards

Every feature should include automated tests.

Preferred structure:

```text
tests/

api/

services/

repositories/

core/
```

Testing goals:

* deterministic
* isolated
* repeatable
* fast

---

# 17. Dependency Management

Dependencies should be:

* minimal
* actively maintained
* version controlled

Avoid introducing libraries without clear justification.

---

# 18. Import Rules

Import order:

1. Standard Library

2. Third-party

3. Application modules

Example

```python
import logging

from fastapi import APIRouter

from app.services.startup_service import StartupService
```

Avoid wildcard imports.

---

# 19. Code Review Checklist

Every Pull Request should verify:

✓ Correct package

✓ Tests added

✓ Type hints present

✓ Documentation updated

✓ No dead code

✓ No duplicated logic

✓ Logging appropriate

✓ Lint passes

✓ Formatter passes

✓ Architecture respected

---

# 20. Forbidden Practices

The following are discouraged unless justified:

* wildcard imports
* circular dependencies
* business logic in API routes
* direct SQL inside services
* print() debugging
* hard-coded configuration
* duplicated utilities
* commented-out code
* unused imports

---

# 21. Tooling

Formatting

```text
Black
```

Linting

```text
Ruff
```

Testing

```text
pytest
```

Coverage

```text
pytest-cov
```

Static Typing (future)

```text
mypy
```

---

# 22. Quality Gates

Before merging:

* All tests pass.
* Ruff passes.
* Black formatting passes.
* Coverage target maintained.
* Documentation updated.
* No architectural violations.

---

# 23. Exceptions

Temporary deviations from these standards require:

* documented rationale
* code review approval
* follow-up backlog item if the deviation is expected to be removed later

---

# 24. Consequences

## Positive

* Consistent codebase.
* Faster reviews.
* Easier onboarding.
* Reduced maintenance cost.
* Improved testability.
* Better long-term scalability.

## Negative

* Slightly more upfront effort.
* Developers must learn and follow project conventions.

These trade-offs are acceptable for a long-lived engineering project.

---

# 25. Review Schedule

This ADR should be reviewed:

* annually
* when major tooling changes occur
* when introducing a new programming language
* when adopting significant new frameworks

---

# 26. Decision Summary

Investment OS adopts a unified set of coding standards and engineering conventions to ensure a consistent, maintainable, and scalable codebase.

These standards complement the architectural principles established in ADR-0001 and provide the day-to-day engineering rules that all contributors are expected to follow.

**Decision:** Accepted

**Effective Release:** v0.1.0 – Backend Foundation

