# Changelog

All notable changes to **Investment OS** are documented in this file.

This project follows:

* [Semantic Versioning (SemVer)](https://semver.org/)
* The principles of **Keep a Changelog**

---

# Release Lifecycle

```
Development
      │
      ▼
Feature Complete
      │
      ▼
Testing
      │
      ▼
Documentation
      │
      ▼
Release Candidate
      │
      ▼
Production Release
```

---

# Changelog Categories

Each release should be organized using the following sections:

* Added
* Changed
* Improved
* Fixed
* Deprecated
* Removed
* Security
* Performance
* Documentation
* Testing
* Known Issues
* Breaking Changes (if applicable)

Only include sections that contain changes for that release.

---

# [Unreleased]

## Planned

### Added

* API Infrastructure
* Exception framework
* JWT authentication
* Pagination
* Filtering
* Response envelope

---

# [0.1.0] - 2026-07-25

## Release Name

**Backend Foundation**

---

## Summary

This release establishes the initial backend foundation for Investment OS.

The focus of this milestone was to create a maintainable, testable, and production-ready FastAPI backend that serves as the base for future investment workflows and AI capabilities.

---

## Added

### Backend Framework

* FastAPI application bootstrap
* Application lifespan management
* Modular router registration

### Configuration

* Environment-based configuration
* Centralized settings management
* Configuration validation
* Constants package

### Middleware

* Request ID middleware
* Request timing middleware
* Request logging middleware
* Request context middleware

### API

* Health endpoint
* Readiness endpoint
* Version endpoint

### Testing

* Automated unit testing framework
* Middleware tests
* Configuration tests
* API endpoint tests
* Lifespan tests

### Development

* Docker support
* Makefile automation
* Ruff integration
* Black formatting

---

## Changed

* Adopted modular package structure.
* Standardized configuration loading.
* Unified logging strategy across the application.

---

## Improved

* Project maintainability through clear package organization.
* Developer onboarding with consistent tooling.
* Code readability using shared conventions.

---

## Fixed

* Test configuration issues.
* Middleware initialization order.
* Configuration loading edge cases.
* Request timing implementation refinements.

---

## Documentation

Added:

* Project README
* Backend setup guide
* Development workflow
* Coding standards
* Initial architecture documentation

---

## Testing

| Metric     |  Value |
| ---------- | -----: |
| Unit Tests |     44 |
| Coverage   |    95% |
| Lint       | Passed |
| Formatter  | Passed |

---

## Known Issues

* Starlette `TestClient` deprecation warning caused by upstream dependency compatibility.
* Planned for future dependency upgrade.

---

## Breaking Changes

None.

---

# Upcoming Release

## v0.2.0

Planned capabilities:

### Added

* Exception framework
* API response envelope
* JWT authentication
* Pagination
* Filtering
* OpenAPI enhancements

---

# Changelog Guidelines

## What SHOULD be included

* New functionality
* User-visible improvements
* Architectural improvements
* Performance improvements
* Security updates
* Bug fixes
* Breaking changes
* Migration notes

---

## What SHOULD NOT be included

* Individual commits
* Refactoring without behavioral impact
* Variable renames
* Formatting-only changes
* Minor documentation wording updates
* Temporary debugging changes

---

# Versioning Policy

The project follows Semantic Versioning.

```
MAJOR.MINOR.PATCH
```

Examples:

| Version | Meaning                  |
| ------- | ------------------------ |
| 0.1.0   | Backend Foundation       |
| 0.2.0   | API Infrastructure       |
| 0.3.0   | Database Platform        |
| 0.4.0   | Investment Domain        |
| 0.5.0   | AI Intelligence          |
| 1.0.0   | First Production Release |

---

# Release Checklist

Before publishing a release:

* All planned features completed
* Tests passing
* Coverage target achieved
* Documentation updated
* Changelog updated
* ADRs updated (if required)
* Milestones updated
* Roadmap updated
* Git tag created

---

# Release History

| Version | Status   | Date       |
| ------- | -------- | ---------- |
| 0.1.0   | Released | 2026-07-25 |
| 0.2.0   | Planned  | TBD        |
| 0.3.0   | Planned  | TBD        |
| 0.4.0   | Planned  | TBD        |
| 0.5.0   | Planned  | TBD        |
| 1.0.0   | Planned  | TBD        |

