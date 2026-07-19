Next.js Frontend
        │
        ▼
FastAPI REST API
        │
        ▼
Business Services
        │
 ┌──────┼─────────┐
 │      │         │
 ▼      ▼         ▼
Postgres Redis   AI Agents
 │                │
 │        ┌───────┴────────┐
 ▼        ▼                ▼
Startup DB  Investment Scoring  Document Analysis
                           │
                           ▼
                    LLM + RAG Pipeline

# ---------------------------------------------
          New Startup
          
          ↓
          
          Basic Information
          
          ↓
          
          Upload Pitch Deck
          
          ↓
          
          Founder Details
          
          ↓
          
          Funding Round
          
          ↓
          
          Due Diligence
          
          ↓
          
          Investment Committee
          
          ↓
          
          Decision

      ┌───────────────┐
      │               │
Invest         Reject

      │               │

Portfolio      Watchlist

      │               │

Performance    Future Tracking

# ---------------------------------------------------
                    Browser
                       │
                       ▼
                 FastAPI Router
                       │
                       ▼
                  Middleware
                       │
                       ▼
             Dependency Injection
                       │
                       ▼
                Service Layer
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   Repository     AI Service     Notification
          │
          ▼
     PostgreSQL
          │
          ▼
        Redis


# Design Principles

| Component     | Responsibility                                             | Should NOT Do              |
| ------------- | ---------------------------------------------------------- | -------------------------- |
| Configuration | Load and validate settings                                 | Business logic             |
| Logging       | Record system activity                                     | Change application state   |
| Database      | Manage connections and sessions                            | Execute business workflows |
| Middleware    | Cross-cutting concerns (logging, request IDs, auth checks) | Business decisions         |
| API Router    | HTTP request/response routing                              | Direct database access     |
| Service       | Business rules and orchestration                           | Raw SQL queries            |
| Repository    | Database CRUD operations                                   | Business validation        |
| Models        | Database structure and relationships                       | HTTP or business logic     |
| Schemas       | Request/response validation and serialization              | Database access            |
| Security      | Authentication and cryptographic utilities                 | User management workflows  |
| Utilities     | Generic helper functions                                   | Domain-specific logic      |
| AI (future)   | AI inference and analysis                                  | Core CRUD operations       |

| Module        | Owns                     | Never Owns             |
| ------------- | ------------------------ | ---------------------- |
| Configuration | Application settings     | Business rules         |
| Logging       | Logging infrastructure   | Decision making        |
| Database      | Connections and sessions | Business workflows     |
| Middleware    | Cross-cutting concerns   | Domain logic           |
| Router        | HTTP routing             | Direct database access |
| Service       | Business workflows       | SQL implementation     |
| Repository    | Data persistence         | Business validation    |
| Model         | Database structure       | HTTP behavior          |
| Schema        | API validation           | Persistence            |
| Security      | Authentication utilities | User workflows         |
| Utilities     | Generic helpers          | Domain-specific logic  |


# -------------------------------------------------------------------------

Coding Standards for Implementation

Every module should adhere to the following principles:

Single Responsibility: One clear purpose per module.
Dependency Injection: Never instantiate shared resources directly; receive them through injection.
Structured Logging: Log entry, exit, errors, and significant events with a request ID.
Centralized Error Handling: Convert exceptions into standard application errors with consistent error codes.
Stateless Services: Services should not maintain mutable state between requests.
Repository Isolation: All database access must be encapsulated in repositories.
Schema Validation: Validate all external input before invoking business logic.
Transaction Boundaries: Transactions should be started and completed at the service layer, with repositories performing only persistence operations.
Consistent Responses: Success and error responses should follow a uniform API contract.
Testability: Every module should expose clear interfaces so it can be unit-tested independently.

# ------------------------------------------------------------------
Coding Standards

| Tool            | Standard       |
| --------------- | -------------- |
| Package Manager | **uv**         |
| Python          | **3.12**       |
| Formatter       | **Black**      |
| Linter          | **Ruff**       |
| Type Checker    | **MyPy**       |
| Test Framework  | **pytest**     |
| Coverage        | **pytest-cov** |
| Pre-commit      | **pre-commit** |

