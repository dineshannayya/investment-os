# ADR-0001: Project Structure and Architectural Foundation

**Status:** Accepted

**Date:** 2026-07-25

**Decision Makers:** Engineering Team

**Supersedes:** None

**Superseded By:** None

---

# Context

Investment OS is envisioned as a long-term, AI-native investment platform that will evolve over multiple development phases. The project is expected to grow significantly in terms of features, codebase size, contributors, and supported deployment environments.

Without a well-defined project structure, the codebase risks becoming difficult to maintain, increasing the cost of onboarding, testing, and future enhancements.

The project requires an architecture that:

* Supports long-term maintainability.
* Encourages clear separation of concerns.
* Enables incremental feature development.
* Facilitates automated testing.
* Scales from a single developer to a multi-engineer team.
* Supports future AI capabilities without major restructuring.

This ADR establishes the foundational project structure and architectural principles for all future development.

---

# Decision

Investment OS will adopt a **modular monolithic architecture** built on **FastAPI**, following principles from **Clean Architecture** and **Domain-Driven Design (DDD)** where appropriate.

The repository will be organized into clearly separated layers:

* API Layer
* Core Infrastructure
* Domain Services
* Data Access
* AI Platform
* Shared Utilities
* Tests
* Documentation

Business logic will remain independent of infrastructure concerns such as web frameworks, databases, and AI providers.

---

# Repository Structure

```text
investment-os/

├── app/
│   ├── api/
│   ├── core/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   ├── schemas/
│   ├── ai/
│   └── utils/
│
├── tests/
├── docs/
├── scripts/
├── docker/
├── alembic/
├── pyproject.toml
├── Makefile
└── README.md
```

This structure provides a clear separation between application code, infrastructure, documentation, tooling, and operational assets.

---

# Architectural Principles

The following principles govern the project:

### 1. Modular Design

Each package should have a single, well-defined responsibility.

Modules should be cohesive and loosely coupled.

---

### 2. Separation of Concerns

Infrastructure, business logic, and presentation logic must remain independent wherever practical.

Business rules should not depend directly on framework-specific APIs.

---

### 3. API-First Development

All platform capabilities are exposed through well-defined APIs.

The frontend, automation tools, and AI agents should interact through the same API contracts.

---

### 4. Configuration as Code

Runtime behavior is controlled through centralized configuration.

Configuration should be environment-aware and validated during application startup.

---

### 5. Documentation-Driven Development

Architectural decisions, project phases, and release milestones must be documented alongside implementation.

Documentation is treated as a first-class engineering artifact.

---

### 6. Testability

Code should be designed to support isolated unit testing.

Dependencies should be injectable or abstracted where practical.

Automated testing is mandatory for new functionality.

---

### 7. AI Provider Independence

The platform should not be tightly coupled to any specific LLM or embedding provider.

AI integrations should be implemented behind abstraction layers to allow future replacement or extension.

---

# Alternatives Considered

## Option 1 – Simple Layered Application

Advantages:

* Easy to understand.
* Minimal initial complexity.

Disadvantages:

* Business logic tends to become tightly coupled with infrastructure.
* Difficult to scale as the project grows.

Decision:

Rejected due to long-term maintainability concerns.

---

## Option 2 – Microservices

Advantages:

* Independent deployment.
* Service isolation.
* Technology flexibility.

Disadvantages:

* Operational complexity.
* Increased infrastructure overhead.
* Premature for the current project stage.

Decision:

Rejected for the initial implementation.

Microservices may be reconsidered after significant platform growth.

---

## Option 3 – Modular Monolith (Selected)

Advantages:

* Clear separation of concerns.
* Easier development and debugging.
* Lower operational complexity.
* Supports gradual extraction into services if required.

Decision:

Accepted.

---

# Consequences

## Positive

* Clear project organization.
* Simplified onboarding for new contributors.
* Consistent engineering practices.
* Easier automated testing.
* Supports future AI modules.
* Reduces architectural drift over time.

---

## Negative

* Requires discipline to maintain module boundaries.
* Additional documentation effort.
* Some initial design overhead.

These trade-offs are considered acceptable given the project's long-term goals.

---

# Implementation Guidelines

Future contributions should follow these rules:

* New business functionality belongs in the appropriate domain module.
* Infrastructure concerns should remain in `core`, `repositories`, or integration packages.
* API endpoints should delegate business logic to service classes.
* Shared utilities should avoid business-specific behavior.
* Circular dependencies between modules are not permitted.

---

# Compliance

Architecture reviews should verify that:

* New modules respect the defined package boundaries.
* Business logic does not directly depend on infrastructure implementations.
* Tests accompany new functionality.
* Documentation is updated when structural changes are introduced.

Non-compliant changes should be refactored before merge unless an explicit exception is approved.

---

# Related Documents

* `docs/architecture/PROJECT_BIBLE.md`
* `docs/roadmap/MASTER_ROADMAP.md`
* `docs/project/BACKLOG.md`
* `docs/project/MILESTONES.md`

Future ADRs expected:

* ADR-0002 – Configuration Management
* ADR-0003 – Logging Framework
* ADR-0004 – Middleware Architecture
* ADR-0005 – Exception Handling Strategy
* ADR-0006 – API Response Standard
* ADR-0007 – Database Access Pattern
* ADR-0008 – AI Provider Abstraction

---

# Review Schedule

This ADR should be reviewed:

* At the completion of Phase 3 (Database & Persistence).
* Before introducing any microservice architecture.
* Before major repository restructuring.

Changes to this ADR require approval through a new ADR rather than editing the historical decision directly.

---

# Decision Summary

The project adopts a **modular monolithic architecture** with clear separation between API, domain, infrastructure, AI, and persistence layers. This approach provides a balance between simplicity and long-term scalability while minimizing operational complexity during the early stages of Investment OS.

**Decision:** Accepted

**Effective From:** v0.1.0 – Backend Foundation

