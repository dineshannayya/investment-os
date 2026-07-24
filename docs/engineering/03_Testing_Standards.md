<a id="investment-os-engineering-handbook"></a># Investment OS Engineering Handbook

<a id="chapter-03-testing-standards"></a># Chapter 03 – Testing Standards

__Version:__ 1\.0

__Project:__ Investment OS

<a id="table-of-contents"></a># Table of Contents

1. Purpose
2. Testing Philosophy
3. Quality Goals
4. Testing Pyramid
5. Test Types
6. Test Organization
7. Naming Conventions
8. Unit Testing Standards
9. Integration Testing Standards
10. API Testing Standards
11. Repository Testing
12. Database Testing
13. Security Testing
14. Performance Testing
15. AI Testing Standards
16. Mocking Guidelines
17. Test Fixtures
18. Test Data Management
19. Coverage Requirements
20. Continuous Integration
21. Regression Testing
22. Code Review Checklist
23. Common Anti\-Patterns
24. Definition of Done

<a id="purpose"></a># 1\. Purpose

Testing exists to provide confidence that software behaves correctly today and continues to behave correctly after future changes\.

The objectives are:

- Detect defects early
- Prevent regressions
- Enable safe refactoring
- Support continuous delivery
- Protect business logic
- Verify security requirements

Testing is part of development—not an activity performed after coding is complete\.

<a id="testing-philosophy"></a># 2\. Testing Philosophy

Investment OS adopts the following principles:

- Every feature must be testable\.
- Tests should describe expected behavior\.
- Tests should be deterministic\.
- Tests should execute quickly\.
- Tests should be easy to understand\.
- Tests should be maintainable\.
- Production defects should result in new regression tests\.

The purpose of tests is to prevent future failures, not merely increase coverage numbers\.

<a id="quality-goals"></a># 3\. Quality Goals

Target engineering metrics:

Category

Target

Unit Test Coverage

≥90%

Core Infrastructure

100%

Public API Coverage

100%

Critical Business Rules

100%

Security Tests

Required

Regression Tests

Required

CI Pass Rate

100%

Coverage alone is not a quality metric\. Meaningful assertions are required\.

<a id="testing-pyramid"></a># 4\. Testing Pyramid

Investment OS follows the testing pyramid\.

               E2E Tests  
                  ▲  
          Integration Tests  
                  ▲  
            Component Tests  
                  ▲  
              Unit Tests

Most tests should be unit tests\.

End\-to\-end tests should focus on complete user journeys\.

<a id="test-types"></a># 5\. Test Types

The platform includes:

- Unit Tests
- Component Tests
- Integration Tests
- API Tests
- Repository Tests
- Database Tests
- AI Evaluation Tests
- Security Tests
- Performance Tests
- Load Tests
- Smoke Tests
- Regression Tests
- Acceptance Tests

Each type serves a different purpose and should not duplicate others\.

<a id="test-organization"></a># 6\. Test Organization

tests/  
  
unit/  
integration/  
api/  
repository/  
database/  
performance/  
security/  
ai/  
fixtures/  
test\_data/  
helpers/

Each directory has a single responsibility\.

Production code must never import test utilities\.

<a id="naming-conventions"></a># 7\. Naming Conventions

Files:

test\_portfolio\_service\.py

Functions:

def test\_create\_portfolio\_success\(\):  
    \.\.\.  
  
def test\_create\_portfolio\_duplicate\_name\(\):  
    \.\.\.

Names should describe expected behavior, not implementation details\.

<a id="unit-testing-standards"></a># 8\. Unit Testing Standards

Unit tests validate a single class or function in isolation\.

Characteristics:

- Fast
- Independent
- Deterministic
- No external services
- No real database
- No network calls

Pattern:

Arrange  
Act  
Assert

Example:

def test\_calculate\_roi\(\):  
    investment = Decimal\("1000"\)  
    exit\_value = Decimal\("1500"\)  
  
    roi = calculate\_roi\(investment, exit\_value\)  
  
    assert roi == Decimal\("0\.5"\)

Every logical branch should have corresponding tests\.

<a id="integration-testing-standards"></a># 9\. Integration Testing Standards

Integration tests verify interactions between components\.

Examples:

- Service ↔ Repository
- Repository ↔ Database
- API ↔ Service
- Authentication flow
- Transaction handling

Integration tests should use isolated test databases\.

Never reuse production databases\.

<a id="api-testing-standards"></a># 10\. API Testing Standards

Every endpoint requires tests for:

- Success responses
- Validation errors
- Authentication failures
- Authorization failures
- Resource not found
- Invalid input
- Unexpected server errors

Example scenarios:

POST /startups  
  
✓ Valid payload  
✓ Missing required fields  
✓ Duplicate startup  
✓ Unauthorized request  
✓ Invalid token

HTTP status codes must be verified\.

<a id="repository-testing"></a># 11\. Repository Testing

Repositories should verify:

- CRUD operations
- Query correctness
- Pagination
- Sorting
- Filtering
- Transaction rollback
- Constraint handling

Business rules belong in service tests, not repository tests\.

<a id="database-testing"></a># 12\. Database Testing

Verify:

- Migrations
- Constraints
- Foreign keys
- Indexes
- Cascade deletes
- Transactions

Every migration must include upgrade and downgrade validation\.

<a id="security-testing"></a># 13\. Security Testing

Security tests should verify:

- Authentication
- Authorization
- Role\-based access
- Token expiration
- Input validation
- Injection protection
- Rate limiting
- File upload validation

Security regressions must block releases\.

<a id="performance-testing"></a># 14\. Performance Testing

Performance testing measures:

- Response time
- Throughput
- Memory usage
- CPU utilization
- Database query performance

Representative goals:

- API latency within agreed SLOs
- No unexpected memory growth during long\-running workloads
- Efficient query execution for common use cases

Performance baselines should be versioned and monitored over time\.

<a id="ai-testing-standards"></a># 15\. AI Testing Standards

AI systems require additional validation beyond traditional software tests\.

Test categories include:

- Prompt version validation
- Output schema validation
- Hallucination detection
- Tool invocation correctness
- Deterministic behavior where applicable
- Safety policy checks
- Cost and latency monitoring

AI evaluation datasets should be version\-controlled\.

Changes to prompts or models should trigger evaluation before release\.

<a id="mocking-guidelines"></a># 16\. Mocking Guidelines

Mock external systems only\.

Examples:

- Email services
- Payment providers
- LLM APIs
- Cloud storage
- Third\-party REST APIs

Do not mock business logic\.

Prefer realistic fakes over excessive mocking where practical\.

<a id="test-fixtures"></a># 17\. Test Fixtures

Reusable fixtures belong in:

tests/fixtures/

Examples:

- Authenticated user
- Organization
- Portfolio
- Startup
- Investment
- Database session

Fixtures should be independent and composable\.

<a id="test-data-management"></a># 18\. Test Data Management

Test data must be:

- Minimal
- Readable
- Reproducible
- Version controlled

Avoid sharing mutable global data between tests\.

Factories and builders are preferred over copying JSON payloads\.

<a id="coverage-requirements"></a># 19\. Coverage Requirements

Coverage targets:

Layer

Target

Services

≥95%

Repositories

≥90%

APIs

≥90%

Core Utilities

100%

Security

100%

Critical Financial Logic

100%

Coverage reports should be generated automatically in CI\.

Coverage should not encourage trivial tests\.

<a id="continuous-integration"></a># 20\. Continuous Integration

Every pull request executes:

1. Ruff
2. Black \(format check\)
3. mypy
4. Unit tests
5. Integration tests
6. Coverage analysis
7. Security scanning
8. Docker build

A failed quality gate blocks merging\.

<a id="regression-testing"></a># 21\. Regression Testing

Every production defect requires:

1. A failing test that reproduces the issue\.
2. A code fix\.
3. The regression test to pass\.

This prevents the same defect from returning\.

Regression tests are never removed without justification\.

<a id="code-review-checklist"></a># 22\. Code Review Checklist

Reviewers should verify:

- Tests cover expected behavior\.
- Edge cases are included\.
- Failure scenarios are tested\.
- Assertions are meaningful\.
- Test names are descriptive\.
- Fixtures are reusable\.
- Mocks are appropriate\.
- Tests remain independent\.

<a id="common-anti-patterns"></a># 23\. Common Anti\-Patterns

Avoid:

- Tests that depend on execution order
- Shared mutable state
- Excessive mocking
- Assertions with no behavioral value
- Sleep\-based synchronization
- Hard\-coded timestamps
- Magic numbers without explanation
- Ignoring flaky tests instead of fixing them

Flaky tests must be investigated and resolved promptly\.

<a id="definition-of-done"></a># 24\. Definition of Done

A feature is considered complete only when:

- Unit tests pass
- Integration tests pass
- API tests pass
- Security checks pass
- Coverage targets are met
- Documentation is updated
- CI pipeline succeeds
- Code review is approved

Testing is a core engineering activity, not an optional deliverable\.

<a id="summary"></a># Summary

A robust testing strategy enables Investment OS to evolve with confidence\.

The objective is not simply to detect bugs, but to create a development process where engineers can refactor, extend, and deploy features safely and predictably\.

Quality is achieved through disciplined engineering practices, comprehensive automated testing, and continuous verification—not through coverage metrics alone\.

