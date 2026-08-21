"""Real startup data loader for Investment OS.

C.6.4.1
--------
Load one real startup, its founders, and source documents into the
application database using the existing application-service contracts.

The loader is resume-safe/idempotent:

* Existing startup is reused.
* Existing founders are matched by normalized full name.
* Missing founders are created.
* Existing documents are matched by SHA-256 within the startup.
* Missing documents are uploaded.
* Existing records are not silently overwritten.

This script intentionally does NOT run startup analysis or Qwen.

Input layout
------------
<startup-dir>/
├── startup.yaml
├── founders.yaml
├── documents.yaml              # optional
└── documents/
    ├── investor_brief.txt
    └── financial_model.txt

Examples
--------
docker compose exec -T backend \
    python -u -m scripts.startup_analysis_real_startup \
    --startup-dir data/real_startups/restomart \
    --dry-run

docker compose exec -T backend \
    python -u -m scripts.startup_analysis_real_startup \
    --startup-dir data/real_startups/restomart
"""

from __future__ import annotations

import argparse
import hashlib
import mimetypes
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy.orm import Session

from app.core.config.settings import settings
from app.core.database.session import create_session
from app.models.document import Document
from app.models.enums import DocumentType
from app.models.founder import Founder
from app.models.startup import Startup
from app.repositories.document import DocumentRepository
from app.repositories.founder import FounderRepository
from app.repositories.startup import StartupRepository
from app.schemas.founder import FounderCreate
from app.schemas.startup import StartupCreate
from app.services.document import DocumentService
from app.services.founder import FounderService
from app.services.startup import StartupService
from app.services.upload import UploadRequest, UploadService
from app.storage.local import LocalStorageProvider
from app.storage.service import StorageService


STARTUP_FILE = "startup.yaml"
FOUNDERS_FILE = "founders.yaml"
DOCUMENTS_FILE = "documents.yaml"
DOCUMENTS_DIR = "documents"


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    """Validated source document definition."""

    path: Path
    title: str
    document_type: DocumentType
    description: str | None


@dataclass(frozen=True, slots=True)
class LoadResult:
    """Result of a startup reconciliation/load operation."""

    startup: Startup
    founders: tuple[Founder, ...]
    documents: tuple[Document, ...]

    startup_created: bool
    founders_created: int
    founders_reused: int
    documents_created: int
    documents_reused: int


# =============================================================================
# Input / YAML helpers
# =============================================================================


def _enum_from_value(
    enum_cls: type[Enum],
    value: Any,
    *,
    field: str,
) -> Enum:
    """Resolve an enum from either its value or enum name."""

    if isinstance(value, enum_cls):
        return value

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field} must be a non-empty string."
        )

    raw = value.strip()

    try:
        return enum_cls(raw)
    except ValueError:
        try:
            return enum_cls[raw.upper()]
        except KeyError as exc:
            choices = ", ".join(
                str(member.value)
                for member in enum_cls
            )
            raise ValueError(
                f"Invalid {field} '{value}'. "
                f"Expected one of: {choices}"
            ) from exc


def _load_yaml(path: Path) -> Any:
    """Load one YAML file."""

    if not path.is_file():
        raise ValueError(
            f"Required file not found: {path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML in {path}: {exc}"
        ) from exc

    return {} if data is None else data


def _load_startup(
    path: Path,
) -> StartupCreate:
    """Load and validate startup.yaml."""

    data = _load_yaml(path)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path} must contain a YAML mapping."
        )

    data = dict(data)

    if "stage" in data:
        from app.models.enums import StartupStage

        data["stage"] = _enum_from_value(
            StartupStage,
            data["stage"],
            field="startup.stage",
        )

    if "status" in data:
        from app.models.enums import StartupStatus

        data["status"] = _enum_from_value(
            StartupStatus,
            data["status"],
            field="startup.status",
        )

    return StartupCreate(**data)


def _load_founders(
    path: Path,
) -> list[dict[str, Any]]:
    """Load founder definitions from founders.yaml."""

    data = _load_yaml(path)

    if isinstance(data, dict):
        data = data.get("founders")

    if not isinstance(data, list):
        raise ValueError(
            f"{path} must contain a list or a 'founders' list."
        )

    founders: list[dict[str, Any]] = []

    for index, item in enumerate(
        data,
        start=1,
    ):
        if not isinstance(item, dict):
            raise ValueError(
                f"{path}: founder #{index} must be a mapping."
            )

        normalized = dict(item)

        if not normalized.get("full_name"):
            raise ValueError(
                f"{path}: founder #{index} requires full_name."
            )

        if not normalized.get("designation"):
            raise ValueError(
                f"{path}: founder #{index} requires designation."
            )

        founders.append(normalized)

    return founders


def _normalize_document_type(
    value: Any,
) -> DocumentType:
    """Resolve document type, defaulting to OTHER."""

    if value is None:
        return DocumentType.OTHER

    result = _enum_from_value(
        DocumentType,
        value,
        field="document.document_type",
    )

    return result  # type: ignore[return-value]


def _infer_document_type(
    path: Path,
) -> DocumentType:
    """Infer document type from common filename conventions."""

    name = (
        path.stem
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    rules = (
        (("pitch", "deck"), DocumentType.PITCH_DECK),
        (("financial", "model"), DocumentType.FINANCIAL_MODEL),
        (("financials",), DocumentType.FINANCIAL_MODEL),
        (("business", "plan"), DocumentType.BUSINESS_PLAN),
        (("term", "sheet"), DocumentType.TERM_SHEET),
        (("sha",), DocumentType.SHA),
        (("cap", "table"), DocumentType.CAP_TABLE),
        (("bank", "statement"), DocumentType.BANK_STATEMENT),
        (("gst",), DocumentType.GST),
        (("roc",), DocumentType.ROC),
        (("patent",), DocumentType.PATENT),
        (("demo",), DocumentType.PRODUCT_DEMO),
    )

    for keywords, document_type in rules:
        if all(keyword in name for keyword in keywords):
            return document_type

    return DocumentType.OTHER


def _load_document_specs(
    startup_dir: Path,
) -> tuple[DocumentSpec, ...]:
    """Discover documents and optional metadata."""

    documents_dir = startup_dir / DOCUMENTS_DIR

    if not documents_dir.is_dir():
        raise ValueError(
            f"Required documents directory not found: "
            f"{documents_dir}"
        )

    metadata: dict[str, dict[str, Any]] = {}

    metadata_path = startup_dir / DOCUMENTS_FILE

    if metadata_path.exists():
        raw = _load_yaml(metadata_path)

        if isinstance(raw, dict):
            raw = raw.get("documents", raw)

        if not isinstance(raw, list):
            raise ValueError(
                f"{metadata_path} must contain a list or "
                f"a 'documents' list."
            )

        for index, item in enumerate(
            raw,
            start=1,
        ):
            if not isinstance(item, dict):
                raise ValueError(
                    f"{metadata_path}: document #{index} "
                    f"must be a mapping."
                )

            filename = item.get("filename")

            if (
                not isinstance(filename, str)
                or not filename.strip()
            ):
                raise ValueError(
                    f"{metadata_path}: document #{index} "
                    f"requires filename."
                )

            metadata[filename] = dict(item)

    files = sorted(
        path
        for path in documents_dir.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
    )

    if not files:
        raise ValueError(
            f"No documents found under {documents_dir}"
        )

    specs: list[DocumentSpec] = []

    for path in files:
        item = metadata.get(path.name, {})

        title = (
            item.get("title")
            or path.stem.replace("_", " ").title()
        )

        document_type = _normalize_document_type(
            item.get("document_type")
            if "document_type" in item
            else _infer_document_type(path)
        )

        description = item.get("description")

        if description is not None and not isinstance(
            description,
            str,
        ):
            raise ValueError(
                f"{DOCUMENTS_FILE}: description for "
                f"{path.name} must be a string."
            )

        specs.append(
            DocumentSpec(
                path=path,
                title=str(title),
                document_type=document_type,
                description=description,
            )
        )

    unknown = (
        set(metadata)
        - {spec.path.name for spec in specs}
    )

    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(
            f"{metadata_path}: metadata references "
            f"missing documents: {names}"
        )

    return tuple(specs)


def validate_input(
    startup_dir: Path,
) -> tuple[
    StartupCreate,
    list[dict[str, Any]],
    tuple[DocumentSpec, ...],
]:
    """Validate all source files without touching DB/storage."""

    startup = _load_startup(
        startup_dir / STARTUP_FILE
    )

    founders = _load_founders(
        startup_dir / FOUNDERS_FILE
    )

    documents = _load_document_specs(
        startup_dir
    )

    return (
        startup,
        founders,
        documents,
    )


# =============================================================================
# Reconciliation helpers
# =============================================================================


def _create_storage_service() -> StorageService:
    """Create the production storage service."""

    return StorageService(
        LocalStorageProvider(
            settings.storage_root,
        )
    )


def _normalize_name(
    value: str,
) -> str:
    """Normalize a founder name for identity matching."""

    return " ".join(
        value.strip().lower().split()
    )


def _sha256(
    data: bytes,
) -> str:
    """Calculate SHA-256 for document contents."""

    return hashlib.sha256(data).hexdigest()


def _get_or_create_startup(
    session: Session,
    payload: StartupCreate,
) -> tuple[Startup, bool]:
    """Reuse an existing startup or create a new one."""

    repository = StartupRepository(session)

    existing = repository.get_by_name(
        payload.name
    )

    if existing is not None:
        return existing, False

    startup = StartupService(
        session
    ).create_startup(payload)

    return startup, True


def _load_existing_founders(
    session: Session,
    startup_id: UUID,
) -> dict[str, Founder]:
    """Load existing founders indexed by normalized name."""

    founders = FounderRepository(
        session
    ).list_by_startup(startup_id)

    result: dict[str, Founder] = {}

    for founder in founders:
        key = _normalize_name(
            founder.full_name
        )

        if key in result:
            raise ValueError(
                "Duplicate founder names detected in database "
                f"for startup {startup_id}: "
                f"{founder.full_name}"
            )

        result[key] = founder

    return result


def _reconcile_founders(
    session: Session,
    startup_id: UUID,
    founder_data: list[dict[str, Any]],
) -> tuple[
    tuple[Founder, ...],
    int,
    int,
]:
    """Reuse existing founders and create missing founders."""

    existing = _load_existing_founders(
        session,
        startup_id,
    )

    service = FounderService(session)

    resolved: list[Founder] = []
    created_count = 0
    reused_count = 0

    seen_input: set[str] = set()

    for item in founder_data:
        full_name = str(
            item["full_name"]
        )

        key = _normalize_name(full_name)

        if key in seen_input:
            raise ValueError(
                f"Duplicate founder in input: {full_name}"
            )

        seen_input.add(key)

        founder = existing.get(key)

        if founder is not None:
            resolved.append(founder)
            reused_count += 1

            print(
                f"  REUSED : {founder.full_name} "
                f"({founder.designation})"
            )
            continue

        payload = FounderCreate(
            startup_id=startup_id,
            **item,
        )

        founder = service.create_founder(
            payload
        )

        resolved.append(founder)
        existing[key] = founder
        created_count += 1

        print(
            f"  CREATED: {founder.full_name} "
            f"({founder.designation})"
        )

    return (
        tuple(resolved),
        created_count,
        reused_count,
    )


def _load_existing_documents(
    session: Session,
    startup_id: UUID,
) -> dict[str, Document]:
    """Load existing startup documents indexed by SHA-256."""

    documents = DocumentRepository(
        session
    ).list_by_startup(startup_id)

    result: dict[str, Document] = {}

    for document in documents:
        if not document.file_hash:
            continue

        if document.file_hash in result:
            raise ValueError(
                "Duplicate document hash detected in database "
                f"for startup {startup_id}: "
                f"{document.file_hash}"
            )

        result[document.file_hash] = document

    return result


def _upload_documents(
    session: Session,
    storage: StorageService,
    startup_id: UUID,
    specs: tuple[DocumentSpec, ...],
) -> tuple[
    tuple[Document, ...],
    int,
    int,
]:
    """Reuse existing documents or upload missing documents."""

    existing = _load_existing_documents(
        session,
        startup_id,
    )

    service = UploadService(
        storage=storage,
        documents=DocumentService(session),
    )

    resolved: list[Document] = []
    created_count = 0
    reused_count = 0

    seen_input_hashes: set[str] = set()

    for spec in specs:
        data = spec.path.read_bytes()
        file_hash = _sha256(data)

        if file_hash in seen_input_hashes:
            raise ValueError(
                "Duplicate document content in input: "
                f"{spec.path.name}"
            )

        seen_input_hashes.add(file_hash)

        document = existing.get(file_hash)

        if document is not None:
            resolved.append(document)
            reused_count += 1

            print(
                f"  REUSED : {document.filename} "
                f"[sha256={document.file_hash}]"
            )
            continue

        mime_type = (
            mimetypes.guess_type(
                spec.path.name
            )[0]
            or "application/octet-stream"
        )

        document = service.upload(
            UploadRequest(
                startup_id=startup_id,
                document_type=spec.document_type,
                title=spec.title,
                filename=spec.path.name,
                mime_type=mime_type,
                description=spec.description,
                data=data,
            )
        )

        session.refresh(document)

        resolved.append(document)
        existing[file_hash] = document
        created_count += 1

        print(
            f"  CREATED: {document.filename} "
            f"[sha256={document.file_hash}]"
        )

    return (
        tuple(resolved),
        created_count,
        reused_count,
    )


# =============================================================================
# Output
# =============================================================================


def _print_dry_run(
    startup: StartupCreate,
    founders: list[dict[str, Any]],
    documents: tuple[DocumentSpec, ...],
) -> None:
    """Print validated input without DB/storage changes."""

    print()
    print("=" * 80)
    print("REAL STARTUP LOADER — DRY RUN")
    print("=" * 80)

    print()
    print("STARTUP")
    print("-" * 80)
    print(f"Name           : {startup.name}")
    print(f"Stage          : {startup.stage.value}")
    print(f"Sector         : {startup.sector}")
    print(f"Industry       : {startup.industry}")
    print(f"Founded year   : {startup.founded_year}")
    print(f"Website        : {startup.website}")
    print(f"Headquarters   : {startup.headquarters}")

    print()
    print("FOUNDERS")
    print("-" * 80)

    for index, founder in enumerate(
        founders,
        start=1,
    ):
        print(
            f"{index}. {founder.get('full_name')} "
            f"({founder.get('designation')})"
        )

    print()
    print("DOCUMENTS")
    print("-" * 80)

    for spec in documents:
        print(
            f"{spec.path.name} | "
            f"{spec.document_type.value} | "
            f"{spec.title}"
        )

    print()
    print(
        "DRY RUN: no database or storage changes made."
    )


def _print_result(
    result: LoadResult,
) -> None:
    """Print persisted startup, founders, and documents."""

    print()
    print("=" * 80)
    print("REAL STARTUP LOADER: PASS")
    print("=" * 80)

    print()
    print("STARTUP")
    print("-" * 80)
    print(f"Startup ID     : {result.startup.id}")
    print(f"Name           : {result.startup.name}")
    print(f"Stage          : {result.startup.stage.value}")
    print(f"Status         : {result.startup.status.value}")
    print(
        "Persistence    : "
        f"{'CREATED' if result.startup_created else 'REUSED'}"
    )

    print()
    print("FOUNDERS")
    print("-" * 80)

    for founder in result.founders:
        print(
            f"{founder.id} | "
            f"{founder.full_name} | "
            f"{founder.designation}"
        )

    print()
    print("DOCUMENTS")
    print("-" * 80)

    for document in result.documents:
        print(
            f"{document.id} | "
            f"{document.document_type.value} | "
            f"{document.filename} | "
            f"{document.status.value}"
        )
        print(
            f"  Storage path : {document.storage_path}"
        )
        print(
            f"  SHA-256      : {document.file_hash}"
        )

    print()
    print("INGESTION SUMMARY")
    print("-" * 80)
    print(
        "Startup persisted : "
        f"{'CREATED' if result.startup_created else 'REUSED'}"
    )
    print(
        f"Founders created  : {result.founders_created}"
    )
    print(
        f"Founders reused   : {result.founders_reused}"
    )
    print(
        f"Documents created : {result.documents_created}"
    )
    print(
        f"Documents reused  : {result.documents_reused}"
    )


# =============================================================================
# CLI
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Load a real startup, founders, and documents "
            "into the Investment OS database."
        )
    )

    parser.add_argument(
        "--startup-dir",
        type=Path,
        required=True,
        help=(
            "Directory containing startup.yaml, "
            "founders.yaml, and documents/."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate and display input without "
            "changing DB or storage."
        ),
    )

    return parser


def main() -> int:
    """CLI entry point."""

    parser = _build_parser()
    args = parser.parse_args()

    startup_dir = (
        args.startup_dir
        .expanduser()
        .resolve()
    )

    session: Session | None = None

    try:
        if not startup_dir.is_dir():
            raise ValueError(
                f"Startup directory not found: "
                f"{startup_dir}"
            )

        (
            startup_payload,
            founder_data,
            document_specs,
        ) = validate_input(startup_dir)

        if args.dry_run:
            _print_dry_run(
                startup_payload,
                founder_data,
                document_specs,
            )
            return 0

        print()
        print("=" * 80)
        print("REAL STARTUP LOADER")
        print("=" * 80)
        print(
            f"Startup directory : {startup_dir}"
        )
        print(
            f"Startup           : {startup_payload.name}"
        )
        print(
            f"Founders          : {len(founder_data)}"
        )
        print(
            f"Documents         : {len(document_specs)}"
        )

        session = create_session()

        print()
        print("Resolving startup...")

        startup, startup_created = (
            _get_or_create_startup(
                session,
                startup_payload,
            )
        )

        print(
            f"Startup ID        : {startup.id}"
        )
        print(
            "Startup status    : "
            f"{'CREATED' if startup_created else 'REUSED'}"
        )

        print()
        print("Reconciling founders...")

        (
            founders,
            founders_created,
            founders_reused,
        ) = _reconcile_founders(
            session,
            startup.id,
            founder_data,
        )

        print(
            f"Founders created  : {founders_created}"
        )
        print(
            f"Founders reused   : {founders_reused}"
        )

        print()
        print("Reconciling documents...")

        storage = _create_storage_service()

        (
            documents,
            documents_created,
            documents_reused,
        ) = _upload_documents(
            session,
            storage,
            startup.id,
            document_specs,
        )

        print(
            f"Documents created : {documents_created}"
        )
        print(
            f"Documents reused  : {documents_reused}"
        )

        result = LoadResult(
            startup=startup,
            founders=founders,
            documents=documents,
            startup_created=startup_created,
            founders_created=founders_created,
            founders_reused=founders_reused,
            documents_created=documents_created,
            documents_reused=documents_reused,
        )

        _print_result(result)

        return 0

    except Exception as exc:
        if session is not None:
            session.rollback()

        print()
        print("=" * 80)
        print("REAL STARTUP LOADER: FAILED")
        print("=" * 80)
        print(
            f"Exception type : {type(exc).__name__}"
        )
        print(
            f"Exception      : {exc}"
        )
        return 1

    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
