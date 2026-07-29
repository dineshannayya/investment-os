# Investment OS Release Plan

## Purpose

This document defines the release management process for Investment OS.

It establishes:

* Release lifecycle
* Versioning strategy
* Release readiness criteria
* Approval process
* Release checklist
* Post-release activities

The objective is to ensure that every release is repeatable, traceable, and meets the project's engineering quality standards.

---

# Release Strategy

Investment OS follows a milestone-driven release model.

Each release represents a completed engineering milestone with defined functionality and documented quality metrics.

Releases are planned at the end of major project phases rather than on fixed calendar dates.

---

# Versioning

Investment OS follows Semantic Versioning (SemVer).

```
MAJOR.MINOR.PATCH
```

## MAJOR

Incremented for breaking architectural or API changes.

Examples:

* v1.0.0
* v2.0.0

---

## MINOR

Incremented for new functionality delivered through completed project phases.

Examples:

* v0.1.0
* v0.2.0
* v0.3.0

---

## PATCH

Incremented for backward-compatible bug fixes.

Examples:

* v0.2.1
* v0.2.2

---

# Planned Releases

| Version | Milestone                | Status     |
| ------- | ------------------------ | ---------- |
| v0.1.0  | Backend Foundation       | ✅ Released |
| v0.2.0  | API Infrastructure       | Planned    |
| v0.3.0  | Database & Persistence   | Planned    |
| v0.4.0  | Investment Domain        | Planned    |
| v0.5.0  | AI Intelligence Platform | Planned    |
| v0.6.0  | Frontend Application     | Planned    |
| v1.0.0  | General Availability     | Planned    |

---

# Release Lifecycle

Every release follows the same lifecycle.

```text
Sprint Completion
        │
        ▼
Sprint Review Approved
        │
        ▼
Milestone Completed
        │
        ▼
Release Candidate
        │
        ▼
Release Validation
        │
        ▼
Release Approval
        │
        ▼
Git Tag Created
        │
        ▼
Release Published
        │
        ▼
CHANGELOG Updated
```

---

# Release Readiness

A release may proceed only when all release gates have been satisfied.

## Functional

* All planned features completed.
* No unresolved release-blocking defects.
* Acceptance criteria satisfied.

---

## Engineering

* All automated tests passing.
* Coverage target achieved.
* Static analysis passing.
* Formatting verified.
* Type checking completed.

---

## Documentation

* API documentation updated.
* Architecture documentation updated.
* Governance documentation updated.
* User documentation updated (if applicable).

---

## Project Governance

* Sprint review approved.
* Milestone approved.
* Backlog updated.
* Technical debt reviewed.

---

# Release Checklist

## Code Quality

* [ ] Code review complete
* [ ] Automated tests passing
* [ ] Coverage target achieved
* [ ] Static analysis passed
* [ ] Formatting verified
* [ ] Type checking passed

---

## Documentation

* [ ] README updated
* [ ] API documentation updated
* [ ] Architecture documentation updated
* [ ] CHANGELOG updated
* [ ] Milestone documentation finalized

---

## Project

* [ ] Sprint approved
* [ ] Milestone approved
* [ ] Version number assigned
* [ ] Git tag prepared

---

# Release Candidate (RC)

A Release Candidate is created after all sprint work has been completed.

Objectives:

* Validate release stability
* Verify documentation
* Confirm deployment readiness
* Resolve final release issues

No new features may be introduced after the Release Candidate has been created.

Only critical fixes are permitted.

---

# Release Approval

A release requires confirmation that all quality gates have passed.

| Area          | Approval |
| ------------- | -------- |
| Engineering   | ☐        |
| Architecture  | ☐        |
| Documentation | ☐        |
| Testing       | ☐        |
| Project Lead  | ☐        |

The release is approved only after every required approval has been completed.

---

# Release Artifacts

Each release should produce the following artifacts.

| Artifact          | Required |
| ----------------- | :------: |
| Git Tag           |     ✓    |
| CHANGELOG         |     ✓    |
| Milestone Record  |     ✓    |
| Version Metadata  |     ✓    |
| API Documentation |     ✓    |

---

# Hotfix Process

Critical production issues may require a patch release.

Patch releases:

* Do not introduce new functionality.
* Focus only on corrective fixes.
* Follow the same engineering quality gates.
* Increment the PATCH version only.

Example:

```
v0.2.0
      │
      ▼
v0.2.1
```

---

# Post-Release Activities

After a successful release:

1. Publish the Git tag.
2. Update project documentation.
3. Archive completed sprint plans.
4. Update milestone history.
5. Review technical debt.
6. Prepare the next sprint plan.
7. Reprioritize the backlog.

---

# Release Retrospective

Each release should conclude with a retrospective.

Topics include:

* What worked well
* Challenges encountered
* Engineering improvements
* Testing effectiveness
* Documentation quality
* Process improvements

Action items identified during the retrospective should be added to `BACKLOG.md`.

---

# Roles and Responsibilities

| Activity                | Primary Owner                  |
| ----------------------- | ------------------------------ |
| Sprint completion       | Engineering Team               |
| Sprint review           | Technical Lead                 |
| Architecture review     | Technical Lead                 |
| Documentation review    | Engineering Team               |
| Release approval        | Project Lead                   |
| Git tag and publication | Release Manager / Project Lead |

---

# Relationship to Other Governance Documents

| Document         | Responsibility                         |
| ---------------- | -------------------------------------- |
| PROCESS.md       | Defines the engineering process        |
| BACKLOG.md       | Tracks future work and technical debt  |
| SPRINT_PLAN.md   | Plans sprint execution                 |
| SPRINT_REVIEW.md | Records sprint outcomes and approvals  |
| MILESTONES.md    | Records completed phase achievements   |
| RELEASE_PLAN.md  | Governs release readiness and approval |
| CHANGELOG.md     | Records released functionality         |

A release is the culmination of completed sprint work, approved milestones, and successful validation. This document defines the process for transitioning engineering work into an officially published version of Investment OS.

