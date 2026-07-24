<a id="investment-os-engineering-handbook"></a># Investment OS Engineering Handbook

<a id="chapter-01-project-structure"></a># Chapter 01 – Project Structure

__Version:__ 1\.0

__Project:__ Investment OS

<a id="table-of-contents"></a># Table of Contents

1. Purpose
2. Repository Philosophy
3. High\-Level Repository Layout
4. Directory Standards
5. Application Layer Structure
6. Documentation Structure
7. Testing Structure
8. Configuration Management
9. Scripts and Automation
10. Docker Organization
11. Infrastructure
12. Dependency Rules
13. Naming Conventions
14. Module Template
15. Adding a New Feature
16. Repository Checklist

<a id="purpose"></a># 1\. Purpose

This document defines the standard repository layout for Investment OS\.

A consistent structure enables:

- Faster onboarding
- Easier maintenance
- Clear ownership
- Predictable navigation
- Better scalability
- Reduced technical debt

Every contributor must follow this structure\.

<a id="repository-philosophy"></a># 2\. Repository Philosophy

The repository is organized according to __Clean Architecture__\.

Business logic is independent of frameworks, databases, or external services\.

Presentation  
        │  
        ▼  
Application  
        │  
        ▼  
Domain  
        │  
        ▼  
Infrastructure

<a id="dependency-rule"></a>### Dependency Rule

Dependencies always point inward\.

API  
    ↓  
Service  
    ↓  
Repository  
    ↓  
Database

Business logic never depends directly on infrastructure\.

<a id="repository-layout"></a># 3\. Repository Layout

investment\-os/  
  
├── app/  
├── tests/  
├── docs/  
├── docker/  
├── scripts/  
├── tools/  
├── templates/  
├── migrations/  
├── config/  
├── assets/  
├── examples/  
├── \.github/  
├── pyproject\.toml  
├── Makefile  
├── README\.md  
└── LICENSE

<a id="directory-responsibilities"></a># 4\. Directory Responsibilities

<a id="app"></a>## app/

Contains production source code only\.

app/  
  
api/  
core/  
config/  
models/  
schemas/  
repositories/  
services/  
agents/  
workers/  
middleware/  
security/  
events/  
utils/

No experimental code\.

<a id="tests"></a>## tests/

Contains automated tests\.

tests/  
  
unit/  
integration/  
performance/  
security/  
fixtures/  
test\_data/

Production code never depends on tests\.

<a id="docs"></a>## docs/

Contains project documentation\.

docs/  
  
engineering/  
architecture/  
adr/  
developer/  
api/  
operations/  
product/

Documentation evolves with the codebase\.

<a id="docker"></a>## docker/

Contains Docker artifacts\.

docker/  
  
development/  
testing/  
production/  
compose/

Each environment should have isolated configurations\.

<a id="scripts"></a>## scripts/

Contains operational scripts\.

Examples:

- Database initialization
- Seed data
- Backup
- Restore
- Deployment
- Code generation
- Maintenance

Scripts should be idempotent where practical\.

<a id="tools"></a>## tools/

Developer utilities\.

Examples:

- Code generators
- Lint wrappers
- Local utilities
- Performance profilers

<a id="templates"></a>## templates/

Reusable templates\.

API Template  
Repository Template  
Service Template  
ADR Template  
Feature Template  
Migration Template  
Test Template

<a id="config"></a>## config/

Configuration files\.

config/  
  
development\.yaml  
testing\.yaml  
production\.yaml  
logging\.yaml

Secrets are never stored here\.

<a id="migrations"></a>## migrations/

Database schema migrations\.

versions/  
  
env\.py  
script\.py\.mako

Only Alembic\-generated migrations should reside here\.

<a id="application-structure"></a># 5\. Application Structure

app/  
  
api/  
services/  
repositories/  
models/  
schemas/  
core/  
security/  
middleware/  
agents/  
workers/

<a id="api"></a>### api/

REST endpoints only\.

Responsibilities:

- Request validation
- Authentication
- Response serialization

Must not contain business rules\.

<a id="services"></a>### services/

Business logic\.

Responsibilities:

- Domain rules
- Workflow orchestration
- Transactions

May depend on repositories\.

<a id="repositories"></a>### repositories/

Database access\.

Responsibilities:

- CRUD
- Queries
- Persistence

No business logic\.

<a id="models"></a>### models/

ORM entities\.

Only database mappings\.

<a id="schemas"></a>### schemas/

Pydantic models\.

Used for:

- Requests
- Responses
- Validation
- DTOs

<a id="core"></a>### core/

Shared infrastructure\.

Examples:

- Logging
- Settings
- Exceptions
- Constants
- Lifespan
- Dependency injection

<a id="security"></a>### security/

Authentication and authorization\.

Examples:

- JWT
- RBAC
- Password hashing
- Permissions

<a id="middleware"></a>### middleware/

Cross\-cutting concerns\.

Examples:

- Request logging
- Correlation IDs
- CORS
- Rate limiting

<a id="agents"></a>### agents/

AI agent implementations\.

Examples:

FounderAgent  
FinancialAgent  
LegalAgent  
MarketAgent  
TechnologyAgent  
PortfolioAgent

Each agent follows a common interface\.

<a id="workers"></a>### workers/

Background processing\.

Examples:

- Email
- Report generation
- AI evaluation
- Scheduled tasks

<a id="testing-structure"></a># 6\. Testing Structure

tests/  
  
unit/  
integration/  
performance/  
security/  
fixtures/

<a id="unit"></a>### unit/

Fast, isolated tests\.

<a id="integration"></a>### integration/

API, database, and workflow tests\.

<a id="performance"></a>### performance/

Load and benchmark tests\.

<a id="security-1"></a>### security/

Authentication and authorization validation\.

<a id="fixtures"></a>### fixtures/

Reusable test fixtures\.

<a id="documentation-layout"></a># 7\. Documentation Layout

docs/  
  
engineering/  
architecture/  
adr/  
developer/  
operations/  
product/  
api/

Every feature should update the relevant documentation\.

<a id="naming-conventions"></a># 8\. Naming Conventions

Directories

snake\_case

Python modules

snake\_case\.py

Classes

PascalCase

Functions

snake\_case

Constants

UPPER\_CASE

Environment variables

UPPER\_CASE

Database tables

snake\_case

<a id="dependency-rules"></a># 9\. Dependency Rules

Allowed:

API → Services  
Services → Repositories  
Repositories → Models  
Models → Database

Not allowed:

API → Database  
Repository → API  
Model → Service

Circular dependencies are prohibited\.

<a id="adding-a-new-feature"></a># 10\. Adding a New Feature

Every feature follows this layout:

feature\_name/  
  
api\.py  
service\.py  
repository\.py  
models\.py  
schemas\.py  
tests\.py  
README\.md

All layers should be created together\.

<a id="repository-checklist"></a># 11\. Repository Checklist

Before merging:

- Directory structure follows standards
- No business logic in API layer
- No SQL in services
- Tests added
- Documentation updated
- ADR created \(if architecture changes\)
- CI passes
- Lint passes
- Type checking passes

<a id="summary"></a># Summary

A predictable repository structure is one of the most effective ways to reduce technical debt\.

The repository should scale from a single developer to a multi\-team engineering organization without requiring structural redesign\.

Following these standards ensures Investment OS remains maintainable, modular, and ready for future AI\-driven capabilities\.

