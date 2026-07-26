# Investment OS Development Process

## Purpose

This document defines the engineering process used to develop Investment OS.

The objective is to ensure that development follows a disciplined, predictable, and product-oriented lifecycle.

The process is intentionally lightweight while maintaining engineering quality and architectural consistency.

---

# Project Governance

The project is managed using four governance documents.

| Document         | Purpose                                          |
| ---------------- | ------------------------------------------------ |
| ROADMAP.md       | Defines the long-term product roadmap.           |
| SPRINT_PLAN.md   | Tracks sprint execution and current progress.    |
| SPRINT_REVIEW.md | Records sprint completion reviews and approvals. |
| CHANGELOG.md     | Records released features and product versions.  |

Each document has a single responsibility and should not duplicate information contained in another document.

---

# Development Lifecycle

Every sprint follows the same lifecycle.

1. Sprint Planning
2. Sprint Development
3. Functional Review
4. Code Review
5. Architecture Alignment Review
6. Sprint Closure
7. Sprint Review Approval
8. Update Sprint Plan
9. Begin Next Sprint

No sprint may begin until the previous sprint has been formally closed.

---

# Scope Management

Every new feature must belong to:

* A Phase
* A Sprint
* A Planned Objective

If a feature cannot be assigned to an active or future sprint, it should not be implemented until the project plan is updated.

---

# Sprint Completion Criteria

A sprint is considered complete only when all of the following conditions are satisfied:

* Planned objectives are completed.
* Code review is complete.
* Automated tests pass.
* Documentation is updated.
* Architecture review passes.
* Sprint Review is approved.

Only after these criteria are met may the sprint be marked as **Completed** in `SPRINT_PLAN.md`.

---

# Architecture Alignment

During sprint review, every new file must be reviewed to ensure it belongs to the planned sprint.

Questions to verify:

* Does this file belong to the current phase?
* Does this file belong to the current sprint?
* Is this implementation introducing work from a future sprint?
* Does it follow the project architecture?

Future-sprint functionality should not be introduced unless explicitly approved.

---

# Change Management

Project plans may evolve, but changes should follow these rules:

* ROADMAP.md changes only for strategic decisions.
* SPRINT_PLAN.md changes only during sprint planning or sprint closure.
* SPRINT_REVIEW.md is append-only after approval.
* CHANGELOG.md records only released functionality.

Completed sprints should not be redefined. New work should be scheduled into future sprints.

---

# Engineering Principles

Investment OS follows these principles throughout development:

* Product-first development
* Incremental delivery
* Stable architecture
* Small, verifiable milestones
* Test-driven quality
* Documentation as part of development
* Traceability from roadmap to implementation

The objective is to deliver a maintainable production-grade platform rather than an open-ended research project.

