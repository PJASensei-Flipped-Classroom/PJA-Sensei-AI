import pytest

from app.api.middleware import reset_rate_limit_buckets
from app.core.config import settings


@pytest.fixture(autouse=True)
def _isolate_rate_limits():
    """Keep inbound rate-limit state from leaking across the whole suite."""
    prev_limit = settings.RATE_LIMIT_PER_MINUTE
    # OLD: no frustration cooldown override
    # Why: suite S4/m5 posts two IDE events immediately to unlock hints.
    # Wrong: production 15s cooldown would flake those tests.
    # Better: force cooldown=0 only inside pytest; restore after.
    prev_cooldown = settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS
    settings.RATE_LIMIT_PER_MINUTE = 10_000
    settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS = 0.0
    reset_rate_limit_buckets()
    yield
    reset_rate_limit_buckets()
    settings.RATE_LIMIT_PER_MINUTE = prev_limit
    settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS = prev_cooldown
