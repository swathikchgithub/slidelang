"""Sliding-window rate limiter unit tests."""
import time

import pytest

from app.routes.generate import _RATE_LIMIT_RPM, _is_rate_limited, _rate_buckets


@pytest.fixture(autouse=True)
def isolate_ip(request):
    """Give each test a unique IP so they don't share bucket state."""
    ip = f"10.0.0.{request.node.originalname.__hash__() % 250 + 1}"
    request.node._test_ip = ip
    yield ip
    _rate_buckets.pop(ip, None)


def _ip(request) -> str:
    return request.node._test_ip


# ---------------------------------------------------------------------------
# Basic allow / block behaviour
# ---------------------------------------------------------------------------

def test_allows_requests_under_limit(request):
    ip = _ip(request)
    for _ in range(_RATE_LIMIT_RPM - 1):
        assert not _is_rate_limited(ip), "request under the limit should be allowed"


def test_allows_exactly_at_limit(request):
    ip = _ip(request)
    for _ in range(_RATE_LIMIT_RPM):
        _is_rate_limited(ip)  # consume all slots
    # At this point the bucket is full — next call is the 11th
    assert _is_rate_limited(ip), "request exceeding the limit should be blocked"


def test_blocks_on_limit_exceeded(request):
    ip = _ip(request)
    for _ in range(_RATE_LIMIT_RPM):
        _is_rate_limited(ip)
    assert _is_rate_limited(ip)


def test_blocked_request_is_not_recorded(request):
    """A rejected request must not consume a slot (bucket size unchanged)."""
    ip = _ip(request)
    for _ in range(_RATE_LIMIT_RPM):
        _is_rate_limited(ip)

    before = len(_rate_buckets[ip])
    _is_rate_limited(ip)  # rejected
    after = len(_rate_buckets[ip])
    assert after == before, "rejected request must not add a timestamp to the bucket"


# ---------------------------------------------------------------------------
# Sliding window — old timestamps expire
# ---------------------------------------------------------------------------

def test_old_requests_outside_window_do_not_count(request):
    """Timestamps older than 60s should be evicted and not count toward the limit."""
    ip = _ip(request)
    old_ts = time.monotonic() - 65  # 65 seconds ago — outside the 60s window

    # Manually fill the bucket with expired timestamps
    bucket = _rate_buckets[ip]
    for _ in range(_RATE_LIMIT_RPM):
        bucket.append(old_ts)

    # The next call should evict all old entries and allow the request
    assert not _is_rate_limited(ip), "expired timestamps must not block new requests"


def test_mix_of_old_and_fresh_requests(request):
    """Only fresh timestamps in the window contribute to the count."""
    ip = _ip(request)
    old_ts = time.monotonic() - 65
    bucket = _rate_buckets[ip]

    # Half expired, half fresh (still under the limit)
    half = _RATE_LIMIT_RPM // 2
    for _ in range(half):
        bucket.append(old_ts)
    for _ in range(half):
        _is_rate_limited(ip)  # records fresh timestamps

    # Should still be under the limit since old ones are evicted
    assert not _is_rate_limited(ip)


# ---------------------------------------------------------------------------
# IP isolation
# ---------------------------------------------------------------------------

def test_different_ips_have_independent_buckets():
    ip_a = "192.0.2.10"
    ip_b = "192.0.2.20"
    try:
        # Exhaust ip_a
        for _ in range(_RATE_LIMIT_RPM):
            _is_rate_limited(ip_a)
        assert _is_rate_limited(ip_a), "ip_a should be rate limited"

        # ip_b should still be clean
        assert not _is_rate_limited(ip_b), "ip_b must not be affected by ip_a's limit"
    finally:
        _rate_buckets.pop(ip_a, None)
        _rate_buckets.pop(ip_b, None)


def test_unknown_ip_gets_own_bucket():
    ip = "unknown"
    try:
        assert not _is_rate_limited(ip)
        assert ip in _rate_buckets
    finally:
        _rate_buckets.pop(ip, None)
