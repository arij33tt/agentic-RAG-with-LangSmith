import time
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Tracks failures per named provider. After `failure_threshold`
    consecutive failures, the circuit "opens" and calls are rejected
    immediately for `cooldown_seconds`, instead of hitting a dead
    provider repeatedly. After cooldown, it allows one trial call
    ("half-open") — success closes the circuit again, failure
    reopens it.
    """

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}
        self._lock = Lock()

    def is_open(self, provider_name: str) -> bool:
        """True = don't even try this provider right now"""
        with self._lock:
            opened_at = self._opened_at.get(provider_name)
            if opened_at is None:
                return False  # circuit was never tripped

            elapsed = time.time() - opened_at
            if elapsed >= self.cooldown_seconds:
                # cooldown passed — allow one trial call (half-open state)
                logger.info(f"Circuit for '{provider_name}' entering half-open trial")
                return False

            return True  # still cooling down, reject immediately

    def record_success(self, provider_name: str) -> None:
        with self._lock:
            self._failures[provider_name] = 0
            self._opened_at.pop(provider_name, None)

    def record_failure(self, provider_name: str) -> None:
        with self._lock:
            self._failures[provider_name] = self._failures.get(provider_name, 0) + 1
            if self._failures[provider_name] >= self.failure_threshold:
                if provider_name not in self._opened_at:
                    logger.warning(
                        f"Circuit OPENED for '{provider_name}' after "
                        f"{self._failures[provider_name]} consecutive failures"
                    )
                self._opened_at[provider_name] = time.time()