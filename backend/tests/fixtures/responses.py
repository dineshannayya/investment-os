import pytest

from app.core.config.error_codes import ErrorCode
from app.schemas.error import ErrorDetail
from app.schemas.pagination import PaginationMeta
from app.schemas.response import ResponseMeta

# =============================================================================
# Common Schema Fixtures
# =============================================================================


@pytest.fixture
def request_id() -> str:
    """
    Sample request identifier.
    """
    return "test-request-id"


@pytest.fixture
def sample_error() -> ErrorDetail:
    """
    Standard validation error.
    """
    return ErrorDetail(
        code=ErrorCode.VALIDATION_ERROR,
        message="Validation failed.",
        field="email",
    )


@pytest.fixture
def sample_pagination() -> PaginationMeta:
    """
    Standard pagination metadata.
    """
    return PaginationMeta(
        page=1,
        per_page=20,
        total_items=100,
        total_pages=5,
        has_previous=False,
        has_next=True,
    )


@pytest.fixture
def response_meta(
    request_id: str,
    sample_pagination: PaginationMeta,
) -> ResponseMeta:
    """
    Standard response metadata.
    """
    return ResponseMeta(
        request_id=request_id,
        pagination=sample_pagination,
    )


@pytest.fixture
def sample_dict():
    """
    Generic dictionary payload.
    """
    return {
        "id": 1,
        "name": "Investment OS",
    }


@pytest.fixture
def sample_list():
    """
    Generic list payload.
    """
    return [
        "one",
        "two",
        "three",
    ]
