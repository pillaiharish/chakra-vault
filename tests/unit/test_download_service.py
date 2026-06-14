from __future__ import annotations

from dataclasses import fields

import pytest

from chakra_vault.downloads.service import (
    DownloadPlan,
    DownloadProgress,
    FakeDownloadSource,
    estimate_eta_seconds,
    network_mode_for,
    run_download_plan,
)
from chakra_vault.downloads.throttle import DownloadScheduler, FakeClock, ThrottleConfig


def test_fake_download_emits_every_required_progress_field() -> None:
    clock = FakeClock()
    throttle = ThrottleConfig(
        max_speed_bytes_per_sec=100,
        global_max_speed_bytes_per_sec=200,
        profile_name="balanced",
    )
    scheduler = DownloadScheduler.from_config(throttle, clock)
    plan = DownloadPlan(
        download_id="job-1",
        source_name="fake-source",
        target_name="fake-target",
        total_bytes=100,
        throttle=throttle,
    )
    emitted: list[DownloadProgress] = []

    events = run_download_plan(
        plan,
        FakeDownloadSource.from_chunks([50, 50]),
        emitted.append,
        scheduler,
    )

    assert events == emitted
    assert {field.name for field in fields(DownloadProgress)} == {
        "current_speed_bytes_per_sec",
        "max_speed_bytes_per_sec",
        "global_max_speed_bytes_per_sec",
        "downloaded_bytes",
        "total_bytes",
        "eta_seconds",
        "throttle_enabled",
        "throttle_profile",
        "network_mode",
        "resume_enabled",
    }
    assert emitted[-1].downloaded_bytes == 100
    assert emitted[-1].current_speed_bytes_per_sec <= 100


def test_eta_handles_known_total_zero_progress_and_unknown_total() -> None:
    assert estimate_eta_seconds(100, downloaded_bytes=50, current_speed_bytes_per_sec=25) == 2
    assert estimate_eta_seconds(100, downloaded_bytes=0, current_speed_bytes_per_sec=0) is None
    assert estimate_eta_seconds(None, downloaded_bytes=50, current_speed_bytes_per_sec=25) is None


def test_resume_preserves_throttle_settings_in_progress() -> None:
    clock = FakeClock()
    throttle = ThrottleConfig(
        max_speed_bytes_per_sec=100,
        global_max_speed_bytes_per_sec=150,
        resume=True,
        profile_name="slow-lane",
    )
    scheduler = DownloadScheduler.from_config(throttle, clock)
    plan = DownloadPlan(
        download_id="job-2",
        source_name="fake-source",
        target_name="fake-target",
        total_bytes=200,
        throttle=throttle,
        resume_from_bytes=100,
    )
    emitted: list[DownloadProgress] = []

    run_download_plan(plan, FakeDownloadSource.from_chunks([50]), emitted.append, scheduler)

    progress = emitted[0]
    assert progress.downloaded_bytes == 150
    assert progress.max_speed_bytes_per_sec == 100
    assert progress.global_max_speed_bytes_per_sec == 150
    assert progress.throttle_enabled is True
    assert progress.throttle_profile == "slow-lane"
    assert progress.resume_enabled is True


@pytest.mark.parametrize(
    ("throttle", "expected"),
    [
        (
            ThrottleConfig(100, None),
            "polite background download",
        ),
        (
            ThrottleConfig(None, None),
            "unlimited local fake download",
        ),
    ],
)
def test_network_mode_reflects_throttle_state(
    throttle: ThrottleConfig, expected: str
) -> None:
    assert network_mode_for(throttle) == expected


def test_fake_download_uses_no_filesystem_or_network() -> None:
    clock = FakeClock()
    throttle = ThrottleConfig(None, None)
    scheduler = DownloadScheduler.from_config(throttle, clock)
    plan = DownloadPlan(
        download_id="job-3",
        source_name="memory-only",
        target_name="memory-only-target",
        total_bytes=10,
        throttle=throttle,
    )
    emitted: list[DownloadProgress] = []

    run_download_plan(plan, FakeDownloadSource.from_chunks([10]), emitted.append, scheduler)

    assert emitted[0].downloaded_bytes == 10
    assert emitted[0].network_mode == "unlimited local fake download"
