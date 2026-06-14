"""Provider-neutral download throttling core."""

from chakra_vault.downloads.service import (
    DownloadPlan,
    DownloadProgress,
    FakeDownloadSource,
    estimate_eta_seconds,
    network_mode_for,
    run_download_plan,
)
from chakra_vault.downloads.throttle import (
    DownloadScheduler,
    FakeClock,
    GlobalDownloadThrottle,
    PerJobThrottle,
    ThrottleConfig,
    parse_speed_limit,
)

__all__ = [
    "DownloadPlan",
    "DownloadProgress",
    "DownloadScheduler",
    "FakeClock",
    "FakeDownloadSource",
    "GlobalDownloadThrottle",
    "PerJobThrottle",
    "ThrottleConfig",
    "estimate_eta_seconds",
    "network_mode_for",
    "parse_speed_limit",
    "run_download_plan",
]
