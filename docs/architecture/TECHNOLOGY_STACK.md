# Technology Stack

**Project:** Investment OS

**Document Version:** 1.0

**Status:** Draft

**Owner:** Architecture Team

**Last Updated:** 2026-07-25

---

# 1. Purpose

This document defines the approved technology stack for **Investment OS**.

It serves as the authoritative reference for:

* programming languages
* frameworks
* libraries
* databases
* AI technologies
* infrastructure
* development tools

Technology selections documented here are expected to align with the architectural decisions captured in the Architecture Decision Records (ADRs).

---

# 2. Technology Selection Principles

Technology choices should satisfy the following criteria:

* Production ready
* Long-term community support
* Strong documentation
* Active maintenance
* Security
* Performance
* Scalability
* Ease of integration
* Open standards where practical

Introducing new technologies should be justified through the ADR process when they significantly affect the architecture.

---

# 3. Technology Overview

| Layer                 | Primary Technology                         |
| --------------------- | ------------------------------------------ |
| Programming Language  | Python 3.12+                               |
| Backend Framework     | FastAPI                                    |
| Data Validation       | Pydantic                                   |
| ASGI Server           | Uvicorn                                    |
| ORM                   | SQLAlchemy *(planned)*                     |
| Database Migration    | Alembic *(planned)*                        |
| Database              | PostgreSQL                                 |
| Authentication        | JWT                                        |
| AI Framework          | LangChain / Custom AI Services *(planned)* |
| Testing               | pytest                                     |
| API Documentation     | OpenAPI / Swagger                          |
| Dependency Management | uv                                         |
| Containerization      | Docker *(planned)*                         |
| CI/CD                 | GitHub Actions *(planned)*                 |

---

# 4. Programming Languages

| Language               | Purpose                                 |
| ---------------------- | --------------------------------------- |
| Python                 | Backend services and AI platform        |
| SQL                    | Database queries and migrations         |
| TypeScript *(planned)* | Frontend development                    |
| Markdown               | Documentation                           |
| YAML                   | Configuration and CI pipelines          |
| JSON                   | API payloads and configuration exchange |

---

# 5. Backend Stack

| Technology     | Purpose                        |
| -------------- | ------------------------------ |
| FastAPI        | REST API framework             |
| Pydantic       | Request/response validation    |
| Uvicorn        | ASGI server                    |
| Starlette      | ASGI components and middleware |
| httpx          | HTTP client                    |
| Python Logging | Logging framework              |

The backend follows a modular monolith architecture as defined in ADR-0001.

---

# 6. Database Stack

| Technology             | Purpose                     |
| ---------------------- | --------------------------- |
| PostgreSQL             | Primary relational database |
| SQLAlchemy *(planned)* | ORM                         |
| Alembic *(planned)*    | Schema migrations           |

Future technologies under evaluation:

* Redis (caching)
* pgvector (vector search)
* Object storage for documents

---

# 7. AI Platform

The AI platform is designed to remain provider-agnostic.

Candidate technologies include:

| Technology                  | Purpose                              |
| --------------------------- | ------------------------------------ |
| LangChain *(planned)*       | LLM orchestration                    |
| OpenAI-compatible APIs      | Commercial model integration         |
| Local LLM runtimes          | Self-hosted inference                |
| Embedding models            | Semantic search                      |
| Vector database *(planned)* | Retrieval-Augmented Generation (RAG) |

The exact implementation is governed by future AI architecture ADRs.

---

# 8. Frontend Stack (Planned)

| Technology     | Purpose                   |
| -------------- | ------------------------- |
| React          | User interface            |
| Next.js        | Web application framework |
| TypeScript     | Frontend language         |
| Tailwind CSS   | Styling                   |
| TanStack Query | Data fetching and caching |

Frontend technologies may evolve independently of the backend provided API contracts remain stable.

---

# 9. Security Technologies

| Technology                  | Purpose          |
| --------------------------- | ---------------- |
| JWT                         | Authentication   |
| HTTPS                       | Secure transport |
| bcrypt / Argon2 *(planned)* | Password hashing |
| Environment variables       | Secret injection |

Future security enhancements will be documented through dedicated ADRs.

---

# 10. Development Tools

| Tool                   | Purpose               |
| ---------------------- | --------------------- |
| Git                    | Version control       |
| GitHub                 | Source repository     |
| uv                     | Dependency management |
| Ruff                   | Linting               |
| Black                  | Code formatting       |
| pytest                 | Automated testing     |
| pytest-cov             | Coverage reporting    |
| mypy *(planned)*       | Static type checking  |
| pre-commit *(planned)* | Local quality gates   |

---

# 11. Documentation Tools

| Tool                | Purpose                       |
| ------------------- | ----------------------------- |
| Markdown            | Documentation format          |
| Mermaid *(planned)* | Architecture diagrams         |
| MkDocs *(planned)*  | Documentation site generation |

Documentation remains part of the source repository and follows the Documentation Strategy defined in ADR-0006.

---

# 12. DevOps & Infrastructure (Planned)

| Technology     | Purpose               |
| -------------- | --------------------- |
| Docker         | Containerization      |
| GitHub Actions | CI/CD                 |
| Nginx          | Reverse proxy         |
| Prometheus     | Metrics collection    |
| Grafana        | Monitoring dashboards |
| OpenTelemetry  | Distributed tracing   |

These technologies may be introduced incrementally as the platform matures.

---

# 13. External Integrations

Potential integration categories include:

* AI model providers
* Market data providers
* Company information services
* Email providers
* Cloud storage
* Identity providers

Specific providers are selected based on business requirements and are abstracted behind service interfaces.

---

# 14. Technology Lifecycle

Technologies are classified according to their adoption status.

| Status           | Meaning                            |
| ---------------- | ---------------------------------- |
| Adopted          | Approved and in production use     |
| Planned          | Approved for future implementation |
| Under Evaluation | Being assessed                     |
| Deprecated       | Scheduled for removal              |

The lifecycle status should be updated as technologies evolve.

---

# 15. Upgrade Policy

Technology upgrades should consider:

* security fixes
* compatibility
* long-term support
* performance improvements
* community adoption

Major version upgrades should be evaluated before adoption and may require a new ADR if they introduce architectural changes.

---

# 16. Technology Constraints

The following principles apply:

* Prefer well-supported open-source technologies.
* Avoid introducing overlapping frameworks.
* Minimize unnecessary dependencies.
* Isolate third-party integrations behind service interfaces.
* Keep the platform portable across deployment environments.

---

# 17. Related Documents

* `PROJECT_BIBLE.md`
* `SYSTEM_ARCHITECTURE.md`
* `CODING_STANDARDS.md`
* `TESTING_STRATEGY.md`
* `CONFIGURATION_GUIDE.md`
* `OBSERVABILITY.md`
* `adr/INDEX.md`

---

# 18. Revision History

| Version | Date       | Description                         |
| ------- | ---------- | ----------------------------------- |
| 1.0     | 2026-07-25 | Initial technology stack definition |

