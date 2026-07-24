<a id="investment-os-engineering-handbook"></a># Investment OS Engineering Handbook

<a id="chapter-04-api-standards"></a># Chapter 04 – API Standards

__Version:__ 1\.0

__Project:__ Investment OS

<a id="table-of-contents"></a># Table of Contents

1. Purpose
2. API Design Philosophy
3. REST Principles
4. API Versioning
5. URL Standards
6. HTTP Methods
7. Request Standards
8. Response Standards
9. HTTP Status Codes
10. Error Handling
11. Pagination
12. Filtering
13. Sorting
14. Field Selection
15. Authentication
16. Authorization
17. Rate Limiting
18. Idempotency
19. Validation
20. File Upload APIs
21. Long Running Operations
22. API Documentation
23. Performance Guidelines
24. Security Guidelines
25. Observability
26. Deprecation Policy
27. Version Migration
28. API Review Checklist
29. Common Anti\-Patterns
30. Definition of Done

<a id="purpose"></a># 1\. Purpose

This document defines the API design standards for Investment OS\.

Objectives:

- Consistent API design
- Predictable behavior
- High usability
- Strong security
- Easy integration
- Long\-term maintainability

Every public and internal HTTP API must comply with these standards\.

<a id="api-design-philosophy"></a># 2\. API Design Philosophy

APIs are products\.

A well\-designed API should be:

- Simple
- Consistent
- Discoverable
- Secure
- Backward compatible
- Self\-documenting

Design APIs around business resources rather than database tables\.

<a id="rest-principles"></a># 3\. REST Principles

REST principles adopted:

- Resource\-oriented URLs
- Stateless requests
- Standard HTTP methods
- Standard HTTP status codes
- Cache\-friendly responses where applicable
- Uniform interface

Example:

/startups  
/founders  
/investments  
/portfolios  
/documents

Avoid verbs in resource names\.

Good:

POST /investments

Avoid:

/createInvestment

<a id="api-versioning"></a># 4\. API Versioning

Every endpoint must include an explicit version\.

Example:

/api/v1/startups

Future versions:

/api/v2/startups

Major versions indicate breaking changes\.

Minor enhancements should remain backward compatible\.

<a id="url-standards"></a># 5\. URL Standards

Use lowercase\.

Use plural nouns\.

Good:

/api/v1/startups  
/api/v1/founders  
/api/v1/portfolios

Nested resources:

/api/v1/startups/\{startup\_id\}/investments

Avoid deep nesting beyond two resource levels\.

<a id="http-methods"></a># 6\. HTTP Methods

Method

Purpose

GET

Read

POST

Create

PUT

Replace

PATCH

Partial update

DELETE

Remove

Examples:

GET    /api/v1/startups  
POST   /api/v1/startups  
GET    /api/v1/startups/\{id\}  
PATCH  /api/v1/startups/\{id\}  
DELETE /api/v1/startups/\{id\}

<a id="request-standards"></a># 7\. Request Standards

Request bodies must use JSON unless binary data is required\.

Example:

\{  
  "name": "Example Startup",  
  "sector": "AI",  
  "country": "India"  
\}

Content\-Type:

application/json

Character encoding:

UTF\-8

<a id="response-standards"></a># 8\. Response Standards

Responses should be consistent\.

Success:

\{  
  "data": \{  
    "id": "123",  
    "name": "Example Startup"  
  \}  
\}

Collection:

\{  
  "data": \[  
    \.\.\.  
  \],  
  "pagination": \{  
    "page": 1,  
    "page\_size": 20,  
    "total": 250  
  \}  
\}

Metadata should remain separate from business data\.

<a id="http-status-codes"></a># 9\. HTTP Status Codes

Use standard HTTP semantics\.

Code

Meaning

200

Success

201

Created

202

Accepted

204

No Content

400

Bad Request

401

Unauthorized

403

Forbidden

404

Not Found

409

Conflict

422

Validation Error

429

Too Many Requests

500

Internal Error

503

Service Unavailable

Do not overload status codes\.

<a id="error-handling"></a># 10\. Error Handling

Every error response follows a standard schema\.

\{  
  "error": \{  
    "code": "STARTUP\_ALREADY\_EXISTS",  
    "message": "Startup already exists\.",  
    "details": \[\],  
    "request\_id": "abc123"  
  \}  
\}

Errors should be machine\-readable\.

Messages should remain human\-readable\.

<a id="pagination"></a># 11\. Pagination

Large collections require pagination\.

Example:

GET /startups?page=2&page\_size=50

Response:

\{  
  "pagination": \{  
    "page": 2,  
    "page\_size": 50,  
    "total\_pages": 12,  
    "total\_items": 598  
  \}  
\}

Avoid returning unbounded collections\.

<a id="filtering"></a># 12\. Filtering

Use query parameters\.

Example:

GET /startups?sector=AI  
GET /startups?country=India  
GET /startups?stage=Seed

Multiple filters may be combined\.

Filtering should remain predictable and documented\.

<a id="sorting"></a># 13\. Sorting

Example:

GET /investments?sort=created\_at  
GET /investments?sort=\-valuation

Convention:

- Ascending: field
- Descending: \-field

<a id="field-selection"></a># 14\. Field Selection

Allow clients to request subsets of fields when beneficial\.

Example:

GET /startups?fields=id,name,sector

This reduces payload size and improves performance\.

<a id="authentication"></a># 15\. Authentication

Primary authentication:

- OAuth2/JWT

Authorization header:

Authorization: Bearer <token>

Tokens should have finite lifetimes and support renewal\.

<a id="authorization"></a># 16\. Authorization

Use Role\-Based Access Control \(RBAC\)\.

Examples:

- Administrator
- Investment Manager
- Analyst
- Viewer

Authorization checks belong in the service or security layer, not scattered across endpoints\.

<a id="rate-limiting"></a># 17\. Rate Limiting

Protect public APIs\.

Example policy:

- 100 requests/minute \(standard\)
- Higher limits for trusted internal services

Responses should include appropriate headers where applicable\.

<a id="idempotency"></a># 18\. Idempotency

POST endpoints that create financial or external side effects should support idempotency\.

Example:

Idempotency\-Key: 5f8e\.\.\.

Duplicate requests with the same key should not create duplicate resources\.

<a id="validation"></a># 19\. Validation

Validate:

- Required fields
- Data types
- Length constraints
- Enumerations
- Numeric ranges
- Business invariants

Use Pydantic models for request validation\.

Business rule validation belongs in the service layer\.

<a id="file-upload-apis"></a># 20\. File Upload APIs

Uploads should:

- Validate MIME type
- Validate file size
- Scan for malware \(where infrastructure supports it\)
- Store metadata separately
- Return resource identifiers

Do not process large files synchronously if avoidable\.

<a id="long-running-operations"></a># 21\. Long Running Operations

Operations such as AI analysis or report generation should be asynchronous\.

Response:

202 Accepted

Return:

\{  
  "job\_id": "xyz123",  
  "status": "queued"  
\}

Provide a status endpoint for polling or support webhooks if appropriate\.

<a id="api-documentation"></a># 22\. API Documentation

Every endpoint must include:

- Summary
- Description
- Parameters
- Request schema
- Response schema
- Error responses
- Authentication requirements
- Example requests
- Example responses

OpenAPI documentation must remain synchronized with implementation\.

<a id="performance-guidelines"></a># 23\. Performance Guidelines

Representative goals:

- Efficient pagination
- Minimize payload size
- Avoid N\+1 database queries
- Compress large responses
- Cache read\-heavy endpoints where appropriate

Performance objectives should be defined through service\-level objectives \(SLOs\)\.

<a id="security-guidelines"></a># 24\. Security Guidelines

Every endpoint must:

- Authenticate
- Authorize
- Validate inputs
- Sanitize outputs where required
- Log security\-relevant events
- Protect against common web vulnerabilities

Never expose internal exception details to clients\.

<a id="observability"></a># 25\. Observability

Each request should include:

- Request ID
- Correlation ID
- Timestamp
- User identifier \(when authenticated\)

Log:

- Request duration
- Response status
- Significant failures

Metrics should support operational monitoring\.

<a id="deprecation-policy"></a># 26\. Deprecation Policy

Deprecated endpoints should:

- Be documented
- Emit deprecation warnings where appropriate
- Provide migration guidance
- Remain available during the published transition period

Breaking removals require a new major API version\.

<a id="version-migration"></a># 27\. Version Migration

Migration guides should include:

- Breaking changes
- New features
- Deprecated fields
- Replacement endpoints
- Upgrade examples

Clients should have sufficient time to migrate\.

<a id="api-review-checklist"></a># 28\. API Review Checklist

Before approval, verify:

- Resource names are consistent\.
- HTTP methods are appropriate\.
- Status codes are correct\.
- Validation is complete\.
- Authentication is enforced\.
- Authorization is verified\.
- Pagination is implemented where required\.
- Error responses follow the standard schema\.
- OpenAPI documentation is updated\.
- Tests cover success and failure scenarios\.

<a id="common-anti-patterns"></a># 29\. Common Anti\-Patterns

Avoid:

- Verbs in URLs
- Inconsistent JSON structures
- Returning 200 for error conditions
- Exposing database identifiers unnecessarily
- Mixing business logic into controllers
- Unbounded collection responses
- Breaking API contracts without versioning
- Returning stack traces to clients
- Ignoring idempotency for create operations with external effects

<a id="definition-of-done"></a># 30\. Definition of Done

An API endpoint is complete only when:

- Request validation is implemented\.
- Business logic is delegated appropriately\.
- Authentication and authorization are enforced\.
- Success and error responses follow the standard schema\.
- OpenAPI documentation is complete\.
- Unit and integration tests pass\.
- Performance considerations have been reviewed\.
- Logging and metrics are implemented\.
- Security review is complete\.

<a id="summary"></a># Summary

The API layer is the public contract of Investment OS\.

Consistency, backward compatibility, and clear contracts are more valuable than short\-term implementation convenience\.

Every API should be designed as if external developers will depend on it for years\.

