# Investment OS Roadmap

**Project:** Investment OS

**Purpose**

This document defines the long-term product roadmap for Investment OS.

It describes **what** will be built and the order in which major capabilities will be delivered.

Implementation details, sprint planning, and design decisions are intentionally excluded.

---

# Project Principles

* Build a production-quality investment platform.
* Complete one phase before expanding into the next.
* Maintain a stable architecture.
* Minimize technical debt.
* Every feature must belong to a planned phase.

---

# Phase Roadmap

| Phase | Name                     | Goal                                  | Status         |
| ----- | ------------------------ | ------------------------------------- | -------------- |
| 1     | Backend Foundation       | Build the core backend infrastructure | ✅ Completed    |
| 2     | API Infrastructure       | Build secure REST APIs                | 🟡 In Progress |
| 3     | Database & Persistence   | Repository and persistence layer      | ⬜ Planned      |
| 4     | Investment Domain        | Business logic and workflows          | ⬜ Planned      |
| 5     | AI Intelligence Platform | AI-assisted investment analysis       | ⬜ Planned      |
| 6     | Frontend Application     | Web application and dashboards        | ⬜ Planned      |
| 7     | Production & Operations  | Deployment, monitoring, security      | ⬜ Planned      |


| Phase   | Scope                   | Repository                                            |
| ------- | ----------------------- | ----------------------------------------------------- |
| Phase 1 | Backend Foundation      | `main`, `config`, `middleware`, `logging`, `lifespan` |
| Phase 2 | API Infrastructure      | `api`, `schemas`                                      |
| Phase 3 | Persistence Layer       | `database`, `models`                                  |
| Phase 4 | Business Domain         | `repositories`, `services`                            |
| Phase 5 | AI Platform             | `ai`, `agents`, `rag`, `llm`, `workflows`             |
| Phase 6 | External Integrations   | `integrations`, `mcp`, CLI                            |
| Phase 7 | Production & Operations | Deployment, monitoring, CI/CD, security               |

---

# Phase Completion Criteria

A phase is considered complete only when:

* All planned sprints are completed.
* Tests are passing.
* Documentation is updated.
* Sprint Review is approved.

---

# Current Phase

**Phase 2 – API Infrastructure**

---

# Next Milestone

**Phase 3 – Database & Persistence**

