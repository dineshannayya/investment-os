Milestone 1 – Investment Workspace
Target: 4–6 weeks
Start Date: 8 July 2026
End   Date:

Features:
    Docker-based development environment
    User login (single user is sufficient)
    Dashboard
    Startup management
    Founder management
    Deal pipeline
    Documents
    Due diligence checklist
    Valuation engine
    Decision journal
    Watchlist
    Portfolio summary


# --------------------------------------------------
All feature expansion are inside

extensions/
│
├── agents/
│
├── experiments/
│
├── notebooks/
│
├── importers/
│
├── exporters/
│
└── tools/
# --------------------------------------------------


Sprint 0 in this order
    ✅ Repository structure
    Dockerfiles (Backend & Frontend)
    docker-compose.yml
    .env.example
    Makefile
    FastAPI "Hello World"
    Next.js "Hello World"
    PostgreSQL connection
    Redis connection
    GitHub Actions

# Sprint 1 Milestones

| Milestone  | Deliverable                                                                      |
| ---------- | -------------------------------------------------------------------------------- |
| Sprint 1.1 | Configuration + Database + SQLAlchemy + Alembic                                  |
| Sprint 1.2 | Startup, Founder, Opportunity, Document models                                   |
| Sprint 1.3 | Repository and Service layers                                                    |
| Sprint 1.4 | REST APIs (CRUD + search + pagination)                                           |
| Sprint 1.5 | Next.js pages (Dashboard, Startup List, Startup Details, Watchlist)              |
| Sprint 1.6 | Basic end-to-end workflow: Create Startup → Upload Documents → Submit for Review |

Revised:

| Milestone  | Deliverable                                     | Status               |
| ---------- | ----------------------------------------------- | -------------------- |
| Sprint 1.1 | Configuration + Database + SQLAlchemy + Alembic | Same                 |
| Sprint 1.2 | Startup, Founder, Opportunity, Document Models  | Same                 |
| Sprint 1.3 | Repository + Service Layer                      | Same                 |
| Sprint 1.4 | REST APIs + CLI Commands (same services)        | **Expanded**         |
| Sprint 1.5 | AI Analysis Workflow (CLI-first)                | **Changed**          |
| Sprint 1.6 | End-to-End Workflow                             | Same goal, CLI-first |


Revised Roadmap


| Sprint         | Primary Outcome                                               |
| -------------- | ------------------------------------------------------------- |
| **Sprint 0**   | Engineering foundation, standards, repository governance ✅    |
| **Sprint 1.1** | Configuration, Database, SQLAlchemy, Alembic                  |
| **Sprint 1.2** | Core domain models                                            |
| **Sprint 1.3** | Repository and service layer                                  |
| **Sprint 1.4** | REST APIs and CLI using the same service layer                |
| **Sprint 1.5** | AI document ingestion and startup analysis workflow           |
| **Sprint 1.6** | End-to-end CLI workflow for startup evaluation                |
| **Sprint 2**   | Local Next.js dashboard and visualization                     |
| **Sprint 3**   | Multi-agent orchestration, remote access, and cloud readiness |


| Sprint  | Deliverable                                                                               |
| ------- | ----------------------------------------------------------------------------------------- |
| **1.1** | Configuration + Database + SQLAlchemy + Alembic                                           |
| **1.2** | Domain Models (Startup, Founder, Opportunity, Document)                                   |
| **1.3** | Repository + Services                                                                     |
| **1.4** | CLI Commands + REST APIs                                                                  |
| **1.5** | AI Agent Integration (single-agent workflow)                                              |
| **1.6** | End-to-End CLI Workflow: Create Startup → Import Documents → AI Analysis → Recommendation |
| **2.0** | Local Next.js Dashboard                                                                   |
| **3.0** | Remote Access, Authentication, Cloud Readiness                                            |
# -----------------------------------------------------------------------------------------------
Sprint 1.1 Expansion

Sprint 1.1.1 – Configuration
    Pydantic Settings
    Environment profiles
    Secrets
    Logging configuration
    Constants
    Tests

Sprint 1.1.2 – Database Infrastructure
    PostgreSQL connection
    Async SQLAlchemy engine
    Session management
    Base model
    UUID support
    Naming conventions

Sprint 1.1.3 – Alembic
    Migration configuration
    Initial migration
    Migration scripts
    Makefile integration

Sprint 1.1.4 – Validation
    Regression tests
    Coverage >95%
    Documentation updates
    CI verification

# ---------------------------------------------------------------------------------------------
