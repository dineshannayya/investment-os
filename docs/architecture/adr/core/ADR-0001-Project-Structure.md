# ADR-0001: Project Structure & Modular Architecture

**ADR ID:** ADR-0001

**Title:** Project Structure & Modular Architecture

**Status:** Accepted

**Date:** 2026-07-25

**Authors:** Investment OS Engineering Team

**Phase:** Phase 1 – Backend Foundation

**Related Documents:**

* `docs/architecture/PROJECT_BIBLE.md`
* `docs/roadmap/MASTER_ROADMAP.md`
* `docs/roadmap/PHASE_01_Backend_Foundation.md`

---

# 1. Context

Investment OS is intended to become an AI-native investment platform that will evolve over multiple years and multiple engineering phases.

The project is expected to grow from a relatively small backend into a platform containing:

* REST APIs
* Database layer
* AI orchestration
* RAG pipelines
* Background workers
* Document processing
* Authentication
* Reporting
* Frontend application

Without an explicit architectural foundation, the repository would gradually become difficult to maintain as new modules are introduced.

The project therefore requires an architecture that:

* scales with project growth
* supports incremental feature development
* minimizes coupling
* maximizes maintainability
* encourages automated testing
* supports future AI components

---

# 2. Problem Statement

How should the Investment OS repository be organized so that:

* business logic remains isolated
* infrastructure can evolve independently
* new contributors can onboard quickly
* future services can be extracted if necessary
* architectural drift is minimized

---

# 3. Decision

Investment OS will adopt a **Modular Monolith Architecture** using **FastAPI**.

The architecture combines ideas from:

* Clean Architecture
* Domain-Driven Design (DDD)
* Layered Architecture
* API-First Design

Business logic shall remain independent from:

* HTTP framework
* database implementation
* AI providers
* deployment platform

Infrastructure exists to support business logic—not the other way around.

---

# 4. Repository Structure

```
investment-os/

├── app/
│
├── tests/
│
├── docs/
│
├── scripts/
│
├── docker/
│
├── alembic/
│
├── pyproject.toml
├── Makefile
└── README.md
```

Application code resides entirely inside the `app/` package.

Everything outside `app/` is considered supporting infrastructure.

---

# 5. Application Layer Structure

```
app/

├── api/
├── core/
├── models/
├── schemas/
├── repositories/
├── services/
├── ai/
├── utils/
└── main.py
```

Each package has a single responsibility.

---

# 6. Package Responsibilities

## api/

Responsible for:

* HTTP endpoints
* request validation
* response generation
* API versioning

Must **not** contain business logic.

---

## core/

Responsible for:

* configuration
* middleware
* logging
* security
* startup
* dependency injection

Acts as the platform infrastructure.

---

## services/

Contains business logic.

Examples:

* startup analysis
* investment workflow
* report generation

Services orchestrate repositories and AI modules.

---

## repositories/

Responsible only for persistence.

Responsibilities:

* CRUD
* queries
* transactions

Repositories should not contain business rules.

---

## models/

Database entities.

Only persistence models belong here.

---

## schemas/

API request/response models.

Implemented using Pydantic.

Schemas are independent from ORM models.

---

## ai/

Contains:

* AI orchestration
* prompt management
* RAG
* vector search
* model abstraction

AI providers should be interchangeable.

---

## utils/

Small reusable helper functions.

Utilities must remain generic.

Business-specific code is not permitted.

---

# 7. Architectural Principles

The following principles are mandatory.

---

## Principle 1

Single Responsibility

Each module owns exactly one concern.

---

## Principle 2

Separation of Concerns

Business logic remains independent from infrastructure.

---

## Principle 3

Dependency Direction

Dependencies always point inward.

```
API
 ↓

Services
 ↓

Repositories
 ↓

Database
```

Infrastructure must never depend on business logic.

---

## Principle 4

Explicit Boundaries

Every package has clear ownership.

Avoid cross-package shortcuts.

---

## Principle 5

Testability

Every service should be independently testable.

External dependencies should be mockable.

---

## Principle 6

Documentation First

Architecture changes require:

* ADR update
* roadmap update
* changelog update (when user-visible)

---

# 8. Alternatives Considered

## Alternative A

Traditional Layered Project

Advantages

* Simple

Disadvantages

* Business logic spreads across controllers.
* Difficult to scale.
* Encourages tight coupling.

Decision

Rejected.

---

## Alternative B

Microservices

Advantages

* Independent deployment
* Service isolation

Disadvantages

* Operational complexity
* Increased infrastructure
* Distributed debugging

Decision

Rejected for initial releases.

May be reconsidered after significant growth.

---

## Alternative C

Modular Monolith

Advantages

* Clear boundaries
* Easier testing
* Lower operational cost
* Supports gradual migration

Decision

Accepted.

---

# 9. Consequences

## Positive

* Consistent repository layout
* Easier onboarding
* High maintainability
* Better testing
* Supports AI expansion
* Lower operational complexity

---

## Negative

* Requires discipline to preserve module boundaries.
* Additional documentation effort.
* Some architectural decisions require review before implementation.

These trade-offs are acceptable for a long-lived platform.

---

# 10. Development Rules

All future development must follow these rules.

### Rule 1

API endpoints call Services.

Never place business logic inside API routes.

---

### Rule 2

Services call Repositories.

Services should not perform direct SQL operations.

---

### Rule 3

Repositories access storage only.

No business calculations.

---

### Rule 4

Schemas remain separate from ORM models.

Never expose database entities directly through APIs.

---

### Rule 5

Configuration is centralized.

Environment variables are accessed through the configuration layer only.

---

### Rule 6

AI integrations use abstraction layers.

Business logic must not depend on a specific LLM provider.

---

### Rule 7

Each new feature must include:

* unit tests
* documentation updates
* appropriate changelog entry (if applicable)

---

# 11. Compliance Checklist

Every pull request should be reviewed against this checklist.

| Question                          | Required   |
| --------------------------------- | ---------- |
| Correct package?                  | ✓          |
| Business logic isolated?          | ✓          |
| Tests included?                   | ✓          |
| Documentation updated?            | ✓          |
| Circular dependencies introduced? | No         |
| Public API changed?               | Documented |

---

# 12. Future Impact

This decision establishes the architectural baseline for all future phases.

The following ADRs build upon this foundation:

* ADR-0002 — Configuration Management
* ADR-0003 — Coding Standards
* ADR-0004 — Logging Strategy
* ADR-0005 — Testing Strategy
* ADR-0101 — FastAPI Architecture
* ADR-0102 — Middleware Design
* ADR-0103 — Exception Handling
* ADR-0201 — Database Architecture
* ADR-0301 — AI Platform Architecture

---

# 13. Review Schedule

This ADR should be reviewed:

* after Phase 3 (Database & Persistence)
* before introducing microservices
* before major repository restructuring

Changes to the architectural direction should be recorded in a new ADR that supersedes this one rather than rewriting its historical decision.

---

# 14. Decision Summary

Investment OS adopts a **Modular Monolith Architecture** with clear separation between API, business logic, persistence, infrastructure, and AI components.

This decision provides a stable foundation for long-term growth while maintaining simplicity during the early phases of development.

**Decision:** Accepted

**Effective Release:** v0.1.0 – Backend Foundation

**Next Review:** After completion of Phase 3

