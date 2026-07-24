# Investment OS Engineering Handbook

## Chapter 07 – Error Handling Standards

__Version: __1\.0  
Project: Investment OS

## 1\. Purpose

Define consistent error handling practices across Investment OS to improve reliability, security, maintainability, observability, and user experience\.

## 2\. Principles

\- Fail fast and fail safely\.  
\- Never hide exceptions\.  
\- Preserve root cause using exception chaining\.  
\- Return consistent API errors\.  
\- Log once with sufficient context\.  
\- Avoid leaking internal implementation details\.

## 3\. Error Classification

Categories:  
• Validation Errors  
• Authentication Errors  
• Authorization Errors  
• Business Rule Errors  
• Resource Not Found  
• Conflict Errors  
• External Service Errors  
• Infrastructure Errors  
• Database Errors  
• AI Service Errors  
• Internal Errors

## 4\. Exception Hierarchy

Create a common base exception \(ApplicationError\) with specialized subclasses such as ValidationError, AuthenticationError, AuthorizationError, BusinessRuleError, NotFoundError, ConflictError, ExternalServiceError, DatabaseError, AIServiceError, and InternalError\.

## 5\. Layer Responsibilities

API Layer: translate exceptions into HTTP responses\.  
Service Layer: raise business exceptions\.  
Repository Layer: translate persistence exceptions\.  
Infrastructure: wrap external failures with contextual exceptions\.

## 6\. Error Response Standard

All APIs should return a consistent structure:  
\{  
  "error": \{  
    "code": "STARTUP\_NOT\_FOUND",  
    "message": "Startup not found\.",  
    "request\_id": "\.\.\.",  
    "details": \[\]  
  \}  
\}

## 7\. HTTP Mapping

400 Validation  
401 Authentication  
403 Authorization  
404 Not Found  
409 Conflict  
422 Business Validation  
429 Rate Limit  
500 Internal  
503 External Dependency

## 8\. Logging

Log errors with request\_id, correlation\_id, user\_id \(if available\), exception type, stack trace \(internal only\), execution context, and elapsed time\. Never log passwords, tokens, or secrets\.

## 9\. Retry Policy

Retry only transient failures \(timeouts, temporary network issues, rate limits\)\. Never retry validation or business rule failures\. Use exponential backoff with jitter\.

## 10\. Database Errors

Translate ORM/database exceptions into domain\-specific exceptions\. Do not expose SQL statements or schema details to clients\.

## 11\. AI Error Handling

Classify prompt validation failures, model unavailability, timeout, tool execution failures, output validation failures, and safety policy violations separately\.

## 12\. Background Jobs

Record retry count, last failure, next retry time, and terminal failure reason\. Dead\-letter unrecoverable jobs\.

## 13\. Security

Never expose stack traces, SQL errors, filesystem paths, or infrastructure details in API responses\.

## 14\. Code Review Checklist

✓ Exceptions are specific\.  
✓ Exception chaining preserved\.  
✓ Logs contain context\.  
✓ API returns standard error schema\.  
✓ Sensitive data is not exposed\.  
✓ Tests cover success and failure paths\.

## 15\. Anti\-Patterns

\- except Exception: pass  
\- Silent failures  
\- Generic error messages everywhere  
\- Logging the same exception multiple times  
\- Returning HTTP 200 for failures  
\- Swallowing root causes

## 16\. Definition of Done

Every feature includes consistent exceptions, API error mapping, logging, automated tests for failure scenarios, and updated documentation\.

