ROADMAP.md → Frozen milestone plan (Sprint 1–4).
BACKLOG.md → Ideas and improvements that are intentionally deferred.
DECISIONS.md → Short architectural decisions (a lightweight ADR log).
PROJECT_STATUS.md → Current sprint and progress.

| Document              | Purpose                                                      | Audience                              |
| --------------------- | ------------------------------------------------------------ | ------------------------------------- |
| **PROJECT_BIBLE.md**  | Long-term engineering vision and principles                  | Architects, Tech Leads                |
| **MASTER_ROADMAP.md** | Overall implementation plan and sequencing                   | Engineering & Product                 |
| **PHASE_XX.md**       | Detailed execution and closure report for a specific phase   | Development Team                      |
| **MILESTONES.md**     | High-level progress, releases, and delivery status           | Engineering, Management, Stakeholders |
| **CHANGELOG.md**      | Chronological record of user-visible and engineering changes | All Contributors                      |
| **BACKLOG.md**        | Prioritized future work, technical debt, and enhancements    | Engineering Team                      |
| **ADR-XXXX.md**       | Record of significant architectural decisions                | Architects & Contributors             |


| ADR          | Decision                                                           |
| ------------ | ------------------------------------------------------------------ |
| **ADR-0001** | Project Structure & Modular Architecture                           |
| **ADR-0002** | Configuration Management (Pydantic Settings, environment strategy) |
| **ADR-0003** | Logging & Observability Strategy                                   |
| **ADR-0004** | Middleware Architecture                                            |
| **ADR-0005** | Exception Handling & Error Model                                   |
| **ADR-0006** | API Response Envelope & Versioning                                 |
| **ADR-0007** | Database Access Pattern (SQLAlchemy + Repository + Unit of Work)   |
| **ADR-0008** | AI Provider Abstraction & LLM Integration                          |
| **ADR-0009** | Authentication & Authorization Strategy                            |
| **ADR-0010** | Testing Strategy & Quality Gates                                   |

docs/
└── architecture/
    ├── PROJECT_BIBLE.md
    ├── SYSTEM_ARCHITECTURE.md
    ├── TECHNOLOGY_STACK.md
    ├── CODING_STANDARDS.md
    ├── TESTING_STRATEGY.md
    │
    └── adr/
        │
        ├── README.md
        ├── INDEX.md
        │
        ├── core/
        │   ├── ADR-0001-Project-Structure.md
        │   ├── ADR-0002-Coding-Standards.md
        │   ├── ADR-0003-Configuration-Management.md
        │   ├── ADR-0004-Logging-Strategy.md
        │   ├── ADR-0005-Testing-Strategy.md
        │   └── ADR-0006-Documentation-Strategy.md
        │
        ├── backend/
        │   ├── ADR-0101-FastAPI-Architecture.md
        │   ├── ADR-0102-Middleware-Architecture.md
        │   ├── ADR-0103-Exception-Handling.md
        │   ├── ADR-0104-Response-Envelope.md
        │   ├── ADR-0105-Dependency-Injection.md
        │   └── ADR-0106-API-Versioning.md
        │
        ├── database/
        │   ├── ADR-0201-PostgreSQL-Selection.md
        │   ├── ADR-0202-SQLAlchemy.md
        │   ├── ADR-0203-Repository-Pattern.md
        │   ├── ADR-0204-Unit-of-Work.md
        │   ├── ADR-0205-Migration-Strategy.md
        │   └── ADR-0206-Database-Indexing.md
        │
        ├── ai/
        │   ├── ADR-0301-LLM-Abstraction.md
        │   ├── ADR-0302-RAG-Architecture.md
        │   ├── ADR-0303-Vector-Database.md
        │   ├── ADR-0304-Agent-Orchestration.md
        │   ├── ADR-0305-Prompt-Management.md
        │   └── ADR-0306-Model-Evaluation.md
        │
        ├── security/
        │   ├── ADR-0401-Authentication.md
        │   ├── ADR-0402-Authorization.md
        │   ├── ADR-0403-Secrets-Management.md
        │   ├── ADR-0404-Audit-Logging.md
        │   └── ADR-0405-Data-Encryption.md
        │
        ├── devops/
        │   ├── ADR-0501-Docker-Strategy.md
        │   ├── ADR-0502-CI-CD.md
        │   ├── ADR-0503-Deployment.md
        │   ├── ADR-0504-Monitoring.md
        │   └── ADR-0505-Logging-Observability.md
        │
        ├── frontend/
        │   ├── ADR-0601-Frontend-Framework.md
        │   ├── ADR-0602-State-Management.md
        │   ├── ADR-0603-Routing.md
        │   └── ADR-0604-Component-Architecture.md
        │
        └── archive/
            ├── ADR-0007-Old-Logging.md
            └── ADR-0108-Deprecated-Auth.md


ADR Numbering Strategy

| Range               | Domain                  |
| ------------------- | ----------------------- |
| ADR-0001 – ADR-0099 | Core Architecture       |
| ADR-0101 – ADR-0199 | Backend/API             |
| ADR-0201 – ADR-0299 | Database                |
| ADR-0301 – ADR-0399 | AI Platform             |
| ADR-0401 – ADR-0499 | Security                |
| ADR-0501 – ADR-0599 | DevOps                  |
| ADR-0601 – ADR-0699 | Frontend                |
| ADR-0701 – ADR-0799 | Infrastructure          |
| ADR-0801 – ADR-0899 | Performance             |
| ADR-0901 – ADR-0999 | Experimental / Research |


# Phase-1: Core

ADR-0001  Project Structure
ADR-0002  Coding Standards
ADR-0003  Configuration Management
ADR-0004  Logging Strategy
ADR-0005  Testing Strategy
ADR-0006  Documentation Strategy

# Phase-2: Backend

ADR-0101  FastAPI Architecture
ADR-0102  Middleware Design
ADR-0103  Exception Handling
ADR-0104  Response Envelope
ADR-0105  Dependency Injection
ADR-0106  API Versioning
ADR-0107  Pagination Strategy

# Phase-3: Database
ADR-0201  PostgreSQL Selection
ADR-0202  SQLAlchemy
ADR-0203  Repository Pattern
ADR-0204  Unit of Work
ADR-0205  Alembic Migration
ADR-0206  Transaction Strategy
ADR-0207  Database Naming Convention

# Phase-4: Investment Domain
ADR-0251  Domain-Driven Design
ADR-0252  Startup Aggregate
ADR-0253  Founder Aggregate
ADR-0254  Investment Workflow
ADR-0255  Scoring Engine
ADR-0256  Report Generation


