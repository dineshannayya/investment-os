<a id="investment-os-engineering-handbook"></a># Investment OS Engineering Handbook

<a id="chapter-12-code-review-standards"></a># Chapter 12 – Code Review Standards

__Version:__ 1\.0

__Project:__ Investment OS

<a id="table-of-contents"></a># Table of Contents

1. Purpose
2. Code Review Philosophy
3. Engineering Principles
4. Review Workflow
5. Pull Request Standards
6. Reviewer Responsibilities
7. Author Responsibilities
8. Review Checklist
9. Architecture Review
10. API Review
11. Database Review
12. AI Code Review
13. Security Review
14. Performance Review
15. Testing Review
16. Documentation Review
17. Logging & Observability Review
18. Infrastructure Review
19. Dependency Review
20. Review Comments
21. Approval Rules
22. Merge Policy
23. Metrics
24. Anti\-Patterns
25. Definition of Done

<a id="purpose"></a># 1\. Purpose

This document defines the engineering standards for code reviews across Investment OS\.

Objectives:

- Improve software quality
- Detect defects early
- Maintain architectural consistency
- Share engineering knowledge
- Improve security
- Reduce technical debt
- Ensure long\-term maintainability

Code review is a collaborative engineering activity, not merely an approval process\.

<a id="code-review-philosophy"></a># 2\. Code Review Philosophy

Every code review should answer five questions:

- Is the feature correct?
- Is the design maintainable?
- Is the implementation secure?
- Is the code understandable?
- Is the change aligned with architecture?

The goal is continuous improvement of both the software and the engineering team\.

<a id="engineering-principles"></a># 3\. Engineering Principles

Reviewers should evaluate changes against these principles:

- SOLID
- DRY \(Don’t Repeat Yourself\)
- KISS \(Keep It Simple\)
- YAGNI \(You Aren’t Gonna Need It\)
- Separation of Concerns
- Clean Architecture
- Single Responsibility

Code should optimize for readability before cleverness\.

<a id="review-workflow"></a># 4\. Review Workflow

text id="h0w1v6" Feature Branch       ↓ Pull Request       ↓ Automated CI       ↓ Peer Review       ↓ Revision       ↓ Approval       ↓ Merge

Every merge to a protected branch requires successful automated checks\.

<a id="pull-request-standards"></a># 5\. Pull Request Standards

Each pull request should include:

- Business objective
- Technical summary
- Related issue
- Architecture impact
- Database migration impact
- API changes
- AI prompt/model changes \(if applicable\)
- Testing performed
- Rollback considerations
- Documentation updates

Recommended size:

- Ideal: < 400 changed lines
- Acceptable: 400–800 changed lines
- Large PRs \(>800 lines\) should be split unless there is a strong justification\.

<a id="reviewer-responsibilities"></a># 6\. Reviewer Responsibilities

Reviewers should:

- Understand the change
- Verify correctness
- Check architecture alignment
- Identify security concerns
- Evaluate maintainability
- Confirm test coverage
- Verify documentation updates

Reviewers should explain concerns and suggest improvements rather than simply rejecting code\.

<a id="author-responsibilities"></a># 7\. Author Responsibilities

Authors should:

- Keep changes focused
- Provide context
- Run tests locally
- Resolve CI failures
- Respond constructively to feedback
- Update documentation
- Remove obsolete code

Authors remain responsible for the code after merge\.

<a id="general-review-checklist"></a># 8\. General Review Checklist

Verify:

- Code compiles
- Naming is meaningful
- Functions are cohesive
- Complexity is reasonable
- Error handling is complete
- Logging is appropriate
- Configuration is externalized
- Dead code removed
- Magic numbers eliminated
- Comments explain intent rather than implementation

<a id="architecture-review"></a># 9\. Architecture Review

Confirm that changes:

- Respect module boundaries
- Preserve layering
- Follow dependency direction
- Avoid circular dependencies
- Reuse existing abstractions
- Do not duplicate business logic

Architectural deviations should be documented with an ADR\.

<a id="api-review"></a># 10\. API Review

Review:

- REST conventions
- HTTP status codes
- Input validation
- Output schemas
- Authentication
- Authorization
- Error responses
- Pagination
- Versioning

Breaking API changes require migration planning\.

<a id="database-review"></a># 11\. Database Review

Verify:

- Naming conventions
- Normalization
- Constraints
- Indexes
- Migration quality
- Rollback strategy
- Transaction boundaries
- Query efficiency

Schema changes should include updated documentation\.

<a id="ai-code-review"></a># 12\. AI Code Review

For AI\-related changes, verify:

- Prompt versioning
- Model selection rationale
- Tool permissions
- Context construction
- Evaluation results
- Hallucination testing
- Cost analysis
- Safety guardrails
- Monitoring hooks

Prompt changes should receive the same level of review as application code\.

<a id="security-review"></a># 13\. Security Review

Review:

- Authentication
- Authorization
- Input validation
- Output encoding \(where applicable\)
- Secret handling
- Encryption
- Dependency vulnerabilities
- File upload validation
- Access control

Never approve code that exposes sensitive information\.

<a id="performance-review"></a># 14\. Performance Review

Consider:

- Algorithmic complexity
- Database queries
- Memory usage
- Network calls
- Caching opportunities
- Concurrency
- Resource cleanup

Optimization should be driven by evidence rather than speculation\.

<a id="testing-review"></a># 15\. Testing Review

Verify that:

- Unit tests are included
- Integration tests cover new behavior
- Existing tests remain valid
- Failure scenarios are tested
- Edge cases are considered
- Regression risks are addressed

Every defect fixed should ideally be accompanied by a test that prevents recurrence\.

<a id="documentation-review"></a># 16\. Documentation Review

Confirm updates to:

- README
- API documentation
- Architecture documents
- Database documentation
- AI documentation
- Runbooks
- ADRs \(if applicable\)

Documentation should evolve with the implementation\.

<a id="logging-observability-review"></a># 17\. Logging & Observability Review

Review:

- Structured logging
- Log levels
- Correlation IDs
- Request IDs
- Audit events
- Metrics
- Tracing hooks

Logs should provide operational insight without exposing sensitive data\.

<a id="infrastructure-review"></a># 18\. Infrastructure Review

Infrastructure\-related changes should verify:

- Infrastructure as Code updates
- Environment configuration
- Container security
- Resource limits
- Secrets handling
- Deployment impact
- Rollback procedures

Infrastructure changes require the same rigor as application code\.

<a id="dependency-review"></a># 19\. Dependency Review

For every new dependency:

- Verify maintenance status
- Check license compatibility
- Assess security advisories
- Evaluate necessity
- Consider long\-term support

Avoid introducing dependencies for functionality that can be implemented simply with existing libraries\.

<a id="review-comments"></a># 20\. Review Comments

Effective feedback should be:

- Respectful
- Specific
- Actionable
- Supported by reasoning
- Focused on the code, not the individual

Differentiate between:

- __Must Fix__ \(correctness, security, reliability\)
- __Should Fix__ \(maintainability, readability\)
- __Suggestion__ \(optional improvements\)
- __Question__ \(clarification\)

<a id="approval-rules"></a># 21\. Approval Rules

A pull request may be approved only when:

- CI succeeds
- Required reviewers approve
- Blocking comments are resolved
- Documentation is updated
- Security concerns are addressed
- Tests pass

Approvals should reflect confidence in the change, not simply completion of a review\.

<a id="merge-policy"></a># 22\. Merge Policy

A pull request may be merged only if:

- Required approvals are present
- CI is green
- No unresolved blocking comments remain
- Merge conflicts are resolved
- Release criteria are satisfied

Squash, merge, or rebase strategies should be defined at the repository level and applied consistently\.

<a id="engineering-metrics"></a># 23\. Engineering Metrics

Track:

- Review turnaround time
- Review coverage
- Average pull request size
- Defects found during review
- Defects found after release
- Rework rate
- Review participation
- CI failure rate

Metrics should improve processes rather than evaluate individual performance\.

<a id="common-anti-patterns"></a># 24\. Common Anti\-Patterns

Avoid:

- Approving without reading the code
- “Looks good” reviews with no meaningful feedback
- Reviewing only formatting
- Ignoring architecture concerns
- Overly large pull requests
- Mixing unrelated changes
- Missing tests
- Missing documentation
- Nitpicking style already enforced by automated tools
- Delaying reviews unnecessarily

<a id="definition-of-done"></a># 25\. Definition of Done

A code change is complete only when:

- Code review is approved\.
- CI passes\.
- Tests pass\.
- Documentation is updated\.
- Security review is complete\.
- Performance impact is acceptable\.
- Logging and observability requirements are met\.
- Database migrations are reviewed \(if applicable\)\.
- AI evaluations are completed \(if applicable\)\.
- Merge requirements are satisfied\.

<a id="recommended-review-flow"></a># Recommended Review Flow

text id="r9c7l2" Developer     │     ▼ Create Pull Request     │     ▼ Automated CI     │     ▼ Peer Review     │  ┌──┼──────────────┐  ▼  ▼              ▼ Architecture   Security   Testing Review         Review     Review     │     ▼ Author Updates     │     ▼ Final Approval     │     ▼ Merge

<a id="summary"></a># Summary

Code review is a cornerstone of engineering excellence\.

A disciplined review process improves software quality, strengthens security, promotes architectural consistency, facilitates knowledge sharing, and reduces long\-term maintenance costs\.

By following these standards, Investment OS can maintain a high\-quality, sustainable codebase as the platform grows in complexity and scale\.

