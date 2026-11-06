import pytest

from app.api.middleware import reset_rate_limit_buckets
from app.core.config import settings


@pytest.fixture(autouse=True)
def _isolate_rate_limits():
    """Keep inbound rate-limit state from leaking across the whole suite."""
    prev_limit = settings.RATE_LIMIT_PER_MINUTE
    prev_cooldown = settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS
    prev_debug = settings.AI_EXPOSE_DEBUG
    settings.RATE_LIMIT_PER_MINUTE = 10_000
    settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS = 0.0
    # Tests assert on MessageResponse.debug_info; production keeps AI_EXPOSE_DEBUG=false.
    settings.AI_EXPOSE_DEBUG = True
    reset_rate_limit_buckets()
    yield
    reset_rate_limit_buckets()
    settings.RATE_LIMIT_PER_MINUTE = prev_limit
    settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS = prev_cooldown
    settings.AI_EXPOSE_DEBUG = prev_debug
