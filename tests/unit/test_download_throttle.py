from __future__ import annotations

import pytest

from chakra_vault.downloads.throttle import (
    DownloadScheduler,
    FakeClock,
    GlobalDownloadThrottle,
    PerJobThrottle,
    ThrottleConfig,
    parse_speed_limit,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("500KB/s", 500_000),
        ("2MB/s", 2_000_000),
        ("5MiB/s", 5 * 1024**2),
        ("1 GB/s", 1_000_000_000),
        (" 2 mb / s ", 2_000_000),
        ("3kIb/S", 3 * 1024),
    ],
)
def test_parse_speed_limit_accepts_supported_units(value: str, expected: int) -> None:
    assert parse_speed_limit(value) == expected


@pytest.mark.parametrize(
    "value",
    ["", "2", "0MB/s", "-1MB/s", "2XB/s", "MB/s", "fast", "1MB/sec"],
)
def test_parse_speed_limit_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="speed limit|greater than|invalid"):
        parse_speed_limit(value)


def test_per_job_throttle_limits_average_speed_with_fake_clock() -> None:
    clock = FakeClock()
    throttle = PerJobThrottle(bytes_per_second=100, clock=clock)

    throttle.acquire(100)
    throttle.acquire(100)

    assert clock.now() == pytest.approx(2.0)
    assert 200 / clock.now() <= 100


def test_global_throttle_limits_combined_average_speed() -> None:
    clock = FakeClock()
    scheduler = DownloadScheduler(
        clock=clock,
        global_throttle=GlobalDownloadThrottle(bytes_per_second=100, clock=clock),
    )
    job_a = PerJobThrottle(bytes_per_second=None, clock=clock)
    job_b = PerJobThrottle(bytes_per_second=None, clock=clock)

    scheduler.acquire(job_a, 100)
    scheduler.acquire(job_b, 100)

    assert clock.now() == pytest.approx(2.0)
    assert 200 / clock.now() <= 100


def test_scheduler_applies_per_job_and_global_limits() -> None:
    clock = FakeClock()
    config = ThrottleConfig(
        max_speed_bytes_per_sec=100,
        global_max_speed_bytes_per_sec=50,
        max_parallel_files=2,
    )
    scheduler = DownloadScheduler.from_config(config, clock)
    job_throttle = scheduler.build_job_throttle(config)

    scheduler.acquire(job_throttle, 100)

    assert clock.now() == pytest.approx(2.0)
    assert 100 / clock.now() <= 50
    assert scheduler.max_parallel_files == 2
