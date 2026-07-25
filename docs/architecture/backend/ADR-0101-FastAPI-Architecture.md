# ADR-0101: FastAPI Application Architecture

**ADR ID:** ADR-0101

**Title:** FastAPI Application Architecture

**Status:** Accepted

**Date:** 2026-07-25

**Authors:** Investment OS Engineering Team

**Phase:** Phase 2 – API Infrastructure

**Supersedes:** None

**Related Documents:**

* `SYSTEM_ARCHITECTURE.md`
* `TECHNOLOGY_STACK.md`
* `ADR-0001-Project-Structure.md`
* `ADR-0002-Coding-Standards.md`
* `ADR-0102-Exception-Handling-Strategy.md`
* `FASTAPI_DEVELOPMENT_GUIDE.md`

---

# 1. Context

Investment OS exposes its capabilities through REST APIs that will support:

* Web Frontend
* AI Services
* Future Mobile Applications
* External Integrations
* Internal Automation
* Background Services

As the platform grows, the API layer must remain:

* modular
* maintainable
* testable
* secure
* scalable

A consistent application architecture is required to prevent business logic from becoming tightly coupled to the web framework.

---

# 2. Problem Statement

The project must define:

* How should FastAPI be organized?
* Where should business logic reside?
* How should routers be structured?
* How should dependencies be managed?
* How should modules communicate?
* How should APIs evolve over time?

---

# 3. Decision

Investment OS adopts a **Modular FastAPI Architecture** based on **Clean Architecture** principles.

FastAPI is used exclusively as the presentation layer.

Business logic, persistence, and domain rules remain independent of the framework.

The application is organized into feature-oriented modules with clearly defined responsibilities.

---

# 4. Design Goals

The architecture should provide:

* Thin API layer
* Strong separation of concerns
* Feature modularity
* Framework independence
* High testability
* Consistent API design
* Future API versioning support

---

# 5. High-Level Architecture

```text
                 Client Applications
                         │
                 HTTPS / REST API
                         │
              +-----------------------+
              |       FastAPI         |
              |  Routers / Middleware |
              +-----------+-----------+
                          │
                 Application Services
                          │
                  Domain Services
                          │
                    Repositories
                          │
                     PostgreSQL
```

FastAPI is responsible only for HTTP concerns and request orchestration.

---

# 6. Layer Responsibilities

## API Layer

Responsible for:

* request parsing
* schema validation
* dependency injection
* authentication
* authorization
* response generation

The API layer must **not** contain business rules.

---

## Service Layer

Responsible for:

* business workflows
* orchestration
* validation beyond schema validation
* coordination across repositories
* interaction with AI services

---

## Repository Layer

Responsible for:

* persistence
* queries
* transactions

Repositories must not implement business workflows.

---

## Domain Layer

Responsible for:

* business entities
* business rules
* domain-specific validation
* reusable business concepts

---

# 7. Feature-Based Organization

Each feature owns its implementation.

Example:

```text
app/

modules/

    startups/
        api.py
        service.py
        repository.py
        schemas.py
        models.py
        exceptions.py
        tests/

    investors/
    deals/
    documents/
```

Features should be self-contained where practical.

---

# 8. Router Organization

Each feature exposes its own router.

Example:

```python
router = APIRouter(
    prefix="/startups",
    tags=["Startups"]
)
```

The application aggregates feature routers in a central registration module.

---

# 9. API Versioning

The architecture supports explicit API versioning.

Example:

```text
/api/v1/startups
/api/v1/investors
/api/v1/deals
```

Breaking API changes should result in a new version rather than modifying existing contracts.

---

# 10. Request Lifecycle

```text
Client Request
      │
      ▼
Middleware
      │
      ▼
Authentication
      │
      ▼
Validation
      │
      ▼
Router
      │
      ▼
Service
      │
      ▼
Repository
      │
      ▼
Database
      │
      ▼
Response
```

Cross-cutting concerns should be handled before business logic executes.

---

# 11. Dependency Injection

Dependencies should be injected using FastAPI's dependency system.

Typical dependencies include:

* configuration
* authentication
* database session
* current user
* service instances

Dependency injection should simplify testing and reduce coupling.

---

# 12. Schema Strategy

Pydantic models define API contracts.

Separate schemas should be used for:

* requests
* responses
* updates
* filters

Internal models should not be exposed directly through public APIs.

---

# 13. Middleware Strategy

Middleware is reserved for cross-cutting concerns such as:

* request logging
* correlation IDs
* timing
* CORS
* security headers
* exception translation

Business logic should never be implemented in middleware.

---

# 14. Error Handling

Errors should be handled centrally.

Routers should avoid repetitive `try/except` blocks.

Exceptions should propagate to the global exception handler defined by the project's exception strategy.

---

# 15. Background Tasks

Background processing should be used only for operations that do not affect the immediate API response.

Examples:

* email notifications
* audit logging
* asynchronous report generation

Critical business transactions should complete before the response is returned.

---

# 16. Alternatives Considered

## Option A – Fat Controllers

Business logic resides in route handlers.

Advantages:

* Simple for small projects

Disadvantages:

* Difficult to maintain
* Poor testability
* High coupling

Decision:

Rejected.

---

## Option B – Service-Oriented FastAPI

Business logic resides in service classes.

Advantages:

* Clear separation
* Easier testing
* Modular design
* Framework independence

Decision:

Accepted.

---

# 17. Consequences

## Positive

* Clean separation of responsibilities.
* Easier unit testing.
* Better scalability.
* Reduced framework coupling.
* Consistent API implementation.
* Improved maintainability.

## Negative

* More files per feature.
* Slightly higher initial development effort.

These trade-offs are acceptable for a long-lived engineering platform.

---

# 18. Compliance Rules

Every new API feature should:

* define its own router
* use request and response schemas
* delegate business logic to services
* isolate persistence in repositories
* include automated tests
* update API documentation

Business logic in route handlers is not permitted.

---

# 19. Future Enhancements

Future phases may introduce:

* API rate limiting
* GraphQL gateway
* WebSocket support
* OpenAPI customization
* asynchronous event processing
* distributed services

These enhancements should preserve the modular FastAPI architecture.

---

# 20. Review Schedule

Review this ADR:

* before introducing API version 2
* before migrating to microservices
* when adopting new transport protocols
* during major backend architecture reviews

---

# 21. Decision Summary

Investment OS adopts a **Modular FastAPI Architecture** in which FastAPI serves exclusively as the presentation layer.

The application is organized into feature-based modules with thin routers, service-oriented business logic, repository-based persistence, centralized dependency management, and clear separation of cross-cutting concerns. This architecture supports long-term maintainability, scalability, and framework independence while providing a consistent foundation for all backend APIs.

**Decision:** Accepted

**Effective Release:** Phase 2 – API Infrastructure

