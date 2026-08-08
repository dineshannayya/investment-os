# Backend Architecture Guide

**Project:** Investment OS
**Version:** 1.0
**Status:** Living Document

---

# 1. Purpose

This document defines the architectural principles for the Investment OS backend.

The goal is to ensure that every new feature follows the same design philosophy, making the project:

* Maintainable
* Testable
* Extensible
* AI-friendly
* Production-ready

This document should be updated whenever a significant architectural decision is made.

---

# 2. High-Level Architecture

The backend follows a layered architecture.

```
                REST API
                   │
                   ▼
              API Endpoints
                   │
                   ▼
            Business Services
                   │
                   ▼
             Repositories
                   │
                   ▼
          SQLAlchemy ORM Models
                   │
                   ▼
                Database
```

Each layer has a single responsibility.

---

# 3. Layer Responsibilities

## API Layer (`app/api`)

Responsibilities

* HTTP endpoints
* Request validation
* Response serialization
* Dependency injection
* HTTP exception mapping
* Authentication / Authorization

The API layer **must not**

* contain business logic
* directly access SQLAlchemy
* execute database queries

The API communicates only with Services.

---

## Service Layer (`app/services`)

Responsibilities

* Business logic
* Validation
* Workflow orchestration
* Object construction
* Transaction boundaries

The Service layer

* converts DTOs into ORM models
* coordinates repositories
* raises business exceptions

The Service layer **must not**

* know anything about HTTP
* return HTTP responses
* raise HTTPException

---

## Repository Layer (`app/repositories`)

Responsibilities

* Database persistence
* Query construction
* CRUD operations

Repositories should never contain business rules.

Repositories should never commit transactions.

Repositories should only interact with SQLAlchemy.

---

## Model Layer (`app/models`)

Responsibilities

* SQLAlchemy ORM
* Relationships
* Constraints
* Indexes

Models should contain no business logic.

---

## Schema Layer (`app/schemas`)

Responsibilities

* Request DTOs
* Response DTOs
* Validation
* Serialization

Schemas should never contain persistence logic.

---

# 4. Dependency Flow

Allowed dependency direction

```
API
 ↓
Service
 ↓
Repository
 ↓
Model
```

Never reverse this direction.

Examples

✅ Allowed

```
Service
    ↓
Repository
```

❌ Not allowed

```
Repository
    ↓
Service
```

---

# 5. Database Transactions

Repositories never commit.

Only Services commit.

Example

```
API
    ↓
Service
    ├── Repository A
    ├── Repository B
    └── commit()
```

This ensures multi-step business operations remain atomic.

---

# 6. Dependency Injection

Every API endpoint receives Services through FastAPI dependency injection.

Example

```
Endpoint
    ↓
StartupService
    ↓
StartupRepository
```

Avoid constructing repositories directly inside endpoint methods.

---

# 7. DTO Rules

Incoming requests

```
StartupCreate
FounderCreate
InvestmentCreate
```

Outgoing responses

```
StartupResponse
FounderResponse
```

Services convert DTOs into ORM models.

Repositories work only with ORM models.

---

# 8. Exception Handling

Business Layer

Raise domain exceptions or ValueError.

```
DuplicateStartupError
StartupNotFoundError
ValidationError
```

API Layer

Translate business exceptions into HTTP responses.

```
DuplicateStartupError
    ↓
409 Conflict

StartupNotFoundError
    ↓
404 Not Found
```

Business logic must never import FastAPI.

---

# 9. Testing Philosophy

The project uses layered testing.

```
Models

Repositories

Services

API

Integration
```

Every layer is tested independently.

API tests validate

* routing
* serialization
* dependency injection
* authentication
* HTTP responses

Service tests validate

* business logic
* workflows
* transactions

Repository tests validate

* persistence
* queries
* constraints

---

# 10. Test Database

Testing uses

* SQLite in-memory
* StaticPool
* check_same_thread=False

Every test runs inside its own transaction.

The API uses the same SQLAlchemy session through dependency overrides.

---

# 11. Naming Conventions

Files

```
startup.py
founder.py
investment.py
```

Repositories

```
StartupRepository
FounderRepository
```

Services

```
StartupService
FounderService
```

Schemas

```
StartupCreate
StartupUpdate
StartupResponse
```

---

# 12. Folder Structure

```
app/

    api/

    core/

    models/

    repositories/

    schemas/

    services/
```

Tests mirror the application structure.

```
tests/

    api/

    core/

    models/

    repositories/

    schemas/

    services/
```

---

# 13. Coding Principles

Prefer composition over inheritance.

Keep functions small.

One public responsibility per class.

Explicit is better than implicit.

Avoid hidden side effects.

Fail early with meaningful exceptions.

---

# 14. AI Workspace Principles

The AI layer must not directly access SQLAlchemy.

The AI interacts only through Services.

```
AI Agent
      ↓
Service
      ↓
Repository
```

This allows

* deterministic testing
* future API exposure
* easier replacement of AI models

---

# 15. Future Modules

Every new domain should follow the same architecture.

Examples

```
Startup

Founder

Document

Investment

Opportunity

Portfolio

Analysis

Scoring

AI Workspace
```

No module should bypass the Service layer.

---

# 16. Architectural Rules

Always

✅ API → Service → Repository → Model

✅ Services own transactions

✅ Repositories never commit

✅ DTOs stop at the Service layer

✅ ORM objects never leave the Service layer unless returned as response models

✅ Tests for every layer

Never

❌ API → Repository

❌ Repository → Service

❌ HTTPException in Services

❌ Business logic inside Repositories

❌ SQLAlchemy inside Schemas

❌ Business rules inside Models

---

# 17. Current Backend Status

Completed

* Core framework
* Authentication
* Middleware
* Logging
* Exception handling
* Database infrastructure
* RBAC models
* Repository infrastructure
* Startup CRUD
* Comprehensive regression tests

Next Focus

* Founder management
* Document management
* Investment workflow
* AI Investment Workspace
* Startup scoring engine
* LLM-powered analysis

