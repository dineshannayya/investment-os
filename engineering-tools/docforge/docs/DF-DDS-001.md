DocForge Detailed Design Specification (DDS)

Document ID: DF-DDS-001
Version: 0.1.0
Status: Draft

1. Module Hierarchy
DocForge

├── CLI
├── Application
│   ├── ScanService
│   ├── PlanService
│   ├── PipelineService
│   └── ReportService
│
├── Domain
│   ├── Document
│   ├── Asset
│   ├── Metadata
│   ├── Diagnostics
│   └── PipelineContext
│
├── Ports
│   ├── Converter
│   ├── Validator
│   ├── Publisher
│   └── MetadataProvider
│
├── Adapters
│   ├── Mammoth
│   ├── MkDocs
│   └── Filesystem
│
└── Infrastructure
2. Core Domain Objects

Instead of dozens of loosely related classes, we'll have six primary domain objects.

Document

Represents one logical document.

Responsibilities:

source path
output path
markdown
metadata
images
diagnostics
processing status
Asset

Represents embedded resources.

Examples:

images
attachments
diagrams
Metadata

Represents structured information.

Examples:

title
author
version
tags
language
Diagnostics

Collects:

warnings
errors
informational messages

Every stage contributes here.

ProcessingContext

Shared execution context.

Contains:

configuration
logger
execution options
statistics
ConversionPlan

Represents the complete batch.

Contains

documents
skipped
failed
summary
3. Application Services

These coordinate work but contain very little business logic.

ScanService

Responsibilities

recursive scanning
ignore rules
supported formats

Output

List<Document>
PlanService

Responsibilities

compare source/output
incremental detection
dry-run support

Output

ConversionPlan
PipelineService

Executes

Converter

↓

Normalizer

↓

Validator

↓

Metadata

↓

Publisher
ReportService

Produces

Console

JSON

Markdown

HTML (future)
4. Plugin Contracts

Every plugin follows the same lifecycle.

initialize()

↓

process(document)

↓

finalize()

This keeps plugins consistent and testable.

5. Pipeline Contract

Every processing stage follows one interface:

Input

↓

Document

↓

Process

↓

Document

↓

Output

No stage directly modifies another stage.

6. Error Model

Three categories:

Recoverable

Continue.

Example

Broken image
Document Failure

Skip current document.

Example

Corrupted DOCX
Fatal

Stop.

Example

Invalid configuration
7. Logging Strategy

Every message contains

Timestamp

Level

Module

Document

Message

Example

INFO scanner README.docx discovered

INFO converter README converted

WARNING validator missing heading

ERROR converter corrupted document
8. Testing Strategy

Every module gets

Unit Tests

↓

Integration Tests

↓

Regression Tests

No module is merged without tests.

9. Performance Targets

Initial goals

Metric	Target
Startup	<1 second
Scan 1000 docs	<3 seconds (excluding conversion)
Memory	<500 MB for typical repositories
Batch Processing	Continue after document failures
Incremental Build	Reprocess only changed documents

These are aspirational targets that we'll validate with benchmarks as the project matures.
