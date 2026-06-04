"""Deterministic LRU response cache for the Moira REST API.

Chart computations are pure functions of their inputs: the same datetime,
bodies, and observer always produce identical results.  Caching the
serialised response avoids redundant engine calls for repeated requests
(e.g. a user refreshing the chart calculator page, or the same birth date
appearing in multiple synastry requests).

Design notes
------------
- The cache is stored on ``app.state.chart_cache`` as a plain ``dict``
  acting as an ordered LRU store.  Using ``functools.lru_cache`` directly
  on service functions would couple the cache lifetime to the module rather
  than the application instance, which complicates testing.
- Keys are built from the normalised, timezone-aware ISO-8601 datetime plus
  the sorted body list, include_nodes flag, and rounded observer coordinates.
  Observer elevation is rounded to the nearest metre to avoid float noise.
- The cache is intentionally *not* thread-safe beyond CPython's GIL.  Uvicorn
  runs in a single-threaded async event loop by default; if workers > 1 are
  ever used, each worker gets its own in-process cache which is still correct
  (just not shared).
- Maximum size defaults to 512 entries (~2–4 MB of serialised JSON).  Each
  entry is a Pydantic model that holds ~4–8 KB of chart data.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any


_DEFAULT_MAX_SIZE = 512


class ChartLRUCache:
    """A simple bounded LRU cache backed by an ``OrderedDict``."""

    def __init__(self, maxsize: int = _DEFAULT_MAX_SIZE) -> None:
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._maxsize = maxsize
        self.hits = 0
        self.misses = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Return the cached value or ``None`` on a miss."""
        if key not in self._store:
            self.misses += 1
            return None
        # Move to end (most-recently-used position).
        self._store.move_to_end(key)
        self.hits += 1
        return self._store[key]

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key*, evicting the LRU entry if full."""
        if key in self._store:
            self._store.move_to_end(key)
            self._store[key] = value
            return
        self._store[key] = value
        if len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    def clear(self) -> None:
        """Evict all entries (useful in tests)."""
        self._store.clear()
        self.hits = 0
        self.misses = 0

    def __len__(self) -> int:
        return len(self._store)

    # ------------------------------------------------------------------
    # Cache-key helpers
    # ------------------------------------------------------------------

    @staticmethod
    def make_chart_key(
        dt_iso: str,
        bodies: list[str] | None,
        include_nodes: bool,
        observer_lat: float | None,
        observer_lon: float | None,
        observer_elev_m: float,
    ) -> str:
        """Build a stable, collision-resistant cache key for a chart request.

        The key is a pipe-delimited string; no hashing is needed because the
        components are already compact and deterministic.
        """
        bodies_part = ",".join(sorted(bodies)) if bodies is not None else "__all__"
        lat_part = f"{observer_lat:.4f}" if observer_lat is not None else "none"
        lon_part = f"{observer_lon:.4f}" if observer_lon is not None else "none"
        elev_part = str(round(observer_elev_m))
        return f"{dt_iso}|{bodies_part}|{include_nodes}|{lat_part}|{lon_part}|{elev_part}"
