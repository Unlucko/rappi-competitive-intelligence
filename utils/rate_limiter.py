import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RateLimiter:

    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.last_request_time: float = 0.0

    async def wait_between_requests(self) -> None:
        elapsed_since_last = time.monotonic() - self.last_request_time
        required_delay = random.uniform(self.min_delay, self.max_delay)
        remaining_wait = required_delay - elapsed_since_last

        if remaining_wait > 0:
            logger.debug("Rate limiter waiting %.2f seconds", remaining_wait)
            await asyncio.sleep(remaining_wait)

        self.last_request_time = time.monotonic()

    async def execute_with_retry(
        self,
        coroutine_factory: Callable[..., Any],
        *args: Any,
        operation_name: str = "operation",
        **kwargs: Any,
    ) -> Optional[Any]:
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                await self.wait_between_requests()
                result = await coroutine_factory(*args, **kwargs)
                return result
            except Exception as exception:
                last_exception = exception
                backoff_time = self.backoff_base ** attempt + random.uniform(0, 1)
                logger.warning(
                    "Attempt %d/%d for %s failed: %s. Retrying in %.1f seconds",
                    attempt,
                    self.max_retries,
                    operation_name,
                    str(exception),
                    backoff_time,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(backoff_time)

        logger.error(
            "All %d attempts failed for %s. Last error: %s",
            self.max_retries,
            operation_name,
            str(last_exception),
        )
        return None
