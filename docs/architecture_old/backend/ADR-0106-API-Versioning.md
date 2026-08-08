# ADR-0106: API Versioning

**ADR ID:** ADR-0106

**Title:** API Versioning

**Status:** Accepted

**Date:** 2026-07-25

**Authors:** Investment OS Engineering Team

**Phase:** Phase 2 – API Infrastructure

**Supersedes:** None

**Related Documents:**

* ADR-0101 – FastAPI Architecture
* ADR-0102 – Middleware Architecture
* ADR-0103 – Exception Handling
* ADR-0104 – Response Envelope
* ADR-0105 – Dependency Injection
* SYSTEM_ARCHITECTURE.md
* FASTAPI_DEVELOPMENT_GUIDE.md

---

# 1. Context

Investment OS provides REST APIs for multiple consumers including:

* Web Applications
* AI Agents
* Internal Automation
* Future Mobile Applications
* Third-party Integrations

These consumers may evolve independently and cannot always upgrade simultaneously.

Without a versioning strategy, changes to API contracts can unintentionally break existing clients, making long-term maintenance difficult.

A formal API versioning strategy is therefore required.

---

# 2. Problem Statement

The platform must define:

* How API versions are identified.
* When a new API version is required.
* What changes are considered backward compatible.
* How deprecated APIs are managed.
* How multiple API versions coexist.

---

# 3. Decision

Investment OS adopts **URI-based API versioning**.

Every public REST endpoint shall include an explicit major version in its URI.

Examples:

```text
/api/v1/startups
/api/v1/investors
/api/v1/deals
```

Major API versions may coexist to allow gradual client migration.

---

# 4. Design Goals

The versioning strategy should:

* preserve backward compatibility
* support long-term evolution
* minimize client disruption
* simplify API discovery
* provide predictable upgrade paths
* support multiple active API versions

---

# 5. Architectural Principles

## Explicit Versioning

Every public API belongs to a defined major version.

---

## Backward Compatibility

Non-breaking improvements should remain within the current major version.

---

## Predictable Evolution

Breaking changes require a new major version.

---

## Stable Contracts

Published API contracts should remain stable throughout the supported lifecycle of a major version.

---

## Independent Client Upgrades

Clients should be able to migrate to newer versions on their own schedule.

---

# 6. Versioning Strategy

Investment OS uses URI-based versioning.

```text
/api/v1/
/api/v2/
/api/v3/
```

The version identifier is part of the resource path and forms part of the public API contract.

---

# 7. API Lifecycle

Each API version progresses through the following lifecycle:

```text
Draft
   │
   ▼
Development
   │
   ▼
Released
   │
   ▼
Supported
   │
   ▼
Deprecated
   │
   ▼
Retired
```

Only supported versions should receive feature enhancements and defect fixes according to project maintenance policies.

---

# 8. Backward-Compatible Changes

The following changes are generally considered backward compatible:

* Adding new endpoints
* Adding optional request fields
* Adding optional response fields
* Improving performance
* Fixing implementation defects
* Improving documentation

Such changes do not require a new major API version.

---

# 9. Breaking Changes

The following changes require a new major API version:

* Removing endpoints
* Renaming endpoints
* Removing request fields
* Removing response fields
* Changing response structure
* Changing authentication requirements
* Modifying business semantics
* Changing resource identifiers
* Altering HTTP behavior

Breaking changes shall not be introduced into an existing major version.

---

# 10. Deprecation Policy

When an API version becomes obsolete:

* it should be formally deprecated
* deprecation should be documented
* clients should receive advance notice
* migration guidance should be provided

Deprecated versions should remain available for a defined transition period unless security or operational concerns require earlier retirement.

---

# 11. Coexistence of Versions

Multiple major versions may operate simultaneously.

Example:

```text
/api/v1/startups
/api/v2/startups
```

Each version should be independently testable and documented.

Business services should be reused where practical while allowing version-specific API behavior.

---

# 12. Integration with Other ADRs

### FastAPI Architecture

Routers are organized by API version.

---

### Middleware

Middleware should operate consistently across supported API versions.

---

### Exception Handling

All API versions should return standardized error responses.

---

### Response Envelope

The response envelope should remain consistent within a major version.

Breaking changes to the envelope require a new major version.

---

### Dependency Injection

Dependency management remains independent of API versions.

---

# 13. Alternatives Considered

## Option A – No Versioning

Expose a single evolving API.

### Advantages

* Simpler implementation.

### Disadvantages

* Breaking client changes.
* Difficult upgrades.
* High integration risk.

**Decision:** Rejected.

---

## Option B – Header-Based Versioning

Specify versions using custom HTTP headers.

### Advantages

* Clean URLs.
* Flexible routing.

### Disadvantages

* Less visible.
* Harder to test manually.
* Reduced discoverability.

**Decision:** Rejected.

---

## Option C – URI-Based Versioning

Expose the version as part of the resource path.

### Advantages

* Clear and explicit.
* Easy client adoption.
* Simple routing.
* Excellent documentation support.
* Widely understood.

**Decision:** Accepted.

---

# 14. Consequences

## Positive

* Stable API contracts.
* Predictable upgrades.
* Easier client migration.
* Improved maintainability.
* Better documentation.
* Independent client evolution.

## Negative

* Multiple versions may need to be maintained simultaneously.
* Version-specific testing increases over time.
* Additional routing complexity.

These trade-offs are acceptable for a long-lived platform.

---

# 15. Compliance Rules

All public APIs shall:

* include a major version in the URI
* maintain backward compatibility within a major version
* document breaking changes
* provide migration guidance for deprecated versions
* avoid introducing breaking changes into supported versions

Exceptions require explicit architectural review and approval.

---

# 16. Future Enhancements

Future enhancements may include:

* automated API compatibility validation
* API lifecycle dashboards
* version usage analytics
* automated deprecation notifications
* OpenAPI version comparison
* API governance tooling

These enhancements should preserve the URI-based versioning strategy.

---

# 17. Review Schedule

Review this ADR when:

* introducing API version 2
* exposing public partner APIs
* adopting GraphQL or gRPC
* changing API governance policies
* modifying the versioning strategy

---

# 18. Decision Summary

Investment OS adopts URI-based API versioning to ensure stable, predictable, and backward-compatible API evolution.

Every public REST endpoint includes an explicit major version as part of its URI. Breaking changes require a new major version, while backward-compatible enhancements continue within the existing version. This strategy enables independent client upgrades, supports long-term platform evolution, and provides a clear governance model for managing API lifecycles.

**Decision:** Accepted

**Effective Release:** Phase 2 – API Infrastructure

