# Investment OS Engineering Process

## Purpose

This document defines the engineering process used to develop **Investment OS**.

The objective is to ensure that development remains predictable, incremental, traceable, and release-oriented while maintaining high engineering quality.

This document defines **how** the project is developed. It does **not** define project scope, release content, or future work.

---

# Engineering Governance

Project governance is distributed across dedicated documents, each with a single responsibility.

| Document         | Responsibility                         |
| ---------------- | -------------------------------------- |
| ROADMAP.md       | Long-term product direction            |
| SPRINT_PLAN.md   | Current sprint planning and execution  |
| SPRINT_REVIEW.md | Sprint review outcomes and approvals   |
| BACKLOG.md       | Planned future work and technical debt |
| MILESTONES.md    | Historical engineering achievements    |
| RELEASE_PLAN.md  | Release strategy and approval process  |
| CHANGELOG.md     | Released functionality                 |

Each document should remain the authoritative source for its own subject and should not duplicate information maintained elsewhere.

---

# Engineering Lifecycle

Every feature follows the same engineering lifecycle.

```text
Roadmap
    │
    ▼
Backlog
    │
    ▼
Sprint Planning
    │
    ▼
Implementation
    │
    ▼
Code Review
    │
    ▼
Testing
    │
    ▼
Architecture Review
    │
    ▼
Documentation Update
    │
    ▼
Sprint Review
    │
    ▼
Milestone Approval
    │
    ▼
Release
```

This lifecycle applies throughout the project regardless of implementation technology.

---

# Development Lifecycle

Each sprint progresses through the following stages.

1. Sprint Planning
2. Development
3. Unit Testing
4. Code Review
5. Architecture Alignment Review
6. Documentation Update
7. Sprint Closure
8. Sprint Review Approval
9. Begin Next Sprint

A new sprint should not begin until the previous sprint has been formally reviewed and approved.

---

# Scope Management

Every implementation must be traceable to the project plan.

Each work item should belong to:

* A Phase
* A Sprint
* A Planned Objective

Features that are not part of the approved project plan should be added to the backlog before implementation.

---

# Architecture Alignment

Architecture reviews verify that new work remains consistent with the planned system architecture.

Typical review questions include:

* Does this implementation belong to the current phase?
* Does it belong to the current sprint?
* Does it introduce functionality from a future phase?
* Does it follow established architectural patterns?
* Can existing components be reused instead of introducing new abstractions?

Architecture reviews should minimize unnecessary complexity while preserving long-term maintainability.

---

# Quality Gates

A sprint is considered complete only when all quality gates have been satisfied.

### Functional

* Planned objectives completed
* Acceptance criteria satisfied

### Engineering

* Code review completed
* Automated tests passing
* Coverage targets achieved
* Static analysis completed
* Formatting verified

### Documentation

* Relevant documentation updated
* Public interfaces documented
* Architecture documentation updated (if required)

### Governance

* Sprint Review approved
* Sprint Plan updated
* Backlog reprioritized (if required)

---

# Milestone Completion

A milestone represents a significant engineering achievement.

A milestone may be closed only when:

* All planned sprint objectives are completed.
* Quality gates have passed.
* Documentation is complete.
* Architecture review is complete.
* Sprint review has been approved.

Milestones become part of the permanent project history and should not be redefined after approval.

---

# Release Process

A release is created only after milestone approval.

The release process consists of:

1. Verify milestone completion
2. Verify quality metrics
3. Update release documentation
4. Update changelog
5. Assign version number
6. Create Git tag
7. Publish release

Release readiness is governed by `RELEASE_PLAN.md`.

---

# Change Management

Project plans evolve throughout development.

Changes should follow these principles:

* ROADMAP.md changes only for strategic planning.
* BACKLOG.md records future work and technical debt.
* SPRINT_PLAN.md changes during sprint planning or closure.
* SPRINT_REVIEW.md becomes read-only after approval.
* MILESTONES.md records completed engineering achievements.
* CHANGELOG.md records only released functionality.

Completed work should never be rewritten. New requirements should be scheduled into future phases.

---

# Documentation Principles

Documentation is part of the engineering deliverable.

Every significant implementation should update the relevant documentation before sprint completion.

Documentation should be:

* Accurate
* Concise
* Version aligned
* Traceable
* Easy to maintain

---

# Engineering Principles

Investment OS follows these engineering principles throughout development.

* Product-first development
* Incremental delivery
* Stable architecture
* Small, verifiable milestones
* Test-driven quality
* Documentation as part of development
* Traceability from planning to implementation
* Release-oriented development
* Continuous refactoring without disrupting released functionality

The objective is to deliver a maintainable, production-grade platform rather than an open-ended research project.

---

# Continuous Improvement

The engineering process should be reviewed at the completion of each major release.

Potential improvements should be identified during milestone retrospectives and incorporated into future phases without disrupting completed project history.

