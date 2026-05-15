"""
resilience.py — API Hardening: Retry, Circuit Breaker, Timeout
Windows-compatible implementation (threading-based timeout, no signal.SIGALRM).
"""

from __future__ import annotations

import functools
import logging
import random
import threading
import time
from enum import Enum
from typing import Any, Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    EXPONENTIAL = "exponential"
    LINEAR      = "linear"
    FIXED       = "fixed"


class CircuitBreakerState(str, Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

class RetryPolicy:
    """Configuration for automatic retry with backoff."""

    def __init__(
        self,
        max_attempts:          int   = 3,
        initial_delay:         float = 1.0,
        max_delay:             float = 60.0,
        strategy:              RetryStrategy = RetryStrategy.EXPONENTIAL,
        backoff_factor:        float = 2.0,
        jitter:                bool  = True,
        retryable_exceptions:  Optional[Tuple[Type[Exception], ...]] = None,
    ) -> None:
        self.max_attempts         = max_attempts
        self.initial_delay        = initial_delay
        self.max_delay            = max_delay
        self.strategy             = strategy
        self.backoff_factor       = backoff_factor
        self.jitter               = jitter
        self.retryable_exceptions = retryable_exceptions or (Exception,)

    def get_delay(self, attempt: int) -> float:
        """Compute sleep duration for the given attempt number (1-based)."""
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay * attempt
        else:
            delay = self.initial_delay

        delay = min(delay, self.max_delay)

        if self.jitter:
            delay += random.uniform(0, delay * 0.1)

        return delay


def retry(policy: Optional[RetryPolicy] = None):
    """Decorator that retries the wrapped function according to *policy*."""

    if policy is None:
        policy = RetryPolicy()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            for attempt in range(1, policy.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info("%s succeeded on attempt %d/%d",
                                    func.__name__, attempt, policy.max_attempts)
                    return result
                except policy.retryable_exceptions as exc:
                    last_exc = exc
                    if attempt < policy.max_attempts:
                        delay = policy.get_delay(attempt)
                        logger.warning(
                            "%s failed (attempt %d/%d), retrying in %.2fs: %s",
                            func.__name__, attempt, policy.max_attempts, delay, exc,
                        )
                        time.sleep(delay)
                    else:
                        logger.error("%s failed after %d attempts: %s",
                                     func.__name__, policy.max_attempts, exc)
            raise last_exc  # type: ignore[misc]
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Circuit breaker: CLOSED → OPEN after *failure_threshold* failures."""

    def __init__(
        self,
        failure_threshold: int   = 5,
        recovery_timeout:  float = 60.0,
        name:              str   = "default",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout  = recovery_timeout
        self.name              = name

        self.state:             CircuitBreakerState = CircuitBreakerState.CLOSED
        self.failure_count:     int                 = 0
        self.success_count:     int                 = 0
        self.last_failure_time: Optional[float]     = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("%s: attempting recovery (HALF_OPEN)", self.name)
            else:
                raise Exception(
                    f"Circuit breaker '{self.name}' is OPEN. Service unavailable."
                )
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        self.failure_count = 0
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:
                self.state         = CircuitBreakerState.CLOSED
                self.success_count = 0
                logger.info("%s: circuit CLOSED (recovered)", self.name)

    def _on_failure(self) -> None:
        self.failure_count     += 1
        self.last_failure_time  = time.monotonic()
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.error("%s: circuit OPEN (recovery failed)", self.name)
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.error("%s: circuit OPEN (%d failures)", self.name, self.failure_count)

    def _should_attempt_recovery(self) -> bool:
        if self.last_failure_time is None:
            return True
        return (time.monotonic() - self.last_failure_time) >= self.recovery_timeout


# ---------------------------------------------------------------------------
# TimeoutHandler (threading-based, Windows-compatible)
# ---------------------------------------------------------------------------

class TimeoutHandler:
    """Thread-based timeout wrapper (works on Windows — no signal.SIGALRM)."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def with_timeout(
        self, func: Callable, timeout: Optional[float] = None
    ) -> Callable:
        timeout_val = timeout or self.timeout_seconds

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result:    list = [None]
            exc:       list = [None]

            def target() -> None:
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exc[0] = e

            t = threading.Thread(target=target, daemon=True)
            t.start()
            t.join(timeout=timeout_val)

            if t.is_alive():
                raise TimeoutError(
                    f"Operation timed out after {timeout_val}s"
                )
            if exc[0] is not None:
                raise exc[0]
            return result[0]

        return wrapper


# ---------------------------------------------------------------------------
# Module-level singletons for bridge_api.py use
# ---------------------------------------------------------------------------

api_retry_policy = RetryPolicy(
    max_attempts=3,
    initial_delay=1.0,
    strategy=RetryStrategy.EXPONENTIAL,
)

valuation_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
    name="valuation_engine",
)

timeout_handler = TimeoutHandler(timeout_seconds=30.0)
