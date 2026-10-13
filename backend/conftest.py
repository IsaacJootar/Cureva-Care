"""Pytest fixtures shared across the backend test suite."""
import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset the process cache before each test.

    The default locmem cache persists across tests in one process, which would
    otherwise leak DRF throttle counters (the session-exchange rate limit) and
    cached platform-setting values between tests.
    """
    cache.clear()
    yield
    cache.clear()
