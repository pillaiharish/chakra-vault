"""Fake download service harness for throttling tests."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass

from chakra_vault.downloads.throttle import DownloadScheduler, ThrottleConfig

ProgressSink = Callable[["DownloadProgress"], None]


@dataclass(frozen=True)
class DownloadPlan:
    """Provider-neutral fake download plan."""

    download_id: str
    source_name: str
    target_name: str
    total_bytes: int | None
    throttle: ThrottleConfig
    resume_from_bytes: int = 0

    def __post_init__(self) -> None:
        if self.total_bytes is not None and self.total_bytes < 0:
            raise ValueError("total_bytes must be non-negative or None")
        if self.resume_from_bytes < 0:
            raise ValueError("resume_from_bytes must be non-negative")
        if self.total_bytes is not None and self.resume_from_bytes > self.total_bytes:
            raise ValueError("resume_from_bytes cannot exceed total_bytes")


@dataclass(frozen=True)
class DownloadProgress:
    """Progress event emitted by the fake download service."""

    current_speed_bytes_per_sec: float
    max_speed_bytes_per_sec: int | None
    global_max_speed_bytes_per_sec: int | None
    downloaded_bytes: int
    total_bytes: int | None
    eta_seconds: float | None
    throttle_enabled: bool
    throttle_profile: str | None
    network_mode: str
    resume_enabled: bool


@dataclass(frozen=True)
class FakeDownloadSource:
    """Deterministic fake byte source.

    Chunk values are byte counts. The source never reads from disk and never
    opens network connections.
    """

    chunks: tuple[int, ...]

    @classmethod
    def from_chunks(cls, chunks: Iterable[int]) -> FakeDownloadSource:
        return cls(tuple(chunks))

    @property
    def total_bytes(self) -> int:
        return sum(self.chunks)

    def iter_chunks(self) -> Iterator[int]:
        for chunk_size in self.chunks:
            if chunk_size < 0:
                raise ValueError("fake chunk sizes must be non-negative")
            yield chunk_size


def run_download_plan(
    plan: DownloadPlan,
    source: FakeDownloadSource,
    progress_sink: ProgressSink,
    scheduler: DownloadScheduler,
) -> list[DownloadProgress]:
    """Run a fake download plan and emit progress after each accepted chunk."""

    started_at = scheduler.clock.now()
    downloaded_bytes = plan.resume_from_bytes
    downloaded_this_run = 0
    progress_events: list[DownloadProgress] = []
    job_throttle = scheduler.build_job_throttle(plan.throttle)

    for chunk_size in source.iter_chunks():
        scheduler.acquire(job_throttle, chunk_size)
        downloaded_bytes += chunk_size
        downloaded_this_run += chunk_size
        elapsed = scheduler.clock.now() - started_at
        current_speed = _current_speed(downloaded_this_run, elapsed)
        progress = DownloadProgress(
            current_speed_bytes_per_sec=current_speed,
            max_speed_bytes_per_sec=plan.throttle.max_speed_bytes_per_sec,
            global_max_speed_bytes_per_sec=plan.throttle.global_max_speed_bytes_per_sec,
            downloaded_bytes=downloaded_bytes,
            total_bytes=plan.total_bytes,
            eta_seconds=estimate_eta_seconds(
                plan.total_bytes, downloaded_bytes, current_speed
            ),
            throttle_enabled=plan.throttle.throttle_enabled,
            throttle_profile=plan.throttle.profile_name,
            network_mode=network_mode_for(plan.throttle),
            resume_enabled=plan.throttle.resume,
        )
        progress_sink(progress)
        progress_events.append(progress)

    return progress_events


def estimate_eta_seconds(
    total_bytes: int | None,
    downloaded_bytes: int,
    current_speed_bytes_per_sec: float,
) -> float | None:
    if total_bytes is None or current_speed_bytes_per_sec <= 0:
        return None
    remaining_bytes = max(0, total_bytes - downloaded_bytes)
    return remaining_bytes / current_speed_bytes_per_sec


def network_mode_for(throttle: ThrottleConfig) -> str:
    if throttle.throttle_enabled:
        return "polite background download"
    return "unlimited local fake download"


def _current_speed(downloaded_bytes: int, elapsed_seconds: float) -> float:
    if downloaded_bytes <= 0 or elapsed_seconds <= 0:
        return 0.0
    return downloaded_bytes / elapsed_seconds
