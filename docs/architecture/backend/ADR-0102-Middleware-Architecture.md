i# ADR-0102: Middleware Architecture

**ADR ID:** ADR-0102

**Title:** Middleware Architecture

**Status:** Accepted

**Date:** 2026-07-25

**Authors:** Investment OS Engineering Team

**Phase:** Phase 2 – API Infrastructure

**Supersedes:** None

**Related Documents:**

* ADR-0101 – FastAPI Architecture
* ADR-0103 – Exception Handling
* ADR-0105 – Dependency Injection
* ADR-0106 – API Versioning
* SYSTEM_ARCHITECTURE.md
* FASTAPI_DEVELOPMENT_GUIDE.md

---

# 1. Context

Investment OS exposes REST APIs that are consumed by:

* Web applications
* AI services
* Internal automation
* Future mobile applications
* Third-party integrations

Every HTTP request requires common processing before reaching business logic. Examples include:

* request identification
* structured logging
* request timing
* security headers
* CORS handling
* correlation IDs
* request context

Without a common architecture, these concerns would be duplicated across API endpoints, leading to inconsistent behavior and increased maintenance.

---

# 2. Problem Statement

The platform requires a consistent mechanism to process all incoming HTTP requests.

Key architectural questions include:

* Which responsibilities belong in middleware?
* What execution order should middleware follow?
* How should middleware interact with routing and exception handling?
* How can cross-cutting concerns remain independent of business logic?

---

# 3. Decision

Investment OS adopts a centralized middleware pipeline.

Middleware is responsible only for framework-level, cross-cutting concerns that apply uniformly to all HTTP requests.

Business rules, domain workflows, persistence logic, and application-specific validation are explicitly excluded from middleware.

---

# 4. Design Goals

The middleware architecture should:

* eliminate duplicated infrastructure code
* provide a consistent request lifecycle
* improve observability
* improve security
* simplify maintenance
* minimize request overhead
* remain independent of business logic

---

# 5. Architectural Principles

The middleware architecture follows these principles:

## Single Responsibility

Each middleware component performs one technical concern.

---

## Stateless Processing

Middleware should not maintain application state.

---

## Framework-Level Processing

Middleware operates on HTTP requests and responses rather than domain entities.

---

## Composability

Middleware components should be independently enabled, disabled, or extended.

---

## Predictable Execution

Middleware ordering should be deterministic and documented.

---

# 6. Request Processing Pipeline

```text
                    HTTP Request
                          │
                          ▼
                Trusted Host Validation
                          │
                          ▼
                   Security Headers
                          │
                          ▼
                        CORS
                          │
                          ▼
                 Correlation ID
                          │
                          ▼
                  Request Logging
                          │
                          ▼
                 Performance Timer
                          │
                          ▼
                 Authentication Context
                          │
                          ▼
                 FastAPI Route Handler
                          │
                          ▼
                    Service Layer
                          │
                          ▼
                 Exception Handling
                          │
                          ▼
                   Response Envelope
                          │
                          ▼
                    HTTP Response
```

This pipeline establishes the standard request lifecycle for all backend APIs.

---

# 7. Middleware Responsibilities

Middleware may perform responsibilities including:

* Request ID generation
* Correlation ID propagation
* Structured request logging
* Performance timing
* Security header injection
* CORS configuration
* Compression
* Trusted host validation
* Request context initialization

These concerns apply uniformly across the application and do not depend on business functionality.

---

# 8. Responsibilities Excluded from Middleware

The following responsibilities shall not be implemented in middleware:

* Business validation
* Domain rules
* Database queries
* Repository operations
* Investment workflows
* AI inference
* Portfolio calculations
* Startup evaluation logic

Such responsibilities belong to the application and domain layers defined in ADR-0101.

---

# 9. Middleware Ordering

Middleware execution order shall be consistent across all deployments.

Recommended execution sequence:

1. Trusted Host Validation
2. Security Headers
3. CORS
4. Request Correlation
5. Request Logging
6. Performance Timing
7. Authentication Context
8. FastAPI Routing
9. Exception Translation
10. Response Generation

Architectural changes to the execution order should be reviewed before implementation.

---

# 10. Integration with Other Components

Middleware integrates with:

### FastAPI Architecture

Provides the common request pipeline before route execution.

### Exception Handling

Unhandled exceptions are propagated to the centralized exception handling framework.

### Dependency Injection

Middleware establishes request context used by dependency providers.

### Response Envelope

Middleware should not modify application responses except where required for infrastructure concerns such as response headers.

---

# 11. Security Considerations

Middleware contributes to platform security by supporting:

* security headers
* CORS enforcement
* trusted host validation
* HTTPS-aware processing
* request tracing

Authentication and authorization decisions remain outside middleware except for establishing request context.

---

# 12. Observability

Middleware is the preferred location for infrastructure-level observability.

Examples include:

* request duration
* request identifiers
* correlation IDs
* structured access logs
* response status metrics

Business metrics should be collected within application services rather than middleware.

---

# 13. Alternatives Considered

## Option A – Route-Level Processing

Each API endpoint performs logging, timing, and request processing independently.

### Advantages

* Simple implementation for very small projects.

### Disadvantages

* Code duplication.
* Inconsistent behavior.
* Difficult maintenance.
* Poor scalability.

**Decision:** Rejected.

---

## Option B – Centralized Middleware Pipeline

Shared request processing through a common middleware architecture.

### Advantages

* Consistent request handling.
* Better maintainability.
* Centralized observability.
* Reduced duplication.
* Improved extensibility.

**Decision:** Accepted.

---

# 14. Consequences

## Positive

* Consistent infrastructure behavior.
* Cleaner route handlers.
* Improved observability.
* Easier maintenance.
* Better separation of concerns.
* Reusable request processing.

## Negative

* Additional request processing overhead.
* Middleware ordering becomes architecturally significant.
* Debugging may require understanding the middleware chain.

These trade-offs are acceptable for a production-grade backend platform.

---

# 15. Compliance Rules

Every middleware implementation shall:

* perform one responsibility
* remain stateless
* avoid business logic
* avoid repository access
* avoid domain calculations
* support automated testing
* integrate with centralized logging
* document execution order dependencies

---

# 16. Future Enhancements

Future middleware capabilities may include:

* API rate limiting
* request throttling
* distributed tracing
* tenant resolution
* localization
* feature flag resolution
* audit logging
* request caching

Future additions should preserve the single-responsibility architecture.

---

# 17. Review Schedule

Review this ADR when:

* introducing an API gateway
* adopting distributed services
* introducing multi-tenancy
* significantly modifying the request lifecycle
* migrating to a different web framework

---

# 18. Decision Summary

Investment OS adopts a centralized middleware architecture to manage HTTP request processing through a consistent, framework-level pipeline.

Middleware is reserved exclusively for cross-cutting technical concerns such as request tracing, logging, security, and infrastructure processing. Business logic, domain rules, and persistence remain outside middleware, ensuring a clear separation of responsibilities and a maintainable backend architecture.

**Decision:** Accepted

**Effective Release:** Phase 2 – API Infrastructure

