# Investment OS Project Governance

## Project Status

| Item | Value |
|------|-------|
| Current Release | **v0.1.0** |
| Current Phase | **Phase 2 – API Infrastructure** |
| Overall Progress | **~15%** |
| Last Updated | **July 2026** |

## Purpose

This directory contains the project governance documents used to plan, execute, review, and release Investment OS.

The objective is to ensure that development remains:

- Product-driven
- Incremental
- Traceable
- Reviewable
- Release-oriented

Each document has a single responsibility and should not duplicate information maintained elsewhere.

---

# Project Governance Structure

```text
                   Product Vision
                         │
                         ▼
                   ROADMAP.md
                         │
                         ▼
                   BACKLOG.md
                         │
                         ▼
                 Sprint Planning
                         │
                         ▼
                 Sprint Development
                         │
                         ▼
                 Sprint Review
                         │
                         ▼
                 MILESTONES.md
                         │
                         ▼
               RELEASE_PLAN.md
                         │
                         ▼
                 CHANGELOG.md
```

---

# Documents

## PROCESS.md

Defines the engineering process used throughout the project.

Topics include:

- Development lifecycle
- Sprint workflow
- Architecture reviews
- Completion criteria
- Change management
- Engineering principles

**Updated when**

- Engineering process changes

---

## BACKLOG.md

Tracks future engineering work.

Includes:

- Product features
- Architecture improvements
- Security
- AI platform
- Documentation
- Technical debt
- Research initiatives

This is the working list of everything not yet completed.

**Updated when**

- New work is identified
- Priorities change
- Features are completed
- Technical debt is added

---

## MILESTONES.md

Records major engineering achievements.

Each milestone captures:

- Objectives
- Deliverables
- Quality metrics
- Architecture decisions
- Lessons learned
- Exit criteria

Unlike the backlog, milestones are historical records.

**Updated when**

- A phase is completed
- A milestone is approved

---

## RELEASE_PLAN.md

Defines how releases are produced.

Includes:

- Release roadmap
- Version strategy
- Release approval checklist
- Release lifecycle

This document defines *when* a release may occur.

**Updated when**

- Release strategy changes
- New release milestones are added

---

## CHANGELOG.md

Records released functionality.

Each release includes:

- Summary
- Added
- Changed
- Fixed
- Known issues
- Breaking changes

Only released functionality belongs here.

Work in progress belongs in the backlog.

**Updated when**

- A release is created

---

# Governance Principles

Each document owns a specific area.

| Document | Owns |
|----------|------|
| PROCESS.md | Engineering process |
| BACKLOG.md | Future work |
| MILESTONES.md | Historical achievements |
| RELEASE_PLAN.md | Release governance |
| CHANGELOG.md | Released functionality |

Avoid duplicating information across documents.

---

# Typical Development Workflow

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
Development
    │
    ▼
Code Review
    │
    ▼
Architecture Review
    │
    ▼
Sprint Review
    │
    ▼
Milestone
    │
    ▼
Release Approval
    │
    ▼
Git Tag
    │
    ▼
Release
    │
    ▼
Changelog
```

---

# Phase Lifecycle

Each project phase follows the same sequence.

```text
Planning
    │
    ▼
Implementation
    │
    ▼
Testing
    │
    ▼
Documentation
    │
    ▼
Architecture Review
    │
    ▼
Milestone Approval
    │
    ▼
Release
```

Once a phase is released, it becomes part of the permanent project history.

---

# Engineering Principles

Investment OS follows several guiding principles:

- Product-first development
- Small incremental milestones
- Stable architecture
- Test-driven quality
- Documentation as part of development
- Traceability from planning to implementation
- Release-based delivery

---

# Updating Project Documentation

| Event | Documents to Update |
|--------|---------------------|
| New feature planned | BACKLOG.md |
| Sprint completed | MILESTONES.md |
| Release approved | RELEASE_PLAN.md, CHANGELOG.md |
| Engineering workflow changes | PROCESS.md |
| Technical debt identified | BACKLOG.md |

---

# Current Status

| Item | Status |
|------|--------|
| Current Release | v0.1.0 |
| Current Phase | Phase 2 |
| Project Status | Active |
| Development Model | Phase → Sprint → Release |

---

# Version

Project Governance Version: 1.0
