# ADR-0104: Response Envelope

**ADR ID:** ADR-0104

**Title:** Response Envelope

**Status:** Accepted

**Date:** 2026-07-25

**Authors:** Investment OS Engineering Team

**Phase:** Phase 2 – API Infrastructure

**Supersedes:** None

**Related Documents:**

* ADR-0101 – FastAPI Architecture
* ADR-0102 – Middleware Architecture
* ADR-0103 – Exception Handling
* ADR-0105 – Dependency Injection
* ADR-0106 – API Versioning
* FASTAPI_DEVELOPMENT_GUIDE.md

---

# 1. Context

Investment OS exposes REST APIs that are consumed by multiple clients including:

* Web Frontend
* AI Agents
* Internal Automation
* Future Mobile Applications
* Third-party Integrations

Without a standardized response contract, different endpoints may return inconsistent response structures, making client development more complex and reducing maintainability.

A common response architecture is required.

---

# 2. Problem Statement

The platform must define:

* Should all APIs return a common structure?
* How should successful responses be represented?
* How should failures be represented?
* How should metadata be included?
* How can API contracts remain consistent across modules?

---

# 3. Decision

Investment OS adopts a **standardized response envelope** for all public REST APIs.

Every API response shall follow a consistent contract independent of the business domain.

The envelope provides a predictable structure while allowing individual endpoints to return different business payloads.

---

# 4. Design Goals

The response architecture should:

* provide consistency across APIs
* simplify client development
* improve API discoverability
* support future extensibility
* support metadata
* integrate with centralized exception handling
* remain backward compatible

---

# 5. Architectural Principles

## Consistency

Every endpoint returns responses using the same architectural structure.

---

## Separation of Concerns

The response envelope carries transport-level information.

Business objects remain independent of the transport format.

---

## Predictability

Clients should not need endpoint-specific parsing logic.

---

## Extensibility

The envelope should accommodate future metadata without breaking existing clients.

---

## Version Independence

Future API versions should preserve the response architecture unless a major version change is introduced.

---

# 6. Response Architecture

The response consists of two conceptual layers.

```text id="lkg5h6"
HTTP Response
      │
      ▼
Response Envelope
      │
      ├── Status Information
      ├── Metadata
      └── Business Payload
```

Business data is contained within a standardized transport structure.

---

# 7. Success Responses

Successful responses should include:

* operation status
* business payload
* optional metadata
* request correlation information (where applicable)

The envelope should remain consistent regardless of resource type.

---

# 8. Error Responses

Error responses shall integrate with the centralized exception handling architecture.

They should communicate:

* failure status
* error information
* diagnostic identifiers
* optional validation details

Internal implementation details must never be exposed.

---

# 9. Metadata

The response envelope may include metadata such as:

* pagination information
* execution time
* correlation identifier
* API version
* server timestamp
* request identifier

Metadata is intended to support infrastructure and client behavior rather than business logic.

---

# 10. Integration with Exception Handling

The global exception handler is responsible for producing standardized error responses.

Individual API endpoints should not construct error envelopes manually.

This ensures consistent behavior across the platform.

---

# 11. Integration with Middleware

Middleware may enrich the response envelope by adding infrastructure-related metadata such as:

* correlation identifiers
* request identifiers
* timing information
* security headers

Middleware shall not modify business payloads.

---

# 12. Integration with FastAPI

Route handlers should return business results.

Framework-level components are responsible for wrapping responses according to the standardized response architecture where appropriate.

This keeps route handlers focused on application behavior rather than transport formatting.

---

# 13. HTTP Status Codes

HTTP status codes remain the primary mechanism for communicating transport-level success or failure.

The response envelope complements HTTP semantics rather than replacing them.

Clients should interpret both:

* HTTP status
* standardized response structure

---

# 14. Alternative Approaches Considered

## Option A – Endpoint-Specific Responses

Each API returns an independently designed response.

### Advantages

* Maximum flexibility.

### Disadvantages

* Inconsistent API contracts.
* Increased client complexity.
* Difficult documentation.
* Higher maintenance cost.

**Decision:** Rejected.

---

## Option B – Standardized Response Envelope

All APIs follow a common response architecture.

### Advantages

* Consistent contracts.
* Easier client development.
* Better documentation.
* Simplified testing.
* Improved maintainability.

**Decision:** Accepted.

---

# 15. Consequences

## Positive

* Uniform API behavior.
* Simplified client implementation.
* Consistent error handling.
* Better OpenAPI documentation.
* Easier automated testing.
* Improved maintainability.

## Negative

* Slightly larger response payloads.
* Additional architectural abstraction.

These trade-offs are acceptable for an enterprise-grade platform.

---

# 16. Compliance Rules

Every public API shall:

* follow the standardized response architecture
* integrate with centralized exception handling
* use appropriate HTTP status codes
* avoid custom response formats
* avoid exposing internal implementation details
* preserve backward compatibility within an API version

Exceptions to this policy should be documented through a dedicated ADR.

---

# 17. Future Enhancements

Future enhancements may include:

* standardized application error codes
* localization support
* response signatures
* API deprecation metadata
* hypermedia links
* request diagnostics
* distributed tracing metadata

These enhancements should remain backward compatible whenever possible.

---

# 18. Review Schedule

Review this ADR when:

* introducing API version 2
* adding GraphQL endpoints
* introducing gRPC services
* modifying client integration strategy
* changing API transport protocols

---

# 19. Decision Summary

Investment OS adopts a standardized response envelope for all public REST APIs.

The response envelope establishes a consistent transport contract across all services while separating infrastructure metadata from business payloads. This architecture simplifies client development, improves maintainability, integrates with centralized exception handling, and provides a scalable foundation for future API evolution.

**Decision:** Accepted

**Effective Release:** Phase 2 – API Infrastructure

