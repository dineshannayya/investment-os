# Investment OS Architecture Principles

## Purpose

Investment OS is an **AI-assisted startup investment analysis platform**. The system is designed to help analyze investment opportunities using structured data, AI-powered extraction, and repeatable investment workflows.

The project prioritizes maintainability, testability, and incremental evolution over rapid feature development.

---

# 1. Architecture Stability

The project follows an evolutionary architecture.

Existing project structure should be extended rather than redesigned.

The current application layers remain the foundation of the system:

```
app/
├── api/
├── core/
├── models/
├── repositories/
├── schemas/
├── services/
├── utils/
```

AI capabilities are added as a new domain:

```
app/
└── analysis/
    ├── agents/
    ├── extractors/
    ├── pipelines/
    ├── scoring/
    ├── prompts/
    └── services/
```

Existing modules should not be moved or rewritten unless there is a compelling architectural reason.

---

# 2. Layered Design

All new functionality follows the same implementation flow.

```
Model
    ↓
Migration
    ↓
Repository
    ↓
Service
    ↓
API
```

Business logic belongs inside Services.

Database access belongs inside Repositories.

API endpoints should orchestrate services and avoid implementing business logic.

Models remain focused on representing domain entities.

---

# 3. Database Evolution

Database schema changes are managed exclusively through Alembic.

Every schema modification follows this workflow:

```
Update Model
        ↓
Generate Alembic Revision
        ↓
Review Migration
        ↓
Apply Migration
        ↓
Run Regression Tests
```

Schema updates must never rely on automatic table creation.

Each migration should represent a single logical change.

---

# 4. Test-Driven Development

Regression stability is a primary project objective.

Every new feature must include appropriate automated tests.

Recommended implementation sequence:

```
Model Tests
Repository Tests
Service Tests
API Tests
Integration Tests
```

New functionality must not reduce overall test quality.

Regression tests are considered part of the feature implementation.

---

# 5. Repository Pattern

Repositories are the only layer responsible for persistence.

```
Database
    ↑
Repository
    ↑
Service
```

Services should never contain direct SQLAlchemy session management.

This separation improves maintainability and enables easier testing.

---

# 6. AI Architecture

AI functionality is implemented as an independent domain.

```
Application
        ↓
Analysis Service
        ↓
AI Agents
        ↓
Repositories
        ↓
Database
```

AI agents must not directly manipulate database sessions.

They receive structured inputs and return structured outputs.

---

# 7. Structured Data First

AI processing follows a structured pipeline.

```
Documents
        ↓
Structured Extraction
        ↓
Database
        ↓
Scoring
        ↓
Investment Memo
```

Structured data is the system of record.

Narrative reports are generated from structured information rather than becoming the primary source of truth.

This enables:

* repeatable analysis
* model comparison
* regression testing
* historical tracking
* deterministic scoring

---

# 8. Incremental Delivery

Large features are divided into independently testable milestones.

Each milestone should:

* compile successfully
* pass all regression tests
* preserve backward compatibility
* remain deployable

Avoid introducing partially completed architectural changes.

---

# 9. Backward Compatibility

New features should extend existing functionality rather than replacing it.

Refactoring is encouraged when it improves maintainability without changing external behavior.

Avoid unnecessary architectural rewrites.

---

# 10. Code Quality Standards

Every completed sprint should satisfy the following checklist:

* All automated tests pass.
* Existing functionality continues to work.
* Linting is clean.
* Alembic migration chain remains valid.
* New functionality includes documentation.
* Public interfaces remain consistent.

Quality gates are considered mandatory before beginning the next sprint.

---

# Guiding Principle

> Build Investment OS as an AI-native investment analysis platform while preserving the engineering discipline of a production-quality software system.

Every architectural decision should balance innovation with maintainability, ensuring that the platform remains reliable, extensible, and easy to evolve over time.

