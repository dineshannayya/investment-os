from app.core.config.constants import (
    API_PREFIX,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)


def test_constants():
    assert API_PREFIX == "/api/v1"
    assert DEFAULT_PAGE_SIZE == 20
    assert MAX_PAGE_SIZE == 100
