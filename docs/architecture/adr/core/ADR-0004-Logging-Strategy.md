# ADR-0004: Logging & Observability Strategy

**ADR ID:** ADR-0004

**Title:** Logging & Observability Strategy

**Status:** Accepted

**Date:** 2026-07-25

**Authors:** Investment OS Engineering Team

**Phase:** Phase 1 – Backend Foundation

**Supersedes:** None

**Related Documents:**

* `PROJECT_BIBLE.md`
* `ADR-0001-Project-Structure.md`
* `ADR-0003-Configuration-Management.md`
* `OBSERVABILITY.md`

---

# 1. Context

Investment OS is designed as a long-lived platform that will eventually support:

* REST APIs
* AI agents
* Background jobs
* Document processing
* Database operations
* External service integrations
* Multiple deployment environments

As the platform grows, troubleshooting through ad hoc debugging or console output becomes increasingly difficult.

A standardized logging strategy is required to:

* diagnose failures
* monitor application health
* support production operations
* enable auditing
* assist performance analysis
* simplify debugging

---

# 2. Problem Statement

The project must define:

* What should be logged?
* What should never be logged?
* How should logs be structured?
* How can requests be traced?
* How should logs support future monitoring platforms?

---

# 3. Decision

Investment OS adopts a **structured, centralized logging strategy**.

Logging shall be:

* structured
* machine-readable
* environment-aware
* correlation-friendly
* secure
* configurable
* independent of business logic

All application logging shall use a shared logging framework.

Direct `print()` statements are prohibited outside local debugging sessions.

---

# 4. Design Goals

The logging framework should provide:

* consistent log format
* request tracing
* configurable log levels
* minimal performance overhead
* support for centralized log aggregation
* security by default

---

# 5. Logging Architecture

```text
Application
      │
      ▼
Shared Logger
      │
      ▼
Logging Configuration
      │
      ▼
Console / File / External Collector
```

Application modules interact only with the shared logger.

Logging configuration determines the destination and format.

---

# 6. Repository Structure

```text
app/

core/

logging/

    logger.py
    config.py
    formatter.py
```

Responsibilities:

### logger.py

Provides the shared logger instance used throughout the application.

### config.py

Defines logging configuration.

Examples:

* log level
* handlers
* format
* rotation

### formatter.py

Defines structured log formatting.

---

# 7. Logging Principles

## Principle 1

Single Logging Framework

All modules use the shared logger.

Multiple logging frameworks are not permitted.

---

## Principle 2

Structured Logs

Every log entry should contain structured fields.

Example:

```json
{
  "timestamp": "...",
  "level": "INFO",
  "request_id": "...",
  "module": "...",
  "message": "..."
}
```

---

## Principle 3

Correlation IDs

Every incoming request receives a unique request identifier.

The identifier must appear in every log generated during request processing.

Example:

```text
Request-ID: 2ab4e54f...
```

This enables tracing across services and background tasks.

---

## Principle 4

Environment Awareness

Logging behavior may differ by environment.

| Environment | Log Level      |
| ----------- | -------------- |
| Development | DEBUG          |
| Test        | WARNING        |
| CI          | INFO           |
| Production  | INFO (default) |

Production deployments should avoid DEBUG logging unless investigating issues.

---

## Principle 5

Fail-Safe Logging

Logging failures must never prevent the application from processing requests.

If a logging sink becomes unavailable, the application should continue operating with reduced observability rather than fail.

---

# 8. Log Levels

Use standard logging levels consistently.

| Level    | Purpose                                                |
| -------- | ------------------------------------------------------ |
| DEBUG    | Detailed diagnostics for development                   |
| INFO     | Normal application events                              |
| WARNING  | Unexpected but recoverable situations                  |
| ERROR    | Failed operations affecting a request or task          |
| CRITICAL | Unrecoverable conditions requiring immediate attention |

Choosing the appropriate level is more important than logging frequently.

---

# 9. Required Context

Application logs should include, where applicable:

* timestamp
* log level
* request ID
* module name
* function name
* message
* execution time (for request completion)
* exception details (for errors)

This information enables efficient diagnosis without excessive verbosity.

---

# 10. Sensitive Data

The following information must **never** be written to logs:

* passwords
* API keys
* JWT tokens
* session identifiers
* authentication secrets
* encryption keys
* private cryptographic material
* personally identifiable information (PII) unless explicitly required and protected

Sensitive values should be masked or omitted before logging.

---

# 11. Request Logging

Every HTTP request should generate:

### Request Start

Include:

* HTTP method
* request path
* request ID

### Request Completion

Include:

* HTTP status
* response time
* request ID

This provides an end-to-end view of request processing.

---

# 12. Exception Logging

Unhandled exceptions should be logged once by the global exception handler.

Log entries should include:

* request ID
* exception type
* error message
* stack trace (when appropriate)

Avoid logging the same exception multiple times as it propagates through the stack.

---

# 13. Performance Logging

Performance metrics should focus on significant operations, such as:

* API request duration
* database query latency
* AI inference duration
* external API response time
* document processing time

Performance logging should support future optimization efforts without creating excessive log volume.

---

# 14. Alternatives Considered

## Option A – `print()` Statements

Advantages:

* Simple
* Immediate output

Disadvantages:

* No structure
* No log levels
* No filtering
* No request correlation

Decision:

Rejected.

---

## Option B – Module-Specific Loggers

Advantages:

* Familiar
* Flexible

Disadvantages:

* Inconsistent configuration
* Difficult centralized management

Decision:

Rejected as the primary strategy.

Modules may obtain child loggers from the shared configuration but should not define independent logging policies.

---

## Option C – Centralized Structured Logging

Advantages:

* Consistent format
* Easy aggregation
* Request tracing
* Production readiness
* Scalable

Decision:

Accepted.

---

# 15. Consequences

## Positive

* Consistent operational visibility.
* Faster debugging.
* Simplified incident investigation.
* Easier integration with monitoring platforms.
* Improved auditability.

## Negative

* Slight runtime overhead.
* Requires discipline when introducing new log messages.

These trade-offs are acceptable for a production-oriented platform.

---

# 16. Compliance Rules

Every new module should:

* use the shared logger
* avoid `print()` statements
* select appropriate log levels
* avoid duplicate logging
* protect sensitive information
* include request context when applicable

Logging configuration should not be duplicated across packages.

---

# 17. Future Enhancements

Future releases may introduce:

* JSON log formatting
* OpenTelemetry integration
* distributed tracing
* centralized log aggregation
* metrics dashboards
* alerting
* audit event streaming

These enhancements should build upon the centralized logging interface rather than changing application code.

---

# 18. Review Schedule

Review this ADR:

* before introducing distributed services
* before adopting a centralized observability platform
* when adding background job processing
* during major production readiness reviews

---

# 19. Decision Summary

Investment OS adopts a centralized, structured logging strategy with request correlation, configurable log levels, and secure handling of sensitive information.

The logging framework provides a consistent foundation for debugging, monitoring, auditing, and future observability capabilities while remaining independent of specific logging backends or monitoring tools.

**Decision:** Accepted

**Effective Release:** v0.1.0 – Backend Foundation

