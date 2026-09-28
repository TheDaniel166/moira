"""Tests for the ChartLRUCache and the chart route caching behaviour."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from time import monotonic, sleep
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.cache import ChartLRUCache, ResponseLRUCache
from moira_server.models.sade_sati import SadeSatiWindowsRequest
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


# ---------------------------------------------------------------------------
# Unit tests for ChartLRUCache
# ---------------------------------------------------------------------------


class TestChartLRUCache:
    def test_miss_returns_none(self) -> None:
        cache = ChartLRUCache(maxsize=4)
        assert cache.get("nonexistent") is None

    def test_set_and_get_round_trips(self) -> None:
        cache = ChartLRUCache(maxsize=4)
        cache.set("k1", {"value": 42})
        assert cache.get("k1") == {"value": 42}

    def test_hit_and_miss_counters(self) -> None:
        cache = ChartLRUCache(maxsize=4)
        cache.get("missing")
        cache.set("k", "v")
        cache.get("k")
        assert cache.misses == 1
        assert cache.hits == 1

    def test_lru_eviction_removes_oldest_entry(self) -> None:
        cache = ChartLRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Access "a" to make it recently used
        cache.get("a")
        # Adding "d" should evict "b" (oldest unused)
        cache.set("d", 4)
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_maxsize_is_respected(self) -> None:
        cache = ChartLRUCache(maxsize=5)
        for i in range(10):
            cache.set(str(i), i)
        assert len(cache) == 5

    def test_clear_resets_store_and_counters(self) -> None:
        cache = ChartLRUCache(maxsize=4)
        cache.set("x", 1)
        cache.get("x")
        cache.clear()
        assert len(cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_overwrite_existing_key_does_not_grow_cache(self) -> None:
        cache = ChartLRUCache(maxsize=4)
        cache.set("k", "first")
        cache.set("k", "second")
        assert len(cache) == 1
        assert cache.get("k") == "second"


class TestResponseLRUCache:
    def test_get_or_compute_does_not_cache_failures(self) -> None:
        cache = ResponseLRUCache(maxsize=4)
        calls = 0

        def fail_once() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("transient")
            return "recovered"

        with pytest.raises(RuntimeError, match="transient"):
            cache.get_or_compute("key", fail_once)

        assert cache.get_or_compute("key", fail_once) == "recovered"
        assert calls == 2

    def test_get_or_compute_coalesces_concurrent_identical_work(self) -> None:
        cache = ResponseLRUCache(maxsize=4)
        worker_count = 8
        barrier = Barrier(worker_count)
        counter_lock = Lock()
        calls = 0

        def factory() -> str:
            nonlocal calls
            with counter_lock:
                calls += 1
            deadline = monotonic() + 2.0
            while cache.waits < worker_count - 1:
                if monotonic() >= deadline:
                    raise AssertionError("concurrent callers did not reach the cache")
                sleep(0.001)
            return "shared"

        def invoke() -> str:
            barrier.wait()
            return cache.get_or_compute("same-key", factory)

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = list(executor.map(lambda _: invoke(), range(worker_count)))

        assert results == ["shared"] * worker_count
        assert calls == 1
        assert cache.misses == 1
        assert cache.waits == worker_count - 1

    def test_request_key_normalizes_aware_datetimes_to_utc(self) -> None:
        cache = ResponseLRUCache(maxsize=4)
        engine = SimpleNamespace(_reader_obj=SimpleNamespace(
            _source_identity={"sha256": "abc"},
            _kernel_identity={"planetary_ephemeris": "DE441"},
        ))
        utc_request = SadeSatiWindowsRequest(
            natal_moon_sidereal_lon=35.0,
            start_dt="2000-01-01T00:00:00+00:00",
            end_dt="2001-01-01T00:00:00+00:00",
        )
        offset_request = SadeSatiWindowsRequest(
            natal_moon_sidereal_lon=35.0,
            start_dt="1999-12-31T19:00:00-05:00",
            end_dt="2000-12-31T19:00:00-05:00",
        )

        assert cache.make_request_key(
            "v1:sade-sati:windows", utc_request, engine=engine
        ) == cache.make_request_key(
            "v1:sade-sati:windows", offset_request, engine=engine
        )

    def test_request_key_changes_with_resource_identity(self) -> None:
        cache = ResponseLRUCache(maxsize=4)
        request = SadeSatiWindowsRequest(
            natal_moon_sidereal_lon=35.0,
            start_dt="2000-01-01T00:00:00+00:00",
            end_dt="2001-01-01T00:00:00+00:00",
        )
        engine_a = SimpleNamespace(_reader_obj=SimpleNamespace(
            _source_identity={"sha256": "aaa"},
            _kernel_identity={"planetary_ephemeris": "DE441"},
        ))
        engine_b = SimpleNamespace(_reader_obj=SimpleNamespace(
            _source_identity={"sha256": "bbb"},
            _kernel_identity={"planetary_ephemeris": "DE441"},
        ))

        assert cache.make_request_key(
            "v1:test", request, engine=engine_a
        ) != cache.make_request_key("v1:test", request, engine=engine_b)


class TestChartCacheKeyBuilder:
    def test_same_inputs_produce_same_key(self) -> None:
        k1 = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", ["Sun", "Moon"], True, None, None, 0.0
        )
        k2 = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", ["Sun", "Moon"], True, None, None, 0.0
        )
        assert k1 == k2

    def test_body_order_does_not_affect_key(self) -> None:
        k1 = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", ["Moon", "Sun"], True, None, None, 0.0
        )
        k2 = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", ["Sun", "Moon"], True, None, None, 0.0
        )
        assert k1 == k2

    def test_different_datetimes_produce_different_keys(self) -> None:
        k1 = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", None, True, None, None, 0.0
        )
        k2 = ChartLRUCache.make_chart_key(
            "1990-06-15T12:00:00+00:00", None, True, None, None, 0.0
        )
        assert k1 != k2

    def test_different_observer_coords_produce_different_keys(self) -> None:
        k1 = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", None, True, 40.7128, -74.0060, 10.0
        )
        k2 = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", None, True, 51.5, -0.1, 0.0
        )
        assert k1 != k2

    def test_none_bodies_vs_explicit_all_bodies_differ(self) -> None:
        # None means "all bodies" but explicit list should still differ from None
        k_none = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", None, True, None, None, 0.0
        )
        k_explicit = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", ["Sun"], True, None, None, 0.0
        )
        assert k_none != k_explicit

    def test_include_nodes_flag_affects_key(self) -> None:
        k_with = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", None, True, None, None, 0.0
        )
        k_without = ChartLRUCache.make_chart_key(
            "2000-01-01T12:00:00+00:00", None, False, None, None, 0.0
        )
        assert k_with != k_without


# ---------------------------------------------------------------------------
# Integration tests: chart routes use the cache
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_cache(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with a real engine and a fresh cache attached to app.state."""
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


@pytest.mark.requires_ephemeris
def test_chart_route_returns_same_payload_on_cache_hit(
    client_with_cache: TestClient,
) -> None:
    """Two identical POST /v1/chart requests must return identical payloads."""
    payload = {
        "dt": "2000-01-01T12:00:00+00:00",
        "bodies": ["Sun", "Moon"],
        "include_nodes": True,
    }
    r1 = client_with_cache.post("/v1/chart", json=payload)
    r2 = client_with_cache.post("/v1/chart", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()


@pytest.mark.requires_ephemeris
def test_chart_reduction_route_returns_same_payload_on_cache_hit(
    client_with_cache: TestClient,
) -> None:
    """Two identical POST /v1/chart/reduction requests must return identical payloads."""
    payload = {
        "dt": "2000-01-01T12:00:00+00:00",
        "bodies": ["Sun", "Moon"],
        "include_nodes": True,
    }
    r1 = client_with_cache.post("/v1/chart/reduction", json=payload)
    r2 = client_with_cache.post("/v1/chart/reduction", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()


@pytest.mark.requires_ephemeris
def test_chart_and_reduction_routes_use_separate_cache_namespaces(
    client_with_cache: TestClient,
) -> None:
    """A cache hit on /v1/chart must not bleed into /v1/chart/reduction."""
    payload = {
        "dt": "2000-01-01T12:00:00+00:00",
        "bodies": ["Sun"],
        "include_nodes": False,
    }
    r_chart = client_with_cache.post("/v1/chart", json=payload)
    r_reduction = client_with_cache.post("/v1/chart/reduction", json=payload)

    assert r_chart.status_code == 200
    assert r_reduction.status_code == 200
    # The reduction response has a "result" and "reduction" wrapper; chart does not.
    assert "result" in r_reduction.json()
    assert "reduction" in r_reduction.json()
    assert "result" not in r_chart.json()


@pytest.mark.requires_ephemeris
def test_different_datetimes_are_cached_independently(
    client_with_cache: TestClient,
) -> None:
    """Charts for different datetimes must not collide in the cache."""
    payload_a = {"dt": "2000-01-01T12:00:00+00:00", "bodies": ["Sun"], "include_nodes": False}
    payload_b = {"dt": "1990-06-15T12:00:00+00:00", "bodies": ["Sun"], "include_nodes": False}

    r_a = client_with_cache.post("/v1/chart", json=payload_a)
    r_b = client_with_cache.post("/v1/chart", json=payload_b)

    assert r_a.status_code == 200
    assert r_b.status_code == 200
    # Sun longitude must differ for the two dates
    lon_a = r_a.json()["planets"]["Sun"]["longitude"]
    lon_b = r_b.json()["planets"]["Sun"]["longitude"]
    assert abs(lon_a - lon_b) > 0.01
