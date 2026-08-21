"""Tests for the C.6.4.1 real-startup loader.

The tests focus on loader orchestration/reconciliation:

* input identity normalization
* startup create/reuse
* founder create/reuse
* document create/reuse
* duplicate input detection

Repository and service implementations are tested separately.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.models.enums import DocumentType
from scripts.startup_analysis_real_startup import (
    DocumentSpec,
    _get_or_create_startup,
    _load_existing_documents,
    _load_existing_founders,
    _normalize_name,
    _reconcile_founders,
    _sha256,
    _upload_documents,
)


# =============================================================================
# Name / hash helpers
# =============================================================================


def test_normalize_name_collapses_whitespace_and_case():
    assert (
        _normalize_name(
            "  Rajendran   Kathiravan  "
        )
        == "rajendran kathiravan"
    )


def test_sha256_is_deterministic():
    data = b"RestoMart financial information"

    assert _sha256(data) == _sha256(data)


def test_sha256_changes_when_content_changes():
    assert _sha256(b"content-a") != _sha256(
        b"content-b"
    )


# =============================================================================
# Startup reconciliation
# =============================================================================


def test_get_or_create_startup_reuses_existing_startup(
    monkeypatch,
):
    startup = SimpleNamespace(
        id=uuid4(),
        name="RestoMart",
    )

    repository = Mock()
    repository.get_by_name.return_value = startup

    startup_service = Mock()

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.StartupRepository",
        Mock(return_value=repository),
    )
    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.StartupService",
        Mock(return_value=startup_service),
    )

    payload = SimpleNamespace(
        name="RestoMart",
    )

    result, created = _get_or_create_startup(
        Mock(),
        payload,
    )

    assert result is startup
    assert created is False

    repository.get_by_name.assert_called_once_with(
        "RestoMart"
    )
    startup_service.create_startup.assert_not_called()


def test_get_or_create_startup_creates_missing_startup(
    monkeypatch,
):
    created_startup = SimpleNamespace(
        id=uuid4(),
        name="RestoMart",
    )

    repository = Mock()
    repository.get_by_name.return_value = None

    startup_service = Mock()
    startup_service.create_startup.return_value = (
        created_startup
    )

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.StartupRepository",
        Mock(return_value=repository),
    )
    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.StartupService",
        Mock(return_value=startup_service),
    )

    payload = SimpleNamespace(
        name="RestoMart",
    )

    result, created = _get_or_create_startup(
        Mock(),
        payload,
    )

    assert result is created_startup
    assert created is True

    repository.get_by_name.assert_called_once_with(
        "RestoMart"
    )
    startup_service.create_startup.assert_called_once_with(
        payload
    )


# =============================================================================
# Founder reconciliation
# =============================================================================


def test_load_existing_founders_indexes_by_normalized_name(
    monkeypatch,
):
    founder = SimpleNamespace(
        id=uuid4(),
        full_name="Rajendran Kathiravan",
        designation="CBO",
    )

    repository = Mock()
    repository.list_by_startup.return_value = [
        founder
    ]

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.FounderRepository",
        Mock(return_value=repository),
    )

    result = _load_existing_founders(
        Mock(),
        uuid4(),
    )

    assert result["rajendran kathiravan"] is founder


def test_reconcile_founders_reuses_existing_and_creates_missing(
    monkeypatch,
):
    startup_id = uuid4()

    existing_founder_1 = SimpleNamespace(
        id=uuid4(),
        full_name="Chandra Mohan R",
        designation="CEO",
    )

    existing_founder_2 = SimpleNamespace(
        id=uuid4(),
        full_name="Tharun Kumar Rajkumar",
        designation="COO",
    )

    new_founder = SimpleNamespace(
        id=uuid4(),
        full_name="Rajendran Kathiravan",
        designation="CBO",
    )

    repository = Mock()
    repository.list_by_startup.return_value = [
        existing_founder_1,
        existing_founder_2,
    ]

    service = Mock()
    service.create_founder.return_value = (
        new_founder
    )

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.FounderRepository",
        Mock(return_value=repository),
    )
    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.FounderService",
        Mock(return_value=service),
    )

    founders, created, reused = (
        _reconcile_founders(
            Mock(),
            startup_id,
            [
                {
                    "full_name": "Chandra Mohan R",
                    "designation": "CEO",
                },
                {
                    "full_name": " Tharun   Kumar Rajkumar ",
                    "designation": "COO",
                },
                {
                    "full_name": "Rajendran Kathiravan",
                    "designation": "CBO",
                },
            ],
        )
    )

    assert founders == (
        existing_founder_1,
        existing_founder_2,
        new_founder,
    )

    assert created == 1
    assert reused == 2

    service.create_founder.assert_called_once()


def test_reconcile_founders_rejects_duplicate_input_names(
    monkeypatch,
):
    repository = Mock()
    repository.list_by_startup.return_value = []

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.FounderRepository",
        Mock(return_value=repository),
    )

    with pytest.raises(
        ValueError,
        match="Duplicate founder in input",
    ):
        _reconcile_founders(
            Mock(),
            uuid4(),
            [
                {
                    "full_name": "Rajendran Kathiravan",
                    "designation": "CBO",
                },
                {
                    "full_name": " rajendran   kathiravan ",
                    "designation": "CBO",
                },
            ],
        )


def test_reconcile_founders_does_not_create_duplicate_for_name_case_difference(
    monkeypatch,
):
    existing = SimpleNamespace(
        id=uuid4(),
        full_name="Rajendran Kathiravan",
        designation="CBO",
    )

    repository = Mock()
    repository.list_by_startup.return_value = [
        existing
    ]

    service = Mock()

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.FounderRepository",
        Mock(return_value=repository),
    )
    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.FounderService",
        Mock(return_value=service),
    )

    founders, created, reused = (
        _reconcile_founders(
            Mock(),
            uuid4(),
            [
                {
                    "full_name": "RAJENDRAN KATHIRAVAN",
                    "designation": "CBO",
                }
            ],
        )
    )

    assert founders == (existing,)
    assert created == 0
    assert reused == 1

    service.create_founder.assert_not_called()


# =============================================================================
# Document reconciliation
# =============================================================================


def test_load_existing_documents_indexes_by_hash(
    monkeypatch,
):
    content = b"RestoMart document"
    file_hash = _sha256(content)

    document = SimpleNamespace(
        id=uuid4(),
        filename="restomart.txt",
        file_hash=file_hash,
    )

    repository = Mock()
    repository.list_by_startup.return_value = [
        document
    ]

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.DocumentRepository",
        Mock(return_value=repository),
    )

    result = _load_existing_documents(
        Mock(),
        uuid4(),
    )

    assert result[file_hash] is document


def test_upload_documents_reuses_same_hash_and_uploads_missing(
    monkeypatch,
    tmp_path: Path,
):
    existing_data = b"Existing RestoMart document"
    new_data = b"New RestoMart document"

    existing_hash = _sha256(existing_data)

    existing_document = SimpleNamespace(
        id=uuid4(),
        filename="existing.txt",
        file_hash=existing_hash,
    )

    new_document = SimpleNamespace(
        id=uuid4(),
        filename="new.txt",
        file_hash=_sha256(new_data),
        document_type=DocumentType.OTHER,
        title="New Document",
        status=SimpleNamespace(
            value="uploaded"
        ),
        storage_path="startup/new.txt",
    )

    repository = Mock()
    repository.list_by_startup.return_value = [
        existing_document
    ]

    upload_service = Mock()
    upload_service.upload.return_value = (
        new_document
    )

    document_service = Mock()

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.DocumentRepository",
        Mock(return_value=repository),
    )

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.DocumentService",
        Mock(return_value=document_service),
    )

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.UploadService",
        Mock(return_value=upload_service),
    )

    existing_path = (
        tmp_path / "existing.txt"
    )
    existing_path.write_bytes(existing_data)

    new_path = tmp_path / "new.txt"
    new_path.write_bytes(new_data)

    specs = (
        DocumentSpec(
            path=existing_path,
            title="Existing Document",
            document_type=DocumentType.OTHER,
            description=None,
        ),
        DocumentSpec(
            path=new_path,
            title="New Document",
            document_type=DocumentType.OTHER,
            description=None,
        ),
    )

    session = Mock()
    storage = Mock()

    documents, created, reused = _upload_documents(
        session,
        storage,
        uuid4(),
        specs,
    )

    assert documents == (
        existing_document,
        new_document,
    )

    assert created == 1
    assert reused == 1

    upload_service.upload.assert_called_once()

    request = (
        upload_service.upload.call_args.args[0]
    )

    assert request.filename == "new.txt"
    assert request.data == new_data


def test_upload_documents_rejects_duplicate_input_content(
    monkeypatch,
    tmp_path: Path,
):
    content = b"same content"

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"

    first.write_bytes(content)
    second.write_bytes(content)

    repository = Mock()
    repository.list_by_startup.return_value = []

    monkeypatch.setattr(
        "scripts.startup_analysis_real_startup.DocumentRepository",
        Mock(return_value=repository),
    )

    specs = (
        DocumentSpec(
            path=first,
            title="First",
            document_type=DocumentType.OTHER,
            description=None,
        ),
        DocumentSpec(
            path=second,
            title="Second",
            document_type=DocumentType.OTHER,
            description=None,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Document already exists",
    ):
        _upload_documents(
            Mock(),
            Mock(),
            uuid4(),
            specs,
        )
