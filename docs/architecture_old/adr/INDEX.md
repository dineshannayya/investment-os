# Architecture Decision Record (ADR) Index

**Project:** Investment OS

**Document Version:** 1.0

**Last Updated:** 2026-07-25

**Owner:** Architecture Team

---
# Architecture Maturity Dashboard

| Domain   | ADR Coverage | Implementation | Maturity   |
| -------- | -----------: | -------------: | ---------- |
| Core     |        6 / 6 |           100% | 🟢 Stable  |
| Backend  |        0 / 6 |             0% | 🟡 Planned |
| Database |        0 / 6 |             0% | 🟡 Planned |
| Security |        0 / 6 |             0% | 🟡 Planned |
| AI       |        0 / 6 |             0% | 🟡 Planned |
| DevOps   |        0 / 6 |             0% | 🟡 Planned |
| Frontend |        0 / 5 |             0% | 🟡 Planned |

---

# Purpose

This document serves as the master index for all **Architecture Decision Records (ADRs)** within Investment OS.

It provides:

* a catalog of architectural decisions
* implementation status
* ownership by architecture domain
* navigation to ADR documents
* traceability across project phases

All significant architectural decisions should be discoverable from this document.

---

# ADR Status Legend

| Status         | Description                       |
| -------------- | --------------------------------- |
| 📝 Proposed    | Under discussion                  |
| 👀 Review      | Under architectural review        |
| ✅ Accepted     | Approved architectural decision   |
| 🚀 Implemented | Fully implemented in the codebase |
| 🔄 Superseded  | Replaced by a newer ADR           |
| 📦 Archived    | Historical reference only         |

---

# ADR Numbering Scheme

Investment OS reserves ADR number ranges by technical domain.

| Range               | Domain                  | Folder          |
| ------------------- | ----------------------- | --------------- |
| ADR-0001 – ADR-0099 | Core Architecture       | `adr/core/`     |
| ADR-0100 – ADR-0199 | Backend Architecture    | `adr/backend/`  |
| ADR-0200 – ADR-0299 | Database Architecture   | `adr/database/` |
| ADR-0300 – ADR-0399 | AI Platform             | `adr/ai/`       |
| ADR-0400 – ADR-0499 | Security                | `adr/security/` |
| ADR-0500 – ADR-0599 | DevOps & Infrastructure | `adr/devops/`   |
| ADR-0600 – ADR-0699 | Frontend                | `adr/frontend/` |
| ADR-9000 – ADR-9999 | Archived                | `adr/archive/`  |

ADR numbers are permanent and are never reused.

---

# Current ADR Summary

| Domain   | Accepted | Proposed | Implemented |
| -------- | -------: | -------: | ----------: |
| Core     |        6 |        0 |           6 |
| Backend  |        0 |        0 |           0 |
| Database |        0 |        0 |           0 |
| AI       |        0 |        0 |           0 |
| Security |        0 |        0 |           0 |
| DevOps   |        0 |        0 |           0 |
| Frontend |        0 |        0 |           0 |

---

# Core Architecture

**Location**

```text
docs/architecture/adr/core/
```

| ADR      | Status | Title                                      | Phase   |
| -------- | ------ | ------------------------------------------ | ------- |
| ADR-0001 | 🚀     | Project Structure & Modular Architecture   | Phase 1 |
| ADR-0002 | 🚀     | Coding Standards & Engineering Conventions | Phase 1 |
| ADR-0003 | 🚀     | Configuration Management Strategy          | Phase 1 |
| ADR-0004 | 🚀     | Logging & Observability Strategy           | Phase 1 |
| ADR-0005 | 🚀     | Testing Strategy & Quality Assurance       | Phase 1 |
| ADR-0006 | 🚀     | Documentation Strategy                     | Phase 1 |

---

# Backend Architecture

**Location**

```text
docs/architecture/adr/backend/
```

| ADR      | Status | Planned Phase | Title                         |
| -------- | ------ | ------------- | ----------------------------- |
| ADR-0101 | 📝     | Phase 2       | API Architecture              |
| ADR-0102 | 📝     | Phase 2       | Exception Handling Strategy   |
| ADR-0103 | 📝     | Phase 2       | Dependency Injection Strategy |
| ADR-0104 | 📝     | Phase 2       | Middleware Strategy           |
| ADR-0105 | 📝     | Phase 2       | API Versioning Strategy       |
| ADR-0106 | 📝     | Phase 2       | Background Task Strategy      |

---

# Database Architecture

**Location**

```text
docs/architecture/adr/database/
```

| ADR      | Status | Planned Phase | Title                  |
| -------- | ------ | ------------- | ---------------------- |
| ADR-0201 | 📝     | Phase 3       | Database Architecture  |
| ADR-0202 | 📝     | Phase 3       | Repository Pattern     |
| ADR-0203 | 📝     | Phase 3       | Transaction Management |
| ADR-0204 | 📝     | Phase 3       | Migration Strategy     |
| ADR-0205 | 📝     | Phase 3       | Soft Delete Strategy   |
| ADR-0206 | 📝     | Phase 3       | Audit Trail Strategy   |

---

# AI Platform

**Location**

```text
docs/architecture/adr/ai/
```

| ADR      | Status | Planned Phase | Title                     |
| -------- | ------ | ------------- | ------------------------- |
| ADR-0301 | 📝     | Phase 5       | AI Architecture           |
| ADR-0302 | 📝     | Phase 5       | LLM Provider Abstraction  |
| ADR-0303 | 📝     | Phase 5       | Prompt Management         |
| ADR-0304 | 📝     | Phase 5       | RAG Architecture          |
| ADR-0305 | 📝     | Phase 5       | AI Evaluation Framework   |
| ADR-0306 | 📝     | Phase 5       | Model Versioning Strategy |

---

# Security

**Location**

```text
docs/architecture/adr/security/
```

| ADR      | Status | Planned Phase | Title                   |
| -------- | ------ | ------------- | ----------------------- |
| ADR-0401 | 📝     | Phase 4       | Authentication Strategy |
| ADR-0402 | 📝     | Phase 4       | Authorization & RBAC    |
| ADR-0403 | 📝     | Phase 4       | Secret Management       |
| ADR-0404 | 📝     | Phase 4       | API Security            |
| ADR-0405 | 📝     | Phase 4       | Audit Logging           |
| ADR-0406 | 📝     | Phase 4       | Encryption Strategy     |

---

# DevOps & Infrastructure

**Location**

```text
docs/architecture/adr/devops/
```

| ADR      | Status | Planned Phase | Title                      |
| -------- | ------ | ------------- | -------------------------- |
| ADR-0501 | 📝     | Phase 6       | CI/CD Pipeline Strategy    |
| ADR-0502 | 📝     | Phase 6       | Containerization Strategy  |
| ADR-0503 | 📝     | Phase 6       | Deployment Strategy        |
| ADR-0504 | 📝     | Phase 6       | Monitoring & Metrics       |
| ADR-0505 | 📝     | Phase 6       | Backup & Disaster Recovery |
| ADR-0506 | 📝     | Phase 6       | Release Management         |

---

# Frontend

**Location**

```text
docs/architecture/adr/frontend/
```

| ADR      | Status | Planned Phase | Title                     |
| -------- | ------ | ------------- | ------------------------- |
| ADR-0601 | 📝     | Phase 6       | Frontend Architecture     |
| ADR-0602 | 📝     | Phase 6       | State Management          |
| ADR-0603 | 📝     | Phase 6       | UI Component Strategy     |
| ADR-0604 | 📝     | Phase 6       | Routing Strategy          |
| ADR-0605 | 📝     | Phase 6       | Frontend Testing Strategy |

---

# ADR Dependency Roadmap

```text
                 Core Architecture
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
    Backend        Database         Security
        │               │                │
        └───────────────┼────────────────┘
                        ▼
                  AI Platform
                        │
                        ▼
             DevOps & Infrastructure
                        │
                        ▼
                   Frontend
```

Core ADRs establish the architectural foundation upon which all domain-specific ADRs build.

---

# Governance Rules

* Every major architectural decision requires an ADR.
* ADR numbers are assigned sequentially within their domain.
* Accepted ADRs are immutable.
* Superseding a decision requires a new ADR.
* Deprecated ADRs remain in the repository for historical reference.
* ADRs should be linked from pull requests that implement the corresponding architecture.

---

# Review Schedule

Review this index:

* when a new ADR is created
* at the completion of each project phase
* before every major release
* during annual architecture reviews

---

# Related Documents

* `README.md` – ADR process and contribution guide
* `PROJECT_BIBLE.md` – Engineering vision
* `SYSTEM_ARCHITECTURE.md` – Overall system design
* `MASTER_ROADMAP.md` – Implementation roadmap
* `CHANGELOG.md` – Release history
* `BACKLOG.md` – Future engineering work

---

# Revision History

| Version | Date       | Description                                     |
| ------- | ---------- | ----------------------------------------------- |
| 1.0     | 2026-07-25 | Initial ADR index and domain-based organization |

