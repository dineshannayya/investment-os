# Changelog

All notable changes to **Investment OS** are documented in this file.

This project follows:

* [Keep a Changelog](https://keepachangelog.com/)
* Semantic Versioning (SemVer)

The purpose of this document is to record **released functionality only**.

Project planning, sprint execution, engineering reviews, and milestone details are maintained in the project governance documentation.

---

# [Unreleased]

## Added

### API Infrastructure

- Standard API response envelope (`ApiResponse`)
- Response metadata model
- Standard error model
- Pagination metadata model
- Response factory utilities
- Centralized application exception hierarchy
- Global exception handling framework
- Standard HTTP status code definitions
- Centralized error code definitions
- API configuration module

### Testing

- Comprehensive schema unit tests
- Response factory unit tests
- API integration tests
- Middleware integration tests
- Expanded model test coverage
- Test fixtures and database infrastructure

## Changed

- Standardized all API responses through a common response factory.
- Centralized configuration into dedicated configuration modules.
- Adopted Python 3.12 modern typing syntax where applicable.
- Standardized API versioning using a centralized API prefix.
- Improved middleware registration and application startup.

## Fixed

- Request validation handling.
- Response serialization consistency.
- Middleware registration issues.
- API routing consistency.
- Test infrastructure and database isolation.

---

# [0.1.0] - 2026-07-25

## Added

### Backend Framework

* Initial FastAPI application framework
* Configuration management
* Application lifecycle management
* Structured logging

### Middleware

* Request ID middleware
* Request timing middleware
* Request logging middleware
* Middleware registration

### API

* Health endpoint
* Readiness endpoint
* Version endpoint
* OpenAPI documentation

### Database

* SQLAlchemy foundation
* Database engine management
* Session management
* Dependency injection

### Domain Models

* Startup
* Founder
* Investment
* Opportunity
* Document

### Development

* Docker development environment
* Makefile automation
* Ruff linting
* Code formatting
* Static type checking
* Pytest test framework
* Coverage reporting

### Documentation

* Project governance documentation
* Architecture documentation
* Development standards
* Engineering process documentation

## Changed

* Adopted layered application architecture.
* Standardized project structure.
* Established governance-driven development workflow.

## Fixed

* Initial framework stabilization during project setup.

---

# Release History

| Version | Release Date |
| ------- | ------------ |
| 0.1.0   | 2026-07-25   |

