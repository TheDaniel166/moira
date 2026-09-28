"""Bounded, deterministic response caches for the Moira REST API.

The server caches only completed response models for engine computations that
are pure functions of a validated request and the active ephemeris resources.
Failures are never cached. The cache is process-local and application-owned,
so worker processes remain isolated and application shutdown drops all state.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from threading import Event, RLock
from typing import Any, TypeVar

from moira import __version__ as MOIRA_ENGINE_VERSION


_DEFAULT_CHART_MAX_SIZE = 512
EXPENSIVE_RESPONSE_CACHE_MAX_SIZE = 64
_CACHE_KEY_VERSION = 1
_T = TypeVar("_T")


@dataclass(slots=True)
class _InFlight:
    event: Event
    error: BaseException | None = None


def _canonical_value(value: Any) -> Any:
    """Return a JSON-safe, deterministic representation of validated input."""

    if isinstance(value, datetime):
        if value.tzinfo is not None and value.utcoffset() is not None:
            value = value.astimezone(timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_value(asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        canonical = [_canonical_value(item) for item in value]
        return sorted(canonical, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, float) and value == 0.0:
        return 0.0
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _reader_resource_identity(reader: Any) -> dict[str, Any]:
    """Describe the active reader without admitting filesystem paths."""

    reader_type = f"{type(reader).__module__}.{type(reader).__qualname__}"
    children = getattr(reader, "_readers", None)
    if children is not None:
        return {
            "type": reader_type,
            "generation": getattr(reader, "_generation", None),
            "readers": [_reader_resource_identity(child) for child in children],
        }

    source_identity = getattr(reader, "_source_identity", None)
    kernel_identity = getattr(reader, "_kernel_identity", None)
    if source_identity is not None or kernel_identity is not None:
        return {
            "type": reader_type,
            "source": _canonical_value(source_identity),
            "kernel": _canonical_value(kernel_identity),
        }

    # Test doubles and non-SPK readers have no content receipt. Object identity
    # is safe for this process-local cache and prevents cross-engine reuse.
    return {"type": reader_type, "object_id": id(reader)}


def engine_resource_identity(engine: Any) -> dict[str, Any]:
    """Return the engine/resource component of an expensive-response key."""

    reader = getattr(engine, "_reader_obj", None)
    if reader is None:
        return {
            "engine_type": f"{type(engine).__module__}.{type(engine).__qualname__}",
            "engine_object_id": id(engine),
        }
    return {
        "engine_type": f"{type(engine).__module__}.{type(engine).__qualname__}",
        "reader": _reader_resource_identity(reader),
    }


class ResponseLRUCache:
    """Thread-safe bounded LRU with per-key duplicate-work coalescing."""

    def __init__(self, maxsize: int) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be at least 1")
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._maxsize = maxsize
        self._lock = RLock()
        self._inflight: dict[str, _InFlight] = {}
        self.hits = 0
        self.misses = 0
        self.waits = 0

    def get(self, key: str) -> Any | None:
        """Return the cached value or ``None`` on a miss."""

        with self._lock:
            if key not in self._store:
                self.misses += 1
                return None
            self._store.move_to_end(key)
            self.hits += 1
            return self._store[key]

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key*, evicting the least-recently-used entry."""

        with self._lock:
            self._set_locked(key, value)

    def get_or_compute(self, key: str, factory: Callable[[], _T]) -> _T:
        """Return a hit or compute one successful value per key at a time.

        Concurrent callers for the same key wait for the owner calculation and
        then consume its cached result. If the owner raises, the event is
        released without storing a value; a later request therefore retries.
        """

        while True:
            with self._lock:
                if key in self._store:
                    self._store.move_to_end(key)
                    self.hits += 1
                    return self._store[key]
                flight = self._inflight.get(key)
                if flight is None:
                    flight = _InFlight(event=Event())
                    self._inflight[key] = flight
                    self.misses += 1
                    owner = True
                else:
                    self.waits += 1
                    owner = False

            if owner:
                try:
                    value = factory()
                except BaseException as exc:
                    with self._lock:
                        flight.error = exc
                        self._inflight.pop(key, None)
                        flight.event.set()
                    raise
                with self._lock:
                    self._set_locked(key, value)
                    self._inflight.pop(key, None)
                    flight.event.set()
                return value

            flight.event.wait()
            if flight.error is not None:
                raise flight.error

    def clear(self) -> None:
        """Evict completed entries and reset counters."""

        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0
            self.waits = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def _set_locked(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    @staticmethod
    def make_request_key(
        namespace: str,
        request: Any,
        *,
        engine: Any,
    ) -> str:
        """Hash route, validated input, version, and active resource identity."""

        if hasattr(request, "model_dump"):
            request_payload = request.model_dump(mode="python")
        else:
            request_payload = request
        request_type = f"{type(request).__module__}.{type(request).__qualname__}"
        payload = {
            "cache_key_version": _CACHE_KEY_VERSION,
            "namespace": namespace,
            "engine_version": MOIRA_ENGINE_VERSION,
            "engine_resource": engine_resource_identity(engine),
            "request_type": request_type,
            "request": _canonical_value(request_payload),
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return f"{namespace}:{sha256(encoded).hexdigest()}"


class ChartLRUCache(ResponseLRUCache):
    """Backward-compatible chart cache with its established key contract."""

    def __init__(self, maxsize: int = _DEFAULT_CHART_MAX_SIZE) -> None:
        super().__init__(maxsize=maxsize)

    @staticmethod
    def make_chart_key(
        dt_iso: str,
        bodies: list[str] | None,
        include_nodes: bool,
        observer_lat: float | None,
        observer_lon: float | None,
        observer_elev_m: float,
    ) -> str:
        bodies_part = ",".join(sorted(bodies)) if bodies is not None else "__all__"
        lat_part = f"{observer_lat:.4f}" if observer_lat is not None else "none"
        lon_part = f"{observer_lon:.4f}" if observer_lon is not None else "none"
        elev_part = str(round(observer_elev_m))
        return f"{dt_iso}|{bodies_part}|{include_nodes}|{lat_part}|{lon_part}|{elev_part}"


def cached_response(
    cache: ResponseLRUCache | None,
    namespace: str,
    request: Any,
    engine: Any,
    factory: Callable[[], _T],
) -> _T:
    """Execute one response factory through the optional application cache."""

    if cache is None:
        return factory()
    key = cache.make_request_key(namespace, request, engine=engine)
    return cache.get_or_compute(key, factory)


__all__ = [
    "ChartLRUCache",
    "EXPENSIVE_RESPONSE_CACHE_MAX_SIZE",
    "ResponseLRUCache",
    "cached_response",
    "engine_resource_identity",
]
