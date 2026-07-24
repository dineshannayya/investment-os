<a id="investment-os-engineering-handbook"></a># Investment OS Engineering Handbook

<a id="chapter-02-python-coding-standards"></a># Chapter 02 – Python Coding Standards

__Version:__ 1\.0

__Project:__ Investment OS

<a id="table-of-contents"></a># Table of Contents

1. Purpose
2. Guiding Principles
3. Python Version
4. Code Style
5. Naming Conventions
6. Project Organization
7. Type Hints
8. Documentation Standards
9. Function Design
10. Class Design
11. Exception Handling
12. Logging
13. Configuration Management
14. Dependency Injection
15. Async Programming
16. Database Coding Standards
17. API Layer Standards
18. Service Layer Standards
19. Repository Layer Standards
20. AI Module Standards
21. Security Standards
22. Performance Standards
23. Testing Expectations
24. Code Review Checklist
25. Anti\-Patterns

<a id="purpose"></a># 1\. Purpose

This document defines the Python coding standards for Investment OS\.

The objectives are:

- Consistent code style
- High readability
- Predictable architecture
- Strong typing
- High testability
- Long\-term maintainability

Every Python module in the repository must comply with these standards\.

<a id="guiding-principles"></a># 2\. Guiding Principles

Code should optimize for:

1. Readability
2. Simplicity
3. Correctness
4. Maintainability
5. Testability

Avoid clever code\.

Prefer boring, predictable code\.

<a id="python-version"></a># 3\. Python Version

Supported version:

Python 3\.12\+

Features encouraged:

- Structural pattern matching
- Exception groups \(where appropriate\)
- Dataclasses
- Modern typing syntax
- Context managers
- pathlib
- enum\.StrEnum \(when string enums are appropriate\)

Avoid legacy compatibility workarounds unless there is a documented requirement\.

<a id="code-style"></a># 4\. Code Style

Formatting is automated\.

Tools:

- Black
- Ruff
- isort \(or Ruff import sorting\)
- mypy

Never manually format code to override automated tools\.

Maximum line length:

88 characters

One import per line unless grouped by formatter\.

<a id="naming-conventions"></a># 5\. Naming Conventions

Modules

portfolio\_service\.py

Packages

investment\_committee/

Classes

PortfolioService  
FounderRepository

Functions

calculate\_irr\(\)  
create\_startup\(\)

Variables

startup\_id  
investment\_amount

Constants

MAX\_UPLOAD\_SIZE  
DEFAULT\_TIMEOUT

Private members

\_internal\_cache

Boolean variables should read naturally\.

Good:

is\_active  
has\_permission  
can\_invest

Avoid:

flag  
status1  
tmp

<a id="project-organization"></a># 6\. Project Organization

Each feature should follow a consistent structure\.

portfolio/  
  
api\.py  
service\.py  
repository\.py  
models\.py  
schemas\.py  
exceptions\.py  
README\.md  
tests/

Responsibilities must not overlap\.

<a id="type-hints"></a># 7\. Type Hints

Type hints are mandatory for all public interfaces\.

Good

def calculate\_nav\(  
    portfolio\_id: UUID,  
\) \-> Decimal:  
    \.\.\.

Avoid

def calculate\_nav\(id\):  
    \.\.\.

Prefer built\-in generics:

list\[str\]  
dict\[str, Any\]  
set\[UUID\]

Use typing\.Protocol for interfaces where appropriate\.

Avoid Any unless there is a documented reason\.

<a id="documentation-standards"></a># 8\. Documentation Standards

Public modules require a module docstring\.

Public classes require a class docstring\.

Public functions require docstrings\.

Example:

def calculate\_roi\(  
    investment: Decimal,  
    exit\_value: Decimal,  
\) \-> Decimal:  
    """Calculate return on investment\."""

Document:

- Purpose
- Parameters
- Return values
- Raised exceptions
- Side effects \(if any\)

<a id="function-design"></a># 9\. Function Design

Functions should:

- Perform one task
- Be easy to test
- Minimize side effects

Target size:

20–40 lines\.

Split large functions into smaller private helpers\.

Avoid more than five parameters\. Prefer configuration objects or dataclasses if needed\.

<a id="class-design"></a># 10\. Class Design

Classes should have a single responsibility\.

Example:

Good

PortfolioService

Bad

PortfolioService  
EmailService  
ReportGenerator

Prefer composition over inheritance\.

<a id="exception-handling"></a># 11\. Exception Handling

Catch only exceptions you can handle\.

Good

try:  
    repository\.save\(entity\)  
except DatabaseError as exc:  
    logger\.exception\("Failed to save portfolio"\)  
    raise PortfolioPersistenceError from exc

Avoid

except Exception:  
    pass

Always preserve exception chaining with raise \.\.\. from \.\.\.\.

<a id="logging"></a># 12\. Logging

Use structured logging\.

Every significant operation should include context\.

Example fields:

- request\_id
- correlation\_id
- user\_id
- organization\_id
- portfolio\_id

Never log:

- Passwords
- API keys
- Tokens
- Personally identifiable secrets

<a id="configuration-management"></a># 13\. Configuration Management

Never hard\-code:

- URLs
- Credentials
- Ports
- Timeouts
- Feature flags

Use a centralized settings module\.

Example:

settings\.database\_url  
settings\.jwt\_secret

<a id="dependency-injection"></a># 14\. Dependency Injection

Services should receive dependencies through constructors\.

Good

class PortfolioService:  
    def \_\_init\_\_\(  
        self,  
        repository: PortfolioRepository,  
    \):  
        self\.repository = repository

Avoid creating infrastructure objects inside business logic\.

<a id="async-programming"></a># 15\. Async Programming

Use async only for I/O\-bound work\.

Typical async operations:

- HTTP requests
- Database access \(async stack\)
- Message queues
- AI service calls
- File storage

Avoid using async for CPU\-bound calculations\.

<a id="database-coding-standards"></a># 16\. Database Coding Standards

Repositories own persistence\.

Good

Service  
    ↓  
Repository  
    ↓  
Database

Repositories should:

- Encapsulate queries
- Return domain objects
- Avoid leaking ORM implementation details

Services should not construct SQL\.

<a id="api-layer-standards"></a># 17\. API Layer Standards

API handlers should:

- Validate input
- Invoke services
- Return responses
- Handle HTTP concerns

API handlers must not contain business rules\.

<a id="service-layer-standards"></a># 18\. Service Layer Standards

Services contain:

- Business rules
- Validation beyond schema constraints
- Workflow orchestration
- Transaction coordination

Services should remain independent of FastAPI\-specific types\.

<a id="repository-layer-standards"></a># 19\. Repository Layer Standards

Repositories:

- Encapsulate persistence
- Manage CRUD operations
- Implement optimized queries

They should not:

- Send emails
- Call AI models
- Perform business calculations

<a id="ai-module-standards"></a># 20\. AI Module Standards

Each AI component should expose a common interface\.

Example responsibilities:

- Prompt construction
- Tool invocation
- Response validation
- Output normalization
- Evaluation logging

Keep prompt templates separate from orchestration logic\.

<a id="security-standards"></a># 21\. Security Standards

Validate all external input\.

Never trust:

- Query parameters
- JSON payloads
- Uploaded files
- HTTP headers

Always:

- Authenticate
- Authorize
- Validate
- Audit

<a id="performance-standards"></a># 22\. Performance Standards

Measure before optimizing\.

Avoid:

- N\+1 queries
- Blocking I/O in async code
- Repeated expensive computations

Cache only after measuring a bottleneck\.

<a id="testing-expectations"></a># 23\. Testing Expectations

Every new module requires:

- Unit tests
- Integration tests \(where applicable\)

Public methods should be testable without depending on external services\.

Aim for high\-value tests rather than simply maximizing coverage\.

<a id="code-review-checklist"></a># 24\. Code Review Checklist

Before approving a change, verify:

- Naming is clear\.
- Type hints are complete\.
- Business logic is in the service layer\.
- Repositories contain only persistence\.
- Exceptions are meaningful\.
- Logging includes useful context\.
- Tests cover expected behavior and failures\.
- Documentation is updated\.

<a id="anti-patterns"></a># 25\. Anti\-Patterns

The following are prohibited unless explicitly justified:

- God classes
- Functions longer than 100 lines
- Deep inheritance hierarchies
- Circular imports
- Global mutable state
- Hard\-coded secrets
- Silent exception handling
- Business logic in API endpoints
- SQL embedded in service classes
- Copy\-and\-paste implementations
- Unused code committed “for later”

<a id="summary"></a># Summary

Python is the implementation language of Investment OS, but consistency is more important than individual style\.

Every contributor should write code that is:

- Easy to understand
- Easy to test
- Easy to review
- Easy to maintain
- Secure by default
- Well documented

The objective is not merely to produce working software, but to create a codebase that remains reliable and understandable as the platform grows\.

