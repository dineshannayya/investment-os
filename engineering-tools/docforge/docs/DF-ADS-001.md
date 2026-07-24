DocForge Architecture Design Specification (ADS)

Document ID: DF-ADS-001
Version: 0.1.0
Status: Draft

1. Architectural Goals

The architecture shall:

Be modular and extensible.
Support multiple document formats without core changes.
Process large document repositories efficiently.
Be deterministic and reproducible.
Isolate third-party libraries from business logic.
Support AI-ready document pipelines.
Enable future distributed execution if needed.
2. Architectural Principles

We will adopt the following principles:

Domain-Centric Design – The document is the core domain object.
Ports and Adapters (Hexagonal Architecture) – External libraries (e.g., Mammoth, MkDocs) are adapters around a stable core.
Pipeline Processing – Each stage performs one transformation.
Plugin-Based Extensibility – New formats and processors are added as plugins.
Configuration-Driven Behavior – Pipeline behavior is controlled through configuration.
3. High-Level Architecture
                   User / CLI / API
                          │
                          ▼
                Application Orchestrator
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
     Scanner          Planner          Pipeline Runner
                                            │
                                            ▼
              ┌──────────────────────────────────────┐
              │         Processing Pipeline           │
              ├──────────────────────────────────────┤
              │ Converter                            │
              │ Normalizer                           │
              │ Validator                            │
              │ Metadata Enricher                    │
              │ Publisher                            │
              └──────────────────────────────────────┘
                                            │
                                            ▼
                                   Output Repository
4. Core Domain Model

Everything revolves around a single Document object.

Document
├── Source
├── Metadata
├── Content
├── Assets
├── Diagnostics
├── Processing State
└── Output

Every pipeline stage receives a Document and returns an updated Document.

This keeps interfaces simple and consistent.

5. Processing Pipeline

Each document passes through the same ordered stages.

Discovery
    ↓
Planning
    ↓
Conversion
    ↓
Normalization
    ↓
Validation
    ↓
Metadata
    ↓
Publishing

Stages may be enabled or disabled via configuration.

6. Module Responsibilities
Module	Responsibility
Scanner	Discover supported documents
Planner	Build execution plan
Converter	Format-specific conversion
Markdown	Normalize Markdown
Validator	Quality checks
Metadata	Generate and enrich metadata
Publisher	Export documentation
AI	Prepare AI-ready outputs
Reporting	Summaries and metrics

Each module has a single responsibility.

7. Plugin Architecture

Every extensible capability is implemented as a plugin.

Plugins
├── Converters
├── Validators
├── Publishers
├── Metadata Providers
└── AI Processors

Each plugin implements a defined interface, allowing new capabilities to be added without modifying the core pipeline.

8. Repository Structure
docforge/
├── docs/
├── specs/
├── adr/
├── configs/
├── src/
│   └── docforge/
│       ├── application/
│       ├── domain/
│       ├── ports/
│       ├── adapters/
│       ├── plugins/
│       ├── infrastructure/
│       └── cli/
├── tests/
├── samples/
└── benchmarks/
Why this structure?

This is a refinement of our earlier layout. Instead of organizing by technical function (scanner/, converter/, etc.), it reflects architectural boundaries:

domain/ – Core business objects (Document, metadata, diagnostics).
ports/ – Interfaces that define what the core needs (converter, validator, publisher contracts).
adapters/ – Implementations using libraries such as Mammoth.
application/ – Workflow orchestration and pipeline execution.
plugins/ – Optional extensions discovered at runtime.
infrastructure/ – Logging, configuration, filesystem, reporting.

This separation makes dependencies explicit and helps keep the domain independent of external libraries.

9. Dependency Rules

Allowed dependencies:

CLI
    ↓
Application
    ↓
Ports
    ↓
Domain

Adapters ─────► Ports

Infrastructure ─► Application
Infrastructure ─► Adapters

Forbidden dependencies:

Domain → Adapters
Domain → Infrastructure
Ports → Adapters
Application → Specific third-party libraries

These rules preserve the independence of the core domain.

10. Error Handling

Errors are classified as:

Fatal – Stop the application (e.g., invalid configuration).
Document-level – Skip one document and continue.
Warning – Record and continue processing.

All diagnostics are attached to the Document object and included in the final report.

11. Observability

Every pipeline stage reports:

Documents processed
Success/failure counts
Execution time
Warnings
Errors

This information is available in both logs and summary reports.

12. Future Extension Points

The architecture is intentionally designed to support future capabilities without changing the core:

Parallel document processing
Remote storage backends
Cloud execution
REST API
Web UI
AI summarization
Vector database integration
Workflow orchestration
