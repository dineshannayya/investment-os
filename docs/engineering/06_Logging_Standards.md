<a id="investment-os-engineering-handbook"></a># Investment OS Engineering Handbook

<a id="chapter-06-logging-standards"></a># Chapter 06 – Logging Standards

__Version:__ 1\.0

__Project:__ Investment OS

<a id="table-of-contents"></a># Table of Contents

1. Purpose
2. Logging Philosophy
3. Observability Principles
4. Logging Architecture
5. Log Levels
6. Structured Logging
7. Log Format
8. Correlation IDs
9. Request IDs
10. User Context
11. AI Agent Logging
12. Database Logging
13. API Logging
14. Background Worker Logging
15. Security Logging
16. Audit Logging
17. Exception Logging
18. Performance Logging
19. Business Event Logging
20. Sensitive Data Handling
21. Log Storage
22. Log Rotation
23. Log Retention
24. Centralized Logging
25. Metrics & Tracing
26. Alerting
27. Code Review Checklist
28. Anti\-Patterns
29. Definition of Done

<a id="purpose"></a># 1\. Purpose

Logging provides operational visibility into Investment OS\.

Its objectives are:

- Troubleshooting
- Monitoring
- Security
- Compliance
- Auditing
- Performance analysis
- AI evaluation
- Incident investigation

Logging is part of the software architecture—not merely debugging output\.

<a id="logging-philosophy"></a># 2\. Logging Philosophy

Logs exist primarily for operators and support engineers\.

Every log entry should help answer:

- What happened?
- When did it happen?
- Where did it happen?
- Who initiated it?
- Why did it happen?
- What was the outcome?

Avoid logs that require reading source code to understand\.

<a id="observability-principles"></a># 3\. Observability Principles

Investment OS adopts the “Three Pillars of Observability”:

Application  
     │  
 ┌───┼─────────┐  
 │   │         │  
 ▼   ▼         ▼  
Logs Metrics Traces

Logs describe __events__\.

Metrics describe __system health__\.

Traces describe __request flow__\.

All three are required in production\.

<a id="logging-architecture"></a># 4\. Logging Architecture

API  
 │  
 ▼  
Application Logger  
 │  
 ▼  
Structured JSON  
 │  
 ▼  
Log Aggregator  
 │  
 ▼  
Storage  
 │  
 ▼  
Dashboard / Alerts

Every service follows the same logging architecture\.

<a id="log-levels"></a># 5\. Log Levels

Use standard severity levels\.

Level

Usage

DEBUG

Development diagnostics

INFO

Normal business events

WARNING

Recoverable issues

ERROR

Failed operations

CRITICAL

System\-wide failures

Example:

logger\.info\("Investment created\."\)  
logger\.warning\("Retrying API call\."\)  
logger\.error\("Database transaction failed\."\)  
logger\.critical\("Primary database unavailable\."\)

Never misuse log levels\.

<a id="structured-logging"></a># 6\. Structured Logging

All production logs must be JSON\.

Example:

\{  
  "timestamp":"2026\-07\-20T09:30:00Z",  
  "level":"INFO",  
  "service":"investment\-api",  
  "event":"startup\_created",  
  "startup\_id":"uuid",  
  "user\_id":"uuid",  
  "request\_id":"abc123"  
\}

Never log free\-form text only\.

Structured logs enable searching and dashboards\.

<a id="log-format"></a># 7\. Log Format

Required fields:

timestamp  
level  
service  
module  
event  
message  
request\_id  
correlation\_id  
environment  
version  
hostname

Optional fields:

organization\_id  
user\_id  
startup\_id  
investment\_id  
portfolio\_id  
job\_id  
duration\_ms

Keep field names consistent across services\.

<a id="correlation-ids"></a># 8\. Correlation IDs

Every workflow spanning multiple services must use a Correlation ID\.

Example:

Correlation\-ID: c4b51\.\.\.

The same identifier must appear in every related log entry\.

This enables end\-to\-end tracing\.

<a id="request-ids"></a># 9\. Request IDs

Every incoming HTTP request receives a Request ID\.

Example:

X\-Request\-ID

Returned in:

- Response headers
- Logs
- Error responses

This allows support teams to trace individual requests\.

<a id="user-context"></a># 10\. User Context

When authenticated, include:

- user\_id
- organization\_id
- role

Never log:

- Passwords
- Access tokens
- Refresh tokens
- Session secrets

<a id="ai-agent-logging"></a># 11\. AI Agent Logging

AI workflows require additional visibility\.

Log:

- Agent name
- Prompt version
- Model identifier
- Tool invocations
- Input token count
- Output token count
- Latency
- Cost estimate
- Evaluation score

Do not log sensitive prompts or confidential data unless explicitly approved\.

<a id="database-logging"></a># 12\. Database Logging

Log:

- Transaction start/end
- Slow queries
- Deadlocks
- Migration execution
- Connection failures

Avoid logging every SQL statement in production\.

Enable detailed SQL logs only for troubleshooting\.

<a id="api-logging"></a># 13\. API Logging

Log:

- HTTP method
- URL
- Response status
- Latency
- Payload size \(if useful\)
- Authenticated user \(where applicable\)

Do not log full request bodies containing sensitive information\.

<a id="background-worker-logging"></a># 14\. Background Worker Logging

Workers should log:

- Job queued
- Job started
- Progress milestones
- Completion
- Failure
- Retry attempts

Example events:

report\_generated  
ai\_analysis\_completed  
email\_sent  
document\_processed

<a id="security-logging"></a># 15\. Security Logging

Log all security\-relevant events:

- Login success
- Login failure
- Permission denied
- Token refresh
- Password reset
- MFA events
- Account lockout

Security logs should be retained according to organizational policy\.

<a id="audit-logging"></a># 16\. Audit Logging

Audit logs record business actions\.

Examples:

- Startup created
- Investment approved
- Portfolio updated
- Document deleted
- User role changed

Audit logs should be immutable\.

<a id="exception-logging"></a># 17\. Exception Logging

Always log:

- Exception type
- Message
- Stack trace \(internal only\)
- Request ID
- Correlation ID

Example:

logger\.exception\(  
    "Failed to create investment\."  
\)

Use exception chaining to preserve root causes\.

<a id="performance-logging"></a># 18\. Performance Logging

Capture:

- API latency
- Database latency
- AI inference duration
- Cache hit/miss ratio
- Queue wait time
- Background job duration

Performance logs support optimization and capacity planning\.

<a id="business-event-logging"></a># 19\. Business Event Logging

Business events include:

- Investment submitted
- Due diligence completed
- Founder profile updated
- Portfolio valuation calculated

Business logs support analytics and reporting\.

<a id="sensitive-data-handling"></a># 20\. Sensitive Data Handling

Never log:

- Passwords
- API keys
- JWTs
- Credit card data
- Bank account numbers
- Private cryptographic keys

Mask:

\*\*\*\*\*\*\*\*\*\*\*\*

Apply redaction before log emission\.

<a id="log-storage"></a># 21\. Log Storage

Recommended architecture:

Application  
     │  
     ▼  
Log Collector  
     │  
     ▼  
Central Log Store

Logs should not remain only on local disks\.

<a id="log-rotation"></a># 22\. Log Rotation

Rotation policies should prevent uncontrolled disk usage\.

Example:

- Daily rotation
- Size limits
- Compression
- Automatic cleanup

Applications should not require manual log maintenance\.

<a id="log-retention"></a># 23\. Log Retention

Example policy:

Category

Retention

Debug

7 days

Application

90 days

Security

1 year

Audit

7 years \(subject to legal/regulatory requirements\)

Retention periods should align with business, legal, and compliance needs\.

<a id="centralized-logging"></a># 24\. Centralized Logging

All services send logs to a central platform\.

Benefits:

- Unified search
- Cross\-service correlation
- Alerting
- Dashboards
- Incident investigation

Avoid per\-service log silos\.

<a id="metrics-tracing"></a># 25\. Metrics & Tracing

Logging complements metrics and distributed tracing\.

Representative metrics:

- Request rate
- Error rate
- Latency
- Queue depth
- AI inference duration
- Database response time

Distributed traces should connect service boundaries using correlation identifiers\.

<a id="alerting"></a># 26\. Alerting

Critical events should generate alerts\.

Examples:

- Database unavailable
- Authentication failures spike
- AI service unavailable
- Queue backlog exceeds threshold
- Error rate exceeds SLO

Alert fatigue should be avoided by defining meaningful thresholds\.

<a id="code-review-checklist"></a># 27\. Code Review Checklist

Verify:

- Logs are structured\.
- Log levels are appropriate\.
- Sensitive data is excluded\.
- Correlation IDs are propagated\.
- Request IDs are included\.
- Exceptions are logged correctly\.
- Business events are recorded\.
- Audit requirements are satisfied\.

<a id="common-anti-patterns"></a># 28\. Common Anti\-Patterns

Avoid:

- Logging passwords
- Logging access tokens
- Excessive DEBUG logs in production
- Logging every SQL query by default
- Unstructured string concatenation
- Missing request identifiers
- Duplicate log messages
- Logging and swallowing exceptions
- Using print\(\) instead of the logging framework

<a id="definition-of-done"></a># 29\. Definition of Done

A feature is complete only when:

- Structured logs are implemented\.
- Request and correlation IDs are propagated\.
- Security events are logged\.
- Audit events are captured where required\.
- Performance metrics are available\.
- Sensitive information is redacted\.
- Logging has been reviewed\.
- Documentation is updated\.

<a id="summary"></a># Summary

Logging is an operational capability, not a debugging technique\.

A consistent logging strategy enables reliable production support, effective incident response, security investigations, compliance reporting, performance optimization, and AI system evaluation\.

Every log should provide actionable information while protecting sensitive data and maintaining consistency across the platform\.

