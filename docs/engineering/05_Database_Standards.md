<a id="investment-os-engineering-handbook"></a># Investment OS Engineering Handbook

<a id="chapter-05-database-standards"></a># Chapter 05 – Database Standards

__Version:__ 1\.0

__Project:__ Investment OS

<a id="table-of-contents"></a># Table of Contents

1. Purpose
2. Database Philosophy
3. Technology Stack
4. Database Architecture
5. Schema Design Principles
6. Naming Conventions
7. Primary Keys
8. Foreign Keys
9. Data Types
10. Constraints
11. Indexing Standards
12. Normalization
13. Denormalization
14. Transactions
15. Repository Pattern
16. SQLAlchemy Standards
17. Alembic Migration Standards
18. Soft Deletes
19. Audit Fields
20. Multi\-Tenant Design
21. Security Standards
22. Encryption Standards
23. Performance Standards
24. Query Standards
25. Views and Materialized Views
26. Stored Procedures Policy
27. Backup & Recovery
28. Data Retention
29. Observability
30. Review Checklist
31. Anti\-Patterns
32. Definition of Done

<a id="purpose"></a># 1\. Purpose

This document defines the database engineering standards for Investment OS\.

Objectives:

- Reliable data storage
- Long\-term maintainability
- High performance
- Strong integrity
- Secure data handling
- Predictable schema evolution

The database is the source of truth for all business entities\.

<a id="database-philosophy"></a># 2\. Database Philosophy

The database is a business asset—not just a persistence layer\.

Key principles:

- Integrity before convenience
- Explicit relationships
- Minimize duplication
- Schema evolution through migrations only
- Data consistency over premature optimization

Never treat the database as a simple key\-value store\.

<a id="technology-stack"></a># 3\. Technology Stack

Recommended stack:

- PostgreSQL
- SQLAlchemy ORM
- Alembic
- Async database driver \(when using async APIs\)
- Redis for caching only \(never as the system of record\)

<a id="database-architecture"></a># 4\. Database Architecture

API  
   │  
Service  
   │  
Repository  
   │  
SQLAlchemy ORM  
   │  
PostgreSQL

Business logic never accesses SQL directly\.

Repositories own persistence\.

<a id="schema-design-principles"></a># 5\. Schema Design Principles

Every table should represent a business concept\.

Examples:

- users
- organizations
- founders
- startups
- investments
- portfolios
- documents
- ai\_jobs
- audit\_logs

Avoid generic tables such as:

data  
master  
common  
misc

Names should communicate intent\.

<a id="naming-conventions"></a># 6\. Naming Conventions

Tables:

snake\_case  
plural nouns

Examples:

users  
organizations  
investments  
portfolio\_positions

Columns:

snake\_case

Examples:

created\_at  
updated\_at  
startup\_id  
founder\_id

Indexes:

idx\_users\_email  
idx\_startups\_sector

Foreign keys:

fk\_investments\_startup

Unique constraints:

uq\_users\_email

<a id="primary-keys"></a># 7\. Primary Keys

Use UUIDs for public entities\.

Example:

id UUID PRIMARY KEY

Benefits:

- Globally unique
- Difficult to enumerate
- Better for distributed systems

Avoid exposing sequential IDs in public APIs\.

<a id="foreign-keys"></a># 8\. Foreign Keys

Every relationship should be explicit\.

Example:

investment\.startup\_id  
    →  
startups\.id

Always define:

- Foreign key constraints
- Cascade behavior
- Referential integrity

Do not rely solely on application logic\.

<a id="data-types"></a># 9\. Data Types

Choose the smallest type that satisfies requirements\.

Examples:

Business Data

Type

Identifier

UUID

Currency

NUMERIC\(p,s\)

Percentage

NUMERIC

Timestamp

TIMESTAMP WITH TIME ZONE

Boolean

BOOLEAN

JSON metadata

JSONB

Never use floating\-point types for financial calculations\.

<a id="constraints"></a># 10\. Constraints

Prefer database constraints over application\-only validation\.

Examples:

- NOT NULL
- UNIQUE
- CHECK
- FOREIGN KEY

Business rules should be enforced at the appropriate layer, but data integrity belongs in the database whenever possible\.

<a id="indexing-standards"></a># 11\. Indexing Standards

Create indexes for:

- Primary keys
- Foreign keys
- Frequently filtered columns
- Frequently sorted columns
- Unique lookups

Review indexes periodically\.

Avoid excessive indexing that slows writes\.

<a id="normalization"></a># 12\. Normalization

Default target:

Third Normal Form \(3NF\)

Benefits:

- Reduced redundancy
- Easier updates
- Better integrity

Normalize unless there is measured evidence that denormalization is necessary\.

<a id="denormalization"></a># 13\. Denormalization

Denormalize only when justified\.

Examples:

- Reporting tables
- Aggregated analytics
- Read\-heavy dashboards

Document every denormalization decision in an ADR\.

<a id="transactions"></a># 14\. Transactions

Every business operation should execute within an appropriate transaction boundary\.

Examples:

- Create investment
- Update cap table
- Commit funding round

Avoid long\-running transactions\.

Keep transactions as short as possible\.

<a id="repository-pattern"></a># 15\. Repository Pattern

Repositories encapsulate persistence\.

Responsibilities:

- CRUD
- Queries
- Pagination
- Transaction participation

Repositories must not contain business rules\.

<a id="sqlalchemy-standards"></a># 16\. SQLAlchemy Standards

Guidelines:

- Declarative mappings
- Explicit relationships
- Lazy/eager loading chosen intentionally
- Avoid hidden query side effects
- Keep models focused on persistence

Domain workflows belong in services, not ORM models\.

<a id="alembic-migration-standards"></a># 17\. Alembic Migration Standards

Every schema change requires:

- Upgrade migration
- Downgrade migration
- Review
- Testing

Never edit historical migrations after they are applied in shared environments\.

Migration files should describe one logical change\.

<a id="soft-deletes"></a># 18\. Soft Deletes

Default strategy:

deleted\_at TIMESTAMP NULL

Benefits:

- Auditability
- Recovery
- Historical reporting

Permanent deletion should be reserved for approved operational or regulatory scenarios\.

<a id="audit-fields"></a># 19\. Audit Fields

Every business table should include:

created\_at  
updated\_at  
created\_by  
updated\_by

Where applicable:

deleted\_at  
deleted\_by

Audit fields support traceability and operational investigations\.

<a id="multi-tenant-design"></a># 20\. Multi\-Tenant Design

For organization\-scoped data:

organization\_id

Every tenant\-aware query must enforce tenant isolation\.

Cross\-tenant access is prohibited unless explicitly authorized\.

<a id="security-standards"></a># 21\. Security Standards

Protect the database through:

- Least\-privilege accounts
- Encrypted connections
- Secret management
- Role separation
- Audit logging

Application code should never embed credentials\.

<a id="encryption-standards"></a># 22\. Encryption Standards

Encrypt:

- Database connections \(TLS\)
- Sensitive backups
- Sensitive exported data

For highly sensitive fields, consider application\-level encryption in addition to database encryption\.

<a id="performance-standards"></a># 23\. Performance Standards

Monitor:

- Slow queries
- Missing indexes
- Lock contention
- Table growth
- Connection pool usage
- Query execution plans

Optimize based on measurements, not assumptions\.

<a id="query-standards"></a># 24\. Query Standards

Guidelines:

- Select only required columns
- Avoid SELECT \*
- Use parameterized queries
- Prevent N\+1 query patterns
- Paginate large result sets

Review query plans for expensive operations\.

<a id="views-and-materialized-views"></a># 25\. Views and Materialized Views

Use views for:

- Reusable reporting logic
- Simplified read models

Use materialized views for:

- Expensive aggregations
- Dashboard metrics

Refresh strategies should be documented\.

<a id="stored-procedures-policy"></a># 26\. Stored Procedures Policy

Business logic belongs in the application layer\.

Stored procedures may be used only when there is a demonstrated operational or performance requirement\.

Any stored procedure requires documentation and review\.

<a id="backup-recovery"></a># 27\. Backup & Recovery

Backup strategy should define:

- Full backups
- Incremental backups
- Retention period
- Encryption
- Recovery testing

Recovery procedures must be tested regularly\.

A backup that has never been restored is not a verified backup\.

<a id="data-retention"></a># 28\. Data Retention

Define retention policies for:

- Audit logs
- AI job history
- Temporary uploads
- Notifications
- Reports

Retention should align with business and regulatory requirements\.

Deletion policies should be documented\.

<a id="observability"></a># 29\. Observability

Monitor:

- Query latency
- Deadlocks
- Connection counts
- Replication health
- Storage growth
- Backup status
- Failed migrations

Database metrics should integrate with the platform monitoring system\.

<a id="review-checklist"></a># 30\. Review Checklist

Before approving schema changes, verify:

- Naming follows standards\.
- Constraints are appropriate\.
- Indexes are justified\.
- Migrations are reversible\.
- Transactions are correct\.
- Security implications are reviewed\.
- Performance impact has been considered\.
- Documentation is updated\.

<a id="common-anti-patterns"></a># 31\. Common Anti\-Patterns

Avoid:

- Generic table names
- Generic JSON columns replacing structured data without justification
- Missing foreign keys
- Missing indexes
- SELECT \*
- Business logic inside triggers
- Hard deletes by default
- Editing historical migrations
- Using FLOAT for money
- Duplicate business data without documented purpose

<a id="definition-of-done"></a># 32\. Definition of Done

A database change is complete only when:

- Schema design is reviewed\.
- Migration scripts are written and tested\.
- Constraints are defined\.
- Indexes are validated\.
- Rollback is verified\.
- Documentation is updated\.
- Performance impact is assessed\.
- Security review is complete\.
- Automated tests pass\.

<a id="summary"></a># Summary

The database is the foundation of Investment OS\.

Every schema decision should prioritize integrity, clarity, and long\-term maintainability\.

A well\-designed database enables reliable business operations, scalable analytics, and future AI capabilities while minimizing operational risk\.

