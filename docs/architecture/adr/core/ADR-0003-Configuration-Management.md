# ADR-0003: Configuration Management Strategy

**ADR ID:** ADR-0003

**Title:** Configuration Management Strategy

**Status:** Accepted

**Date:** 2026-07-25

**Authors:** Investment OS Engineering Team

**Phase:** Phase 1 – Backend Foundation

**Supersedes:** None

**Related Documents:**

* `PROJECT_BIBLE.md`
* `ADR-0001-Project-Structure.md`
* `ADR-0002-Coding-Standards.md`
* `CONFIGURATION_GUIDE.md`

---

# 1. Context

Investment OS is designed to run across multiple environments, including:

* Local Development
* Testing
* Continuous Integration (CI)
* Staging
* Production

Each environment requires different runtime settings such as database connections, API keys, logging levels, feature flags, and AI provider credentials.

Managing configuration through hard-coded values or scattered environment access would reduce maintainability and increase operational risk.

A centralized configuration strategy is therefore required.

---

# 2. Problem Statement

The project must answer the following questions:

* How should configuration be loaded?
* How should secrets be managed?
* How should environments differ?
* How can configuration be validated?
* How can configuration be tested?
* How can developers safely add new settings?

---

# 3. Decision

Investment OS adopts a **centralized, environment-driven configuration model** based on **Pydantic Settings**.

Configuration shall be:

* centralized
* validated at startup
* strongly typed
* environment-aware
* immutable during runtime
* independent from business logic

No module should access environment variables directly.

---

# 4. Design Goals

The configuration system must provide:

* Type safety
* Validation
* Environment isolation
* Secure secret handling
* Consistent developer experience
* Easy testing
* Future cloud compatibility

---

# 5. Configuration Sources

Configuration values are resolved using the following precedence:

```text
Runtime Environment Variables
        │
        ▼
.env File
        │
        ▼
Default Values
```

Higher-priority sources override lower-priority values.

---

# 6. Configuration Architecture

```text
Application
      │
      ▼
Settings Object
      │
      ▼
Pydantic Settings
      │
      ▼
Environment Variables / .env
```

The application interacts only with the `Settings` object.

---

# 7. Repository Structure

```text
app/

core/

config/

    settings.py
    constants.py
    logging.py
```

Responsibilities:

### settings.py

Contains runtime configuration.

Examples:

* database URL
* host
* port
* JWT secret
* AI provider settings

### constants.py

Contains compile-time or project-wide constants.

Examples:

* default pagination size
* API version
* supported file extensions

Constants must never contain secrets.

---

# 8. Configuration Principles

## Principle 1

Single Source of Truth

All runtime configuration originates from one settings object.

---

## Principle 2

No Direct Environment Access

The following pattern is prohibited:

```python
import os

os.getenv("DATABASE_URL")
```

Instead:

```python
from app.core.config import settings

settings.database_url
```

---

## Principle 3

Strong Typing

All configuration values should have explicit types.

Example:

```python
database_url: str
debug: bool
api_port: int
```

---

## Principle 4

Startup Validation

Configuration errors must be detected during application startup rather than at runtime.

Examples include:

* Missing required values
* Invalid URLs
* Incorrect port numbers
* Unsupported environment names

---

## Principle 5

Immutable Runtime Configuration

Configuration should be initialized once during startup and treated as read-only throughout the application's lifecycle.

---

# 9. Environment Strategy

Supported environments:

| Environment | Purpose                   |
| ----------- | ------------------------- |
| Development | Local development         |
| Test        | Automated testing         |
| CI          | Continuous integration    |
| Staging     | Pre-production validation |
| Production  | Live deployment           |

Each environment should define only the values that differ from the defaults.

---

# 10. Secret Management

Secrets include:

* JWT signing keys
* Database passwords
* API tokens
* AI provider credentials
* Cloud storage credentials

Secrets:

* must never be committed to version control
* must never be stored in `constants.py`
* must be supplied through environment variables or a dedicated secret management system

Future production deployments may integrate with managed secret stores such as cloud key vaults.

---

# 11. Configuration Categories

Configuration should be grouped logically.

Examples:

### Application

* Name
* Version
* Environment

### API

* Host
* Port
* CORS

### Database

* Connection URL
* Pool size
* Timeout

### Logging

* Log level
* Format

### Authentication

* JWT configuration
* Token expiration

### AI

* Model provider
* Embedding provider
* API endpoints

### Storage

* Upload directory
* Maximum file size

---

# 12. Testing Strategy

Tests should not depend on production configuration.

Test suites may override configuration using dedicated test settings or fixtures.

Configuration behavior should be verified through automated tests, including:

* default values
* environment overrides
* validation failures

---

# 13. Error Handling

Configuration errors are considered startup failures.

The application should fail fast if required configuration is invalid or incomplete.

Examples:

* missing database URL
* invalid API key format
* unsupported environment
* malformed connection string

---

# 14. Alternatives Considered

## Option A – Direct `os.getenv()`

Advantages:

* Simple
* No dependencies

Disadvantages:

* No validation
* Weak typing
* Difficult testing
* Scattered configuration access

Decision:

Rejected.

---

## Option B – Configuration Dictionary

Advantages:

* Centralized

Disadvantages:

* No type checking
* Limited validation
* Easy to misuse

Decision:

Rejected.

---

## Option C – Pydantic Settings

Advantages:

* Strong typing
* Automatic validation
* Environment integration
* Clear developer experience
* Excellent FastAPI compatibility

Decision:

Accepted.

---

# 15. Consequences

## Positive

* Centralized configuration
* Improved reliability
* Easier testing
* Better security
* Strong validation
* Consistent deployment

## Negative

* Additional initial setup
* Developers must extend the settings model when introducing new configuration

These trade-offs are acceptable.

---

# 16. Compliance Rules

All new configuration values must:

* be added to the settings model
* include type annotations
* include sensible defaults where appropriate
* be documented
* include tests if validation behavior changes

Direct calls to `os.getenv()` outside the configuration layer are not permitted.

---

# 17. Migration Strategy

Future enhancements may include:

* cloud secret management
* dynamic feature flags
* runtime configuration refresh
* centralized configuration service

These enhancements should preserve the centralized configuration interface exposed to the application.

---

# 18. Review Schedule

Review this ADR:

* when introducing a new deployment environment
* before migrating to cloud secret management
* when adding significant configuration domains (e.g., AI providers or external integrations)

---

# 19. Decision Summary

Investment OS adopts a centralized, strongly typed, and validated configuration management strategy based on **Pydantic Settings**.

All runtime configuration is accessed through a single settings object, validated during startup, isolated from business logic, and designed to support secure deployment across multiple environments.

**Decision:** Accepted

**Effective Release:** v0.1.0 – Backend Foundation

