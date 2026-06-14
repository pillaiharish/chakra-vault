"""Provider-neutral download throttling primitives."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

_SPEED_PATTERN = re.compile(
    r"^\s*(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>kib|mib|gib|kb|mb|gb)\s*/\s*s\s*$",
    re.IGNORECASE,
)

_UNITS = {
    "kb": 1000,
    "mb": 1000**2,
    "gb": 1000**3,
    "kib": 1024,
    "mib": 1024**2,
    "gib": 1024**3,
}


class Clock(Protocol):
    """Clock interface used by throttles."""

    def now(self) -> float:
        """Return monotonic time in seconds."""

    def sleep(self, seconds: float) -> None:
        """Sleep or advance time by ``seconds``."""


class FakeClock:
    """Deterministic clock for tests and fake downloads."""

    def __init__(self) -> None:
        self._now = 0.0

    def now(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("sleep seconds must be non-negative")
        self._now += seconds


def parse_speed_limit(value: str) -> int:
    """Parse a speed string such as ``2MB/s`` into bytes per second."""

    if not isinstance(value, str):
        raise ValueError("speed limit must be a string with units, for example '2MB/s'")

    match = _SPEED_PATTERN.match(value)
    if match is None:
        raise ValueError(
            "invalid speed limit; expected a positive value with KB/s, MB/s, GB/s, "
            "KiB/s, MiB/s, or GiB/s"
        )

    amount = float(match.group("amount"))
    if amount <= 0:
        raise ValueError("speed limit must be greater than zero")

    unit = match.group("unit").lower()
    bytes_per_second = int(amount * _UNITS[unit])
    if bytes_per_second <= 0:
        raise ValueError("speed limit must resolve to at least one byte per second")
    return bytes_per_second


@dataclass(frozen=True)
class ThrottleConfig:
    """Configuration carried by fake download plans and progress events."""

    max_speed_bytes_per_sec: int | None
    global_max_speed_bytes_per_sec: int | None
    max_parallel_files: int = 1
    resume: bool = True
    verify_after_download: bool = True
    pause_when_disk_below_bytes: int | None = None
    profile_name: str | None = None

    def __post_init__(self) -> None:
        _validate_optional_positive_int(
            self.max_speed_bytes_per_sec, "max_speed_bytes_per_sec"
        )
        _validate_optional_positive_int(
            self.global_max_speed_bytes_per_sec, "global_max_speed_bytes_per_sec"
        )
        _validate_optional_positive_int(
            self.pause_when_disk_below_bytes, "pause_when_disk_below_bytes"
        )
        if self.max_parallel_files < 1:
            raise ValueError("max_parallel_files must be at least 1")

    @property
    def throttle_enabled(self) -> bool:
        return (
            self.max_speed_bytes_per_sec is not None
            or self.global_max_speed_bytes_per_sec is not None
        )


class _TokenBucket:
    def __init__(self, bytes_per_second: int | None, clock: Clock) -> None:
        _validate_optional_positive_int(bytes_per_second, "bytes_per_second")
        self._bytes_per_second = bytes_per_second
        self._clock = clock
        self._tokens = 0.0
        self._updated_at = clock.now()

    @property
    def bytes_per_second(self) -> int | None:
        return self._bytes_per_second

    def acquire(self, byte_count: int) -> float:
        if byte_count < 0:
            raise ValueError("byte_count must be non-negative")
        if byte_count == 0 or self._bytes_per_second is None:
            return 0.0

        self._refill()
        if self._tokens < byte_count:
            missing_tokens = byte_count - self._tokens
            wait_seconds = missing_tokens / self._bytes_per_second
            self._clock.sleep(wait_seconds)
            self._refill()

        self._tokens -= byte_count
        return self._clock.now()

    def _refill(self) -> None:
        now = self._clock.now()
        elapsed = max(0.0, now - self._updated_at)
        self._tokens += elapsed * self._bytes_per_second if self._bytes_per_second else 0
        self._updated_at = now


class PerJobThrottle:
    """Token-bucket throttle for one download stream."""

    def __init__(self, bytes_per_second: int | None, clock: Clock) -> None:
        self._bucket = _TokenBucket(bytes_per_second, clock)

    @property
    def bytes_per_second(self) -> int | None:
        return self._bucket.bytes_per_second

    def acquire(self, byte_count: int) -> float:
        return self._bucket.acquire(byte_count)


class GlobalDownloadThrottle:
    """Shared token-bucket throttle for all active download streams."""

    def __init__(self, bytes_per_second: int | None, clock: Clock) -> None:
        self._bucket = _TokenBucket(bytes_per_second, clock)

    @property
    def bytes_per_second(self) -> int | None:
        return self._bucket.bytes_per_second

    def acquire(self, byte_count: int) -> float:
        return self._bucket.acquire(byte_count)


class DownloadScheduler:
    """Apply per-job and global throttles using a shared deterministic clock."""

    def __init__(
        self,
        clock: Clock,
        global_throttle: GlobalDownloadThrottle | None = None,
        max_parallel_files: int = 1,
    ) -> None:
        if max_parallel_files < 1:
            raise ValueError("max_parallel_files must be at least 1")
        self.clock = clock
        self.global_throttle = global_throttle
        self.max_parallel_files = max_parallel_files

    @classmethod
    def from_config(cls, config: ThrottleConfig, clock: Clock) -> DownloadScheduler:
        global_throttle = GlobalDownloadThrottle(
            config.global_max_speed_bytes_per_sec, clock
        )
        return cls(
            clock=clock,
            global_throttle=global_throttle,
            max_parallel_files=config.max_parallel_files,
        )

    def build_job_throttle(self, config: ThrottleConfig) -> PerJobThrottle:
        return PerJobThrottle(config.max_speed_bytes_per_sec, self.clock)

    def acquire(self, job_throttle: PerJobThrottle, byte_count: int) -> float:
        started_at = self.clock.now()
        job_throttle.acquire(byte_count)
        if self.global_throttle is not None:
            self.global_throttle.acquire(byte_count)
        return self.clock.now() - started_at


def _validate_optional_positive_int(value: int | None, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer or None")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
