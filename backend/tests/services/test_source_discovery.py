from pathlib import Path

from app.models.source_document import (
    ExtractionStatus,
    SourceCategory,
    SourceType,
)
from app.services.source_discovery import (
    SourceDiscoveryService,
)


def test_discover_restomart_sources():
    source_root = Path(
        "data/real_startups/restomart/sources"
    )

    service = SourceDiscoveryService()

    sources = service.discover(
        startup_id="restomart",
        source_root=source_root,
    )

    assert sources

    assert all(
        source.startup_id == "restomart"
        for source in sources
    )

    assert all(
        source.extraction_status
        == ExtractionStatus.DISCOVERED
        for source in sources
    )

    assert all(
        source.sha256
        and len(source.sha256) == 64
        for source in sources
    )


def test_discover_restomart_file_types():
    source_root = Path(
        "data/real_startups/restomart/sources"
    )

    sources = SourceDiscoveryService().discover(
        startup_id="restomart",
        source_root=source_root,
    )

    source_types = {
        source.source_type
        for source in sources
    }

    assert SourceType.PDF in source_types
    assert SourceType.DOCX in source_types
    assert SourceType.XLSX in source_types
    assert SourceType.HTML in source_types


def test_discover_restomart_categories():
    source_root = Path(
        "data/real_startups/restomart/sources"
    )

    sources = SourceDiscoveryService().discover(
        startup_id="restomart",
        source_root=source_root,
    )

    categories = {
        source.source_category
        for source in sources
    }

    assert SourceCategory.BUSINESS in categories
    assert SourceCategory.FINANCIAL in categories
    assert SourceCategory.LEGAL in categories
    assert SourceCategory.WEB in categories
