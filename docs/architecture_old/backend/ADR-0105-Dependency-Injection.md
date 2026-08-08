# ADR-0105: Dependency Injection

**ADR ID:** ADR-0105

**Title:** Dependency Injection

**Status:** Accepted

**Date:** 2026-07-25

**Authors:** Investment OS Engineering Team

**Phase:** Phase 2 – API Infrastructure

**Supersedes:** None

**Related Documents:**

* ADR-0101 – FastAPI Architecture
* ADR-0102 – Middleware Architecture
* ADR-0103 – Exception Handling
* ADR-0104 – Response Envelope
* ADR-0106 – API Versioning
* CODING_STANDARDS.md
* FASTAPI_DEVELOPMENT_GUIDE.md

---

# 1. Context

Investment OS is designed as a modular backend composed of independent feature modules and layered application components.

Core application components include:

* API Routers
* Application Services
* Repositories
* Database Sessions
* Configuration
* Authentication Providers
* AI Services
* External Service Clients

These components depend on one another to fulfill business workflows.

Without a consistent dependency management strategy, components become tightly coupled, difficult to test, and harder to replace or extend.

---

# 2. Problem Statement

The platform must define:

* How are application components connected?
* Who creates service objects?
* How are repositories provided?
* How is configuration shared?
* How are database sessions managed?
* How are dependencies replaced during testing?

---

# 3. Decision

Investment OS adopts **Dependency Injection (DI)** as the standard mechanism for constructing and supplying application dependencies.

Application components receive their required collaborators through dependency injection rather than creating them directly.

Object construction is separated from business logic.

---

# 4. Design Goals

The dependency injection architecture should:

* reduce coupling
* improve modularity
* simplify testing
* centralize object construction
* improve maintainability
* support future extensibility
* remain framework-independent where practical

---

# 5. Architectural Principles

## Inversion of Control

Components declare what they require rather than creating those dependencies.

---

## Constructor-Based Design

Dependencies should be supplied during object construction whenever practical.

---

## Single Responsibility

Components should focus on business behavior rather than object creation.

---

## Explicit Dependencies

Dependencies should be visible through public interfaces rather than hidden within implementations.

---

## Replaceability

Any dependency should be replaceable with another implementation without affecting consumers.

---

# 6. Dependency Architecture

```text
                 FastAPI Router
                       │
                       ▼
              Dependency Provider
                       │
                       ▼
                 Application Service
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
    Repository                 AI Service
          │                         │
          ▼                         ▼
     Database Session        External Provider
```

The dependency provider assembles application components while business logic remains unaware of the construction process.

---

# 7. Dependency Categories

The application recognizes several dependency categories.

## Infrastructure

Examples:

* Database Session
* Configuration
* Logger
* Cache
* Storage Client

---

## Application Services

Examples:

* Startup Service
* Investor Service
* Portfolio Service
* Report Service

---

## Repository Layer

Examples:

* Startup Repository
* Investor Repository
* Investment Repository

---

## External Services

Examples:

* AI Providers
* Email Providers
* Market Data Services
* Notification Services

---

## Security Components

Examples:

* Authentication Provider
* Authorization Provider
* Current User Context

---

# 8. Dependency Lifetime

Dependencies should have an appropriate lifecycle based on their responsibility.

Typical categories include:

* Application-wide shared components
* Request-scoped components
* Short-lived operation-specific components

The lifecycle should be chosen to ensure correctness, performance, and resource efficiency.

---

# 9. Dependency Ownership

Application components should not create other application components directly.

Examples of responsibilities:

* Routers receive services.
* Services receive repositories.
* Repositories receive infrastructure resources.
* Infrastructure components are supplied by dependency providers.

This preserves the layered architecture defined in ADR-0101.

---

# 10. Testing Strategy

Dependency Injection enables testing by replacing production dependencies with test implementations.

Examples include:

* Mock repositories
* In-memory services
* Test database sessions
* Stub AI providers
* Fake authentication providers

Business logic should remain unchanged regardless of the supplied implementation.

---

# 11. Configuration Integration

Configuration is treated as an injectable dependency.

Application components should receive configuration through dependency providers rather than reading environment variables directly.

This supports:

* centralized configuration
* validation
* testing
* environment portability

---

# 12. Database Integration

Database access should be provided through injected database sessions.

Application services should never create database connections directly.

Connection lifecycle management remains the responsibility of the infrastructure layer.

---

# 13. AI Service Integration

AI providers should be injected as abstractions rather than referenced directly.

This enables:

* provider replacement
* local model execution
* cloud model execution
* testing without external services

The application remains independent of specific AI vendors.

---

# 14. Alternatives Considered

## Option A – Direct Object Construction

Each component creates its own dependencies.

### Advantages

* Simple for small applications.

### Disadvantages

* Tight coupling.
* Difficult testing.
* Poor maintainability.
* Limited extensibility.

**Decision:** Rejected.

---

## Option B – Dependency Injection

Dependencies are created externally and supplied to consumers.

### Advantages

* Loose coupling.
* Easier testing.
* Better modularity.
* Centralized lifecycle management.
* Improved extensibility.

**Decision:** Accepted.

---

# 15. Consequences

## Positive

* Improved testability.
* Reduced coupling.
* Better separation of concerns.
* Easier maintenance.
* Flexible component replacement.
* Consistent application architecture.

## Negative

* Additional architectural abstraction.
* Requires clear dependency boundaries.
* Poorly designed dependency graphs can become difficult to understand.

These trade-offs are acceptable for a production-grade platform.

---

# 16. Compliance Rules

Application components shall:

* receive dependencies rather than construct them
* avoid direct instantiation of repositories or services
* expose dependencies explicitly
* avoid hidden global state
* support dependency replacement during testing
* preserve layer boundaries

Framework-specific dependency configuration should remain outside business logic.

---

# 17. Future Enhancements

Future improvements may include:

* dependency provider modules
* service factories
* plugin architecture
* feature-based dependency registration
* background worker dependency scopes
* event handler dependency injection

These enhancements should preserve the dependency inversion principles established by this ADR.

---

# 18. Review Schedule

Review this ADR when:

* introducing plugin architectures
* adopting distributed services
* introducing background processing frameworks
* changing dependency management mechanisms
* migrating to a different application framework

---

# 19. Decision Summary

Investment OS adopts Dependency Injection as the architectural mechanism for constructing and supplying application components.

Dependencies are created outside business logic and supplied to consumers through explicit interfaces. This approach reduces coupling, improves testability, simplifies maintenance, and supports long-term extensibility while preserving the layered architecture defined in ADR-0101.

**Decision:** Accepted

**Effective Release:** Phase 2 – API Infrastructure

