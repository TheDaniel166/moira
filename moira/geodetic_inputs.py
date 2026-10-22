"""Explicit, immutable body inputs shared by Geodetic analysis.

Engine positions use the canonical geocentric apparent ecliptic provider.
Manual positions require a declared frame; they do not acquire an ephemeris.
Available provenance is retained without inventing per-body reduction receipts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections.abc import Mapping, Sequence

from .geodetic import _circular_delta, _normalize_angle
from .small_body_identity import SmallBodyIdentity, resolve_small_body_identity

__all__ = [
    "GeodeticBodyPosition", "GeodeticBodyFailure", "GeodeticBodySnapshot",
    "geodetic_snapshot_from_positions", "geodetic_snapshot_from_chart",
    "geodetic_snapshot_at",
]

_ENGINE_FRAME = "geocentric_true_ecliptic_and_equinox_of_date"
_ENGINE_CORRECTIONS = "canonical_planet_at_apparent_default"


def _label(value, name):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a nonempty trimmed string")
    return value


def _zodiac_offset(zodiac, ayanamsa_deg):
    if zodiac not in ("tropical", "sidereal"):
        raise ValueError("zodiac must be tropical or sidereal")
    if zodiac == "sidereal" and ayanamsa_deg is None:
        raise ValueError("sidereal inputs require an explicit reference ayanamsa_deg")
    offset = 0.0 if ayanamsa_deg is None else float(ayanamsa_deg)
    if not math.isfinite(offset) or (zodiac == "tropical" and offset != 0.0):
        raise ValueError("ayanamsa must be finite; tropical inputs require zero")
    return offset


def _body_identity(name):
    from .constants import Body
    _label(name, "body")
    identity = resolve_small_body_identity(name)
    major = next((body for body in Body.ALL_PLANETS if body.casefold() == name.casefold()), None)
    return (identity.qualified_name if identity else major or name), identity


@dataclass(frozen=True, slots=True)
class GeodeticBodyPosition:
    """One stable identity and its source and selected-zodiac longitudes."""

    body_id: str
    requested_name: str
    display_name: str
    tropical_longitude_deg: float
    selected_longitude_deg: float
    identity: SmallBodyIdentity | None = None
    ecliptic_latitude_deg: float | None = None
    speed_deg_per_day: float | None = None

    def __post_init__(self):
        for name in ("body_id", "requested_name", "display_name"):
            _label(getattr(self, name), name)
        for name in ("tropical_longitude_deg", "selected_longitude_deg"):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value < 360.0:
                raise ValueError(f"{name} must be in [0, 360)")
        for name in ("ecliptic_latitude_deg", "speed_deg_per_day"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite when known")
        if self.ecliptic_latitude_deg is not None and abs(self.ecliptic_latitude_deg) > 90:
            raise ValueError("ecliptic latitude must be in [-90, 90]")
        if self.identity is not None:
            if not isinstance(self.identity, SmallBodyIdentity):
                raise TypeError("identity must be SmallBodyIdentity")
            if self.body_id != self.identity.qualified_name:
                raise ValueError("body_id must match canonical qualified identity")


@dataclass(frozen=True, slots=True)
class GeodeticBodyFailure:
    """A requested body that could not be calculated under collecting policy."""

    requested_name: str
    body_id: str
    failure_type: str
    reason: str


@dataclass(frozen=True, slots=True)
class GeodeticBodySnapshot:
    """Ordered positions, explicit coordinate provenance and any failures.

    Missing resource receipts are explicitly unknown, rather than inferred
    from a catalog's nominal dates. Engine timing separately admits coverage.
    """

    positions: tuple[GeodeticBodyPosition, ...]
    source_kind: str
    source_frame: str
    correction_regime: str
    zodiac: str = "tropical"
    ayanamsa_deg: float = 0.0
    ayanamsa_system: str | None = None
    jd_ut1: float | None = None
    jd_tt: float | None = None
    failures: tuple[GeodeticBodyFailure, ...] = ()
    resource_receipt_status: str = "not_exposed_by_source"

    def __post_init__(self):
        if not isinstance(self.positions, tuple) or any(not isinstance(p, GeodeticBodyPosition) for p in self.positions):
            raise TypeError("positions must be a tuple of GeodeticBodyPosition")
        if not isinstance(self.failures, tuple) or any(not isinstance(p, GeodeticBodyFailure) for p in self.failures):
            raise TypeError("failures must be a tuple of GeodeticBodyFailure")
        ids = [p.body_id for p in self.positions] + [p.body_id for p in self.failures]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate canonical body identities")
        if self.source_kind not in ("supplied_positions", "chart_context", "engine"):
            raise ValueError("unsupported snapshot source_kind")
        _label(self.source_frame, "source_frame")
        _label(self.correction_regime, "correction_regime")
        _zodiac_offset(self.zodiac, self.ayanamsa_deg)
        if self.ayanamsa_system is not None:
            _label(self.ayanamsa_system, "ayanamsa_system")
            if self.zodiac != "sidereal":
                raise ValueError("tropical snapshot cannot name an ayanamsa system")
        for name in ("jd_ut1", "jd_tt"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.source_kind != "supplied_positions" and (self.jd_ut1 is None or self.jd_tt is None):
            raise ValueError("calculated snapshots require UT1 and TT epochs")
        for position in self.positions:
            expected = _normalize_angle(position.tropical_longitude_deg - self.ayanamsa_deg)
            if abs(_circular_delta(position.selected_longitude_deg, expected)) > 1e-10:
                raise ValueError("position disagrees with snapshot zodiac offset")

    @property
    def complete(self):
        """Whether every explicitly requested body was calculated."""
        return not self.failures

    @property
    def longitudes(self):
        """Return a fresh selected-zodiac mapping, safe to mutate by callers."""
        return {p.body_id: p.selected_longitude_deg for p in self.positions}


def _requests(bodies):
    if isinstance(bodies, str) or not isinstance(bodies, Sequence) or not bodies:
        raise ValueError("bodies must be a nonempty explicit sequence of names")
    result = tuple((name, *_body_identity(name)) for name in bodies)
    if len({item[1] for item in result}) != len(result):
        raise ValueError("duplicate canonical body identities")
    return result


def geodetic_snapshot_from_positions(
    positions: Mapping[str, float], *, source_frame: str,
    correction_regime: str = "caller_declared_unspecified", zodiac: str = "tropical",
    ayanamsa_deg: float | None = None, ayanamsa_system: str | None = None,
    jd_ut1: float | None = None, jd_tt: float | None = None,
) -> GeodeticBodySnapshot:
    """Adapt explicit *tropical* longitudes; arbitrary labels stay manual.

    Declared catalog names retain their canonical identity and alias rules.
    Values are normalized, then displaced into the requested zodiac.
    """
    if not isinstance(positions, Mapping) or not positions:
        raise ValueError("positions must be a nonempty mapping")
    offset = _zodiac_offset(zodiac, ayanamsa_deg)
    records = []
    for name, body_id, identity in _requests(tuple(positions)):
        lon = _normalize_angle(positions[name])
        records.append(GeodeticBodyPosition(body_id, name, identity.canonical_name if identity else name,
                                          lon, _normalize_angle(lon - offset), identity))
    return GeodeticBodySnapshot(tuple(records), "supplied_positions", source_frame, correction_regime,
                               zodiac, offset, ayanamsa_system, jd_ut1, jd_tt)


def geodetic_snapshot_from_chart(
    chart, bodies: Sequence[str] | None = None, *, zodiac: str = "tropical",
    ayanamsa_deg: float | None = None, ayanamsa_system: str | None = None,
) -> GeodeticBodySnapshot:
    """Adapt existing geocentric ChartContext positions without recalculation.

    ChartContext does not preserve every frame/reduction receipt. This adapter
    declares that limitation and refuses known topocentric entries.
    """
    from .chart import ChartContext
    if not isinstance(chart, ChartContext):
        raise TypeError("chart must be ChartContext")
    offset = _zodiac_offset(zodiac, ayanamsa_deg)
    records = []
    available = {}
    for key, value in chart.planets.items():
        body_id, _ = _body_identity(key)
        if body_id in available:
            raise ValueError("chart contains duplicate canonical body identities")
        available[body_id] = value
    for name, body_id, identity in _requests(tuple(chart.planets) if bodies is None else bodies):
        value = available[body_id]
        if value.is_topocentric:
            raise ValueError("Geodetic chart adapter requires geocentric positions")
        lon = _normalize_angle(value.longitude)
        records.append(GeodeticBodyPosition(body_id, name, identity.canonical_name if identity else name,
                                          lon, _normalize_angle(lon - offset), identity, value.latitude, value.speed))
    return GeodeticBodySnapshot(tuple(records), "chart_context", _ENGINE_FRAME,
                               "chart_context_not_fully_receipted", zodiac, offset, ayanamsa_system,
                               chart.jd_ut, chart.jd_tt)


def geodetic_snapshot_at(
    jd_ut1: float, bodies: Sequence[str], *, reader=None, zodiac: str = "tropical",
    ayanamsa_deg: float | None = None, ayanamsa_system: str | None = None,
    error_policy: str = "raise",
) -> GeodeticBodySnapshot:
    """Calculate only selected bodies using canonical planet_at reductions.

    Qualified asteroid/comet names are admitted by the shared identity
    resolver. No downloads, extrapolation, substitutions, or silent omissions.
    """
    from ._ephemeris_time import _ut1_to_ephemeris_tt
    from .planets import planet_at
    from .spk_reader import get_reader
    if not math.isfinite(jd_ut1):
        raise ValueError("jd_ut1 must be finite")
    if error_policy not in ("raise", "collect"):
        raise ValueError("error_policy must be raise or collect")
    requests = _requests(bodies)
    offset = _zodiac_offset(zodiac, ayanamsa_deg)
    if reader is None:
        reader = get_reader()
    jd_tt = _ut1_to_ephemeris_tt(jd_ut1, reader)
    records, failures = [], []
    for name, body_id, identity in requests:
        try:
            value = planet_at(body_id, jd_ut1, reader=reader)
            lon = _normalize_angle(value.longitude)
            records.append(GeodeticBodyPosition(body_id, name, identity.canonical_name if identity else name,
                                              lon, _normalize_angle(lon - offset), identity,
                                              value.latitude, value.speed))
        except (ValueError, KeyError, RuntimeError, OSError) as exc:
            if error_policy == "raise":
                raise
            failures.append(GeodeticBodyFailure(name, body_id, type(exc).__name__, str(exc)))
    return GeodeticBodySnapshot(tuple(records), "engine", _ENGINE_FRAME, _ENGINE_CORRECTIONS,
                               zodiac, offset, ayanamsa_system, jd_ut1, jd_tt, tuple(failures))
