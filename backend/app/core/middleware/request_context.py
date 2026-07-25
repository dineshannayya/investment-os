"""
Per-request context shared by all middleware.
"""

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class RequestContext:

    request_id: UUID

    method: str

    path: str

    start_time: float = field(default_factory=perf_counter)

    status_code: int | None = None

    duration_ms: float | None = None

    exception: Exception | None = None

    user_id: str | None = None

    workspace: str | None = None

    extra: dict[str, Any] = field(default_factory=dict)
