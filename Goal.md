
# Overall Goal (V1)

  Build a web-based Investment Operating System that replaces Excel sheets and Word documents for startup evaluation, while keeping the architecture ready for AI agents.

# Phase 0 - Project Planning

1. Architecture

		Frontend (Next.js)
		↓
		REST API (FastAPI)
		↓
		Business Layer
		↓
		Repository Layer
		↓
		PostgreSQL
		↓
		Document Storage

2. Database Schema

	Startup
	Founder
	Investment Opportunity
	Funding Round
	Investment
	Valuation
	Due Diligence
	Risk
	Document
	Meeting
	Decision Journal
	Watchlist
	Portfolio

3. UI Sitemap

	Dashboard
	
	Startups
	    List
	    Details
	    Documents
	    Valuation
	    Due Diligence
	    Risks
	    Notes
	Watchlist
	Portfolio
	Investment Committee
	Reports
	Settings

4. API Design

	GET /startups
	POST /startups
	GET /startup/{id}
	PUT /startup/{id}
	DELETE /startup/{id}

# --------------------------------------------------------
# Development Roadmap
# --------------------------------------------------------

# Sprint 0 (Infrastructure)
No investment logic yet.
Deliverables:

	Git Repository
	Docker
	Docker Compose
	FastAPI
	Next.js
	PostgreSQL
	Redis
	Health Check
	Swagger
	GitHub Actions

# Sprint 1 (Startup Management)

	Dashboard
	Startup CRUD
	Founder CRUD
	Search
	Tags
	Sector
	Investment Stage

# Sprint 2 (Investment Workspace)
	Startup Profile
	Investment Ask
	Current Valuation
	Funding History
	Founder Details
	Meeting Notes
	Documents
	Timeline

# Sprint 3 (Due Diligence)

	Checklist
	Risks
	Open Issues
	Pending Items
	Questions
	Comments

# Sprint 4 (Valuation)

	Scorecard
	VC Method
	Berkus
	DCF
	Comparable
	Custom

# Sprint 5 (Decision Journal)

	Every startup gets:
		Decision
		Reason
		Confidence
		Expected Revenue
		Expected Valuation
		Expected Exit
		Review Date

# Sprint 6 (Watchlist)

Instead of rejecting startups permanently:

	Lead
	↓
	Meeting
	↓
	Due Diligence
	↓
	Watchlist
	↓
	Invest
	OR
	Reject


# ----------------------------------------------------------
# Suggested Technology Stack
#-----------------------------------------------------------
| Layer          | Technology                               |
| -------------- | ---------------------------------------- |
| Frontend       | Next.js 15 + React + TypeScript          |
| Backend        | FastAPI + Python 3.12                    |
| ORM            | SQLAlchemy 2                             |
| Database       | PostgreSQL 17                            |
| Migrations     | Alembic                                  |
| Validation     | Pydantic v2                              |
| Cache          | Redis                                    |
| UI             | Tailwind CSS + shadcn/ui                 |
| Charts         | Apache ECharts                           |
| Authentication | JWT (expand later)                       |
| Storage        | Local filesystem initially (MinIO later) |
| Containers     | Docker Compose                           |

# Documentation Structure

docs/
	001-vision.md
	002-architecture.md
	003-database.md
	004-api.md
	005-ui.md
	006-roadmap.md
	007-coding-standards.md
	008-deployment.md
