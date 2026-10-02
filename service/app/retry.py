import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.config import Settings
from app.exceptions import ExternalServiceError

T = TypeVar("T")


async def with_retries(operation: Callable[[], Awaitable[T]], settings: Settings, label: str) -> T:
    last_error: Exception | None = None
    attempts = settings.external_retry_count + 1
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception as exc:  # noqa: BLE001 - converted to a stable app exception.
            last_error = exc
            if attempt == attempts - 1:
                break
            await asyncio.sleep(settings.retry_backoff_seconds * (2**attempt))
    raise ExternalServiceError(f"{label} failed after {attempts} attempts: {last_error}") from last_error

