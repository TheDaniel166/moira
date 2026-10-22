"""
Moira — Geodetic Astrology Engine
==================================

Archetype: Engine

Purpose
-------
Governs computation of Geodetic Astrology — the direct mapping of the
tropical (or sidereal) zodiac onto geographic longitude.  Every location
on Earth carries a native Geodetic MC and a derived Geodetic Ascendant
without requiring a birth time.

The foundational mapping (Sepharial / Johndro tradition):

    Geodetic MC (tropical) = geographic longitude (°E, 0–360)

    Geographic latitude is taken as supplied in signed decimal degrees and is
    passed unchanged into the Ascendant geometry. No datum or geodetic-to-
    geocentric/astronomical latitude conversion is inferred.

    0° Aries (tropical) ≡ 0° geographic longitude (Greenwich meridian)
    30° Aries           ≡ 30° E
    0° Taurus           ≡ 30° E
    …and so on eastward through the full 360°

The Geodetic Ascendant is the ecliptic degree rising on the eastern
horizon at the given latitude for the Geodetic MC, computed via the
standard hour-angle / ARMC formula.

Both tropical and sidereal paths are supported:

  tropical — Geodetic MC = geographic longitude (mod 360)
  sidereal — Geodetic MC = (geographic longitude − ayanamsa) mod 360
             expressed in the chosen sidereal zodiac.  The inverse
             (geodetic equivalents) adds the ayanamsa back.

Boundary declaration
--------------------
Owns: Geodetic MC derivation, Geodetic chart vessel (``GeodeticChart``),
      geodetic equivalents map, and the tropical/sidereal ayanamsa lane policy.
Delegates: the Ascendant branch selection and circular normalization to
      ``moira._angles``, shared with ``moira.houses``; obliquity at a Julian
      Day to ``moira.obliquity``; ayanamsa to ``moira.sidereal``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  Caller supplies
either raw geographic coordinates + obliquity, or a ``ChartContext``
for the convenience wrappers.

Public surface
--------------
``GeodeticChart``               — vessel for a single geodetic chart.
``geodetic_mc``                 — Geodetic MC from geographic longitude.
``geodetic_asc``                — Geodetic ASC from location + obliquity.
``geodetic_chart``              — full GeodeticChart from coordinates.
``geodetic_chart_from_chart``   — convenience wrapper for a ChartContext.
``geodetic_equivalents``        — geographic longitudes native to each planet.
``geodetic_equivalents_from_chart`` — equivalents directly from a ChartContext.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

from .constants import DEG2RAD, RAD2DEG
from .geoutils import wrap_longitude_deg
from ._angles import _asc_from_armc  # noqa: F401 - canonical doctrine lives in moira._angles

__all__ = [
    "GeodeticAngleDerivatives",
    "GeodeticChart",
    "GeodeticChartProvenance",
    "GeodeticEquivalentPosition",
    "GeodeticEquivalentsProvenance",
    "GeodeticEquivalentsResult",
    "GeodeticInputUncertainty",
    "GeodeticLatitudeKind",
    "GeodeticLocation",
    "GeodeticSensitivityResult",
    "geodetic_mc",
    "geodetic_asc",
    "geodetic_chart",
    "geodetic_chart_at_location",
    "geodetic_chart_from_chart",
    "geodetic_equivalents",
    "geodetic_equivalents_from_chart",
    "geodetic_equivalents_result_from_chart",
    "geodetic_chart_sensitivity",
]


# ---------------------------------------------------------------------------
# Data vessel
# ---------------------------------------------------------------------------

_GEODETIC_LATITUDE_CONVENTION = "caller_supplied_geographic_latitude_no_conversion"
_EARTH_OBLIQUITY_MIN_DEG = 22.0
_EARTH_OBLIQUITY_MAX_DEG = 25.0
_EQUIVALENTS_CALCULATION_POLICY = "geodetic_mc_inverse_v1"
_CHART_LONGITUDE_FRAME = "chart_context_tropical_ecliptic_longitude"

GeodeticLatitudeKind = Literal["unspecified", "geodetic", "astronomical", "geocentric"]


@dataclass(slots=True, frozen=True)
class GeodeticLocation:
    """Coordinates and optional source metadata for a terrestrial location.

    The engine does not transform coordinates. ``latitude_kind`` records what
    the caller supplied; the conventional Geodetic calculation uses that
    numeric latitude unchanged. Geocentric latitude is retained as metadata
    but is refused by ``geodetic_chart_at_location`` until an explicit
    conversion is implemented and selected.

    ``coordinate_epoch`` is a decimal year. Height is ellipsoidal metres and
    therefore requires the caller to identify the reference datum or frame.
    """

    latitude_deg: float
    longitude_deg: float
    latitude_kind: GeodeticLatitudeKind = "unspecified"
    datum: str | None = None
    reference_frame: str | None = None
    coordinate_epoch: float | None = None
    ellipsoidal_height_m: float | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        _validate_finite("latitude_deg", self.latitude_deg)
        _validate_finite("longitude_deg", self.longitude_deg)
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("latitude_deg must be in [-90, 90]")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("longitude_deg must be in [-180, 180]")
        if self.latitude_kind not in ("unspecified", "geodetic", "astronomical", "geocentric"):
            raise ValueError(
                "latitude_kind must be 'unspecified', 'geodetic', 'astronomical', or 'geocentric'"
            )
        for name in ("datum", "reference_frame", "source"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be a non-empty string when supplied")
        if self.coordinate_epoch is not None:
            _validate_finite("coordinate_epoch", self.coordinate_epoch)
        if self.ellipsoidal_height_m is not None:
            _validate_finite("ellipsoidal_height_m", self.ellipsoidal_height_m)
            if self.datum is None and self.reference_frame is None:
                raise ValueError(
                    "ellipsoidal_height_m requires an explicit datum or reference_frame"
                )


@dataclass(slots=True, frozen=True)
class GeodeticInputUncertainty:
    """Caller-supplied maximum absolute input deviations, in degrees."""

    longitude_deg: float = 0.0
    latitude_deg: float = 0.0
    obliquity_deg: float = 0.0

    def __post_init__(self) -> None:
        for name in ("longitude_deg", "latitude_deg", "obliquity_deg"):
            value = getattr(self, name)
            _validate_finite(name, value)
            if value < 0.0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(slots=True, frozen=True)
class GeodeticEquivalentPosition:
    """One chart body's source, selected-zodiac, and geographic longitudes."""

    body: str
    source_tropical_longitude_deg: float
    selected_zodiac_longitude_deg: float
    geographic_longitude_deg: float

    def __post_init__(self) -> None:
        if not isinstance(self.body, str) or not self.body.strip():
            raise ValueError("body must be a non-empty string")
        for name in (
            "source_tropical_longitude_deg",
            "selected_zodiac_longitude_deg",
            "geographic_longitude_deg",
        ):
            _validate_finite(name, getattr(self, name))
        for name in ("source_tropical_longitude_deg", "selected_zodiac_longitude_deg"):
            value = getattr(self, name)
            if not 0.0 <= value < 360.0:
                raise ValueError(f"{name} must be in [0, 360)")
        if not -180.0 <= self.geographic_longitude_deg <= 180.0:
            raise ValueError("geographic_longitude_deg must be in [-180, 180]")


@dataclass(slots=True, frozen=True)
class GeodeticEquivalentsProvenance:
    """Chart epoch and policy used for a detailed equivalents result."""

    chart_jd_ut: float
    chart_jd_tt: float
    calculation_source: Literal["chart_context"] = "chart_context"
    zodiac: Literal["tropical", "sidereal"] = "tropical"
    ayanamsa_deg: float = 0.0
    ayanamsa_system: str | None = None
    ayanamsa_timescale: Literal["UT"] | None = None
    source_longitude_frame: Literal[
        "chart_context_tropical_ecliptic_longitude"
    ] = _CHART_LONGITUDE_FRAME
    calculation_policy: Literal["geodetic_mc_inverse_v1"] = _EQUIVALENTS_CALCULATION_POLICY

    def __post_init__(self) -> None:
        if self.calculation_source != "chart_context":
            raise ValueError("equivalents provenance must come from chart_context")
        _validate_finite("chart_jd_ut", self.chart_jd_ut)
        _validate_finite("chart_jd_tt", self.chart_jd_tt)
        _validate_finite("ayanamsa_deg", self.ayanamsa_deg)
        if self.zodiac not in ("tropical", "sidereal"):
            raise ValueError("zodiac must be 'tropical' or 'sidereal'")
        if self.source_longitude_frame != _CHART_LONGITUDE_FRAME:
            raise ValueError("unsupported source longitude frame")
        if self.calculation_policy != _EQUIVALENTS_CALCULATION_POLICY:
            raise ValueError("unsupported equivalents calculation policy")
        if self.zodiac == "tropical":
            if self.ayanamsa_deg != 0.0 or self.ayanamsa_system is not None:
                raise ValueError("tropical equivalents provenance cannot carry an ayanamsa")
            if self.ayanamsa_timescale is not None:
                raise ValueError("tropical equivalents provenance cannot carry an ayanamsa timescale")
        else:
            if not isinstance(self.ayanamsa_system, str) or not self.ayanamsa_system.strip():
                raise ValueError("sidereal equivalents provenance requires ayanamsa_system")
            if self.ayanamsa_timescale != "UT":
                raise ValueError("sidereal equivalents provenance must name UT")


@dataclass(slots=True, frozen=True)
class GeodeticEquivalentsResult:
    """Immutable, ordered equivalent positions plus the calculation receipt."""

    positions: tuple[GeodeticEquivalentPosition, ...]
    provenance: GeodeticEquivalentsProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, GeodeticEquivalentsProvenance):
            raise TypeError("provenance must be GeodeticEquivalentsProvenance")
        if not isinstance(self.positions, tuple) or any(
            not isinstance(item, GeodeticEquivalentPosition) for item in self.positions
        ):
            raise TypeError("positions must be a tuple of GeodeticEquivalentPosition")
        bodies = [item.body for item in self.positions]
        if len(bodies) != len(set(bodies)):
            raise ValueError("equivalent position body names must be unique")

    @property
    def geographic_longitudes(self) -> dict[str, float]:
        """Return a fresh compatibility mapping of body to geographic longitude."""
        return {item.body: item.geographic_longitude_deg for item in self.positions}


@dataclass(slots=True, frozen=True)
class GeodeticAngleDerivatives:
    """Local output-angle derivatives per degree of each input quantity."""

    geo_longitude_deg: float
    geo_latitude_deg: float
    obliquity_deg: float

    def __post_init__(self) -> None:
        for name in ("geo_longitude_deg", "geo_latitude_deg", "obliquity_deg"):
            _validate_finite(name, getattr(self, name))


@dataclass(slots=True, frozen=True)
class GeodeticSensitivityResult:
    """First-order local sensitivity estimates; these are not error bounds."""

    base_chart: GeodeticChart
    uncertainty: GeodeticInputUncertainty
    mc_derivatives: GeodeticAngleDerivatives
    asc_derivatives: GeodeticAngleDerivatives
    mc_linearized_radius_deg: float
    asc_linearized_radius_deg: float
    latitude_margin_to_pole_deg: float
    interpretation: Literal["first_order_local_not_a_bound"] = "first_order_local_not_a_bound"

    def __post_init__(self) -> None:
        if not isinstance(self.base_chart, GeodeticChart):
            raise TypeError("base_chart must be a GeodeticChart")
        if not isinstance(self.uncertainty, GeodeticInputUncertainty):
            raise TypeError("uncertainty must be GeodeticInputUncertainty")
        if not isinstance(self.mc_derivatives, GeodeticAngleDerivatives):
            raise TypeError("mc_derivatives must be GeodeticAngleDerivatives")
        if not isinstance(self.asc_derivatives, GeodeticAngleDerivatives):
            raise TypeError("asc_derivatives must be GeodeticAngleDerivatives")
        for name in ("mc_linearized_radius_deg", "asc_linearized_radius_deg", "latitude_margin_to_pole_deg"):
            value = getattr(self, name)
            _validate_finite(name, value)
            if value < 0.0:
                raise ValueError(f"{name} must be non-negative")
        if self.interpretation != "first_order_local_not_a_bound":
            raise ValueError("unsupported sensitivity interpretation")


@dataclass(slots=True, frozen=True)
class GeodeticChartProvenance:
    """Calculation provenance retained by a ``GeodeticChart`` result.

    Direct calculations retain their caller-supplied coordinates and numeric
    parameters on ``GeodeticChart`` itself. Chart-backed calculations also
    preserve the exact chart epochs and astronomy model identities used by the
    wrapper. Latitude is passed through unchanged; no datum or conversion is
    inferred from the numeric value.
    """

    calculation_source: Literal["direct_inputs", "chart_context"] = "direct_inputs"
    latitude_convention: Literal[
        "caller_supplied_geographic_latitude_no_conversion"
    ] = _GEODETIC_LATITUDE_CONVENTION
    chart_jd_ut: float | None = None
    chart_jd_tt: float | None = None
    obliquity_timescale: Literal["TT"] | None = None
    mean_obliquity_model: str | None = None
    nutation_model: str | None = None
    ayanamsa_system: str | None = None
    ayanamsa_timescale: Literal["UT"] | None = None
    location: GeodeticLocation | None = None

    def __post_init__(self) -> None:
        if self.calculation_source not in ("direct_inputs", "chart_context"):
            raise ValueError(
                "calculation_source must be 'direct_inputs' or 'chart_context'"
            )
        if self.latitude_convention != _GEODETIC_LATITUDE_CONVENTION:
            raise ValueError("unsupported geodetic latitude convention")
        for name in ("chart_jd_ut", "chart_jd_tt"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite when supplied")

        if self.calculation_source == "direct_inputs":
            chart_fields = (
                self.chart_jd_ut,
                self.chart_jd_tt,
                self.obliquity_timescale,
                self.mean_obliquity_model,
                self.nutation_model,
                self.ayanamsa_system,
                self.ayanamsa_timescale,
            )
            if any(value is not None for value in chart_fields):
                raise ValueError(
                    "direct-input provenance cannot claim chart-derived epochs or models"
                )
            if self.location is not None and not isinstance(self.location, GeodeticLocation):
                raise TypeError("location must be a GeodeticLocation or None")
            if self.location is not None and self.location.latitude_kind == "geocentric":
                raise ValueError("geocentric latitude requires an explicit conversion")
            return

        if self.chart_jd_ut is None or self.chart_jd_tt is None:
            raise ValueError("chart-context provenance requires both chart Julian Days")
        if self.obliquity_timescale != "TT":
            raise ValueError("chart-context obliquity provenance must name TT")
        if not self.mean_obliquity_model or not self.nutation_model:
            raise ValueError("chart-context provenance requires obliquity model identities")
        if (self.ayanamsa_system is None) != (self.ayanamsa_timescale is None):
            raise ValueError("ayanamsa system and timescale provenance must be supplied together")
        if self.ayanamsa_system is not None and not self.ayanamsa_system.strip():
            raise ValueError("ayanamsa_system must be non-empty when supplied")
        if self.ayanamsa_timescale not in (None, "UT"):
            raise ValueError("chart-context ayanamsa provenance must name UT")
        if self.location is not None and not isinstance(self.location, GeodeticLocation):
            raise TypeError("location must be a GeodeticLocation or None")


@dataclass(slots=True, frozen=True)
class GeodeticChart:
    """
    RITE: The Location-Native Chart — a place's inherent zodiacal identity.

    THEOREM: Holds the Geodetic MC, Geodetic Ascendant, and the derivation
    parameters for a single geographic location.  No birth time is required
    or stored.

    RITE OF PURPOSE:
        Serves the Geodetic Engine as the canonical result vessel.  Without
        this vessel callers would have no structured representation of the
        location-native angles needed for relocation analysis, mundane
        astrology, or overlay against natal charts.

    LAW OF OPERATION:
        Responsibilities:
            - Store the geographic coordinates, Geodetic MC, Geodetic ASC,
              obliquity used, zodiac path, applied ayanamsa, and calculation
              provenance when it is available.
        Non-responsibilities:
            - Does not compute angles (delegated to ``geodetic_chart``).
            - Does not render or project onto a map.
            - Does not infer a coordinate datum or convert latitude conventions.
        Structural invariants:
            - ``mc`` and ``asc`` are always in [0°, 360°).
            - ``zodiac`` and ``ayanamsa_deg`` agree: a tropical vessel always
              carries exactly 0.0, because the tropical lane has no displacement.
            - ``zodiac`` is either "tropical" or "sidereal".
            - Geographic latitude is caller-supplied and passed through without
              geodetic/geocentric conversion.
            - Earth obliquity is finite and lies in [22°, 25°], a guarded
              envelope around the established long-term terrestrial range.
        Succession stance: terminal.

    Canon: Sepharial, "The World Horoscope" (1910);
           Johndro, "The Stars: How and Where They Influence" (1929);
           Meeus, "Astronomical Algorithms" Ch. 13.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.geodetic.GeodeticChart",
        "risk": "low",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "geo_latitude", "geo_longitude", "mc", "asc",
                "obliquity", "zodiac", "ayanamsa_deg", "provenance"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "geo_latitude", "geo_longitude", "mc", "asc",
                "obliquity", "zodiac", "ayanamsa_deg", "provenance"
            ]
        },
        "effects": {"io": [], "signals_emitted": [], "db_writes": []},
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError"],
            "policy": "construction enforces coordinate, angle, zodiac, and provenance invariants"
        },
        "succession": {"stance": "terminal", "override_points": []},
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    geo_latitude:  float  # Observer latitude  (degrees, −90 to +90)
    geo_longitude: float  # Observer longitude (degrees, −180 to +180)
    mc:            float  # Geodetic MC (degrees, 0–360, tropical or sidereal)
    asc:           float  # Geodetic Ascendant (degrees, 0–360)
    obliquity:     float  # True obliquity of the ecliptic used (degrees)
    zodiac:        str    # "tropical" or "sidereal"
    ayanamsa_deg:  float  # Ayanamsa applied; 0.0 for tropical
    provenance:    GeodeticChartProvenance | None = None

    def __post_init__(self) -> None:
        _validate_geodetic_inputs(
            self.geo_longitude,
            self.geo_latitude,
            self.obliquity,
            self.ayanamsa_deg,
        )
        _validate_zodiac(self.zodiac)
        _validate_zodiac_policy(self.zodiac, ayanamsa_deg=self.ayanamsa_deg)
        for name, value in (("mc", self.mc), ("asc", self.asc)):
            _validate_finite(name, value)
            if not 0.0 <= value < 360.0:
                raise ValueError(f"{name} must be in [0, 360), got {value!r}")
        if not -180.0 <= self.geo_longitude <= 180.0:
            raise ValueError(
                "stored geo_longitude must be wrapped to [-180, 180], "
                f"got {self.geo_longitude!r}"
            )
        if self.provenance is not None:
            if not isinstance(self.provenance, GeodeticChartProvenance):
                raise TypeError("provenance must be a GeodeticChartProvenance or None")
            if self.provenance.calculation_source == "chart_context":
                if self.zodiac == "sidereal" and self.provenance.ayanamsa_system is None:
                    raise ValueError(
                        "sidereal chart-context provenance requires ayanamsa_system"
                    )
                if self.zodiac == "tropical" and self.provenance.ayanamsa_system is not None:
                    raise ValueError(
                        "tropical chart-context provenance must not carry ayanamsa_system"
                    )
            if self.provenance.location is not None:
                location = self.provenance.location
                if location.latitude_kind == "geocentric":
                    raise ValueError("geocentric latitude requires an explicit conversion")
                if location.latitude_deg != self.geo_latitude:
                    raise ValueError("provenance location latitude must match geo_latitude")
                if wrap_longitude_deg(location.longitude_deg) != self.geo_longitude:
                    raise ValueError("provenance location longitude must match geo_longitude")

    def __repr__(self) -> str:
        return (
            f"GeodeticChart("
            f"lat={self.geo_latitude:.4f}°, "
            f"lon={self.geo_longitude:.4f}°, "
            f"MC={self.mc:.4f}°, "
            f"ASC={self.asc:.4f}°, "
            f"zodiac={self.zodiac!r})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _armc_from_mc(mc_deg: float, obliquity: float) -> float:
    """
    Convert ecliptic MC longitude to ARMC (Right Ascension of the MC).

    The MC is the ecliptic degree culminating on the upper meridian.  Its
    ARMC is the RA of that ecliptic degree at zero ecliptic latitude:

        ARMC = atan2(sin(λ_MC) · cos(ε),  cos(λ_MC))

    This is the standard ecliptic-to-equatorial RA formula restricted to
    ecliptic latitude = 0.  Meeus, "Astronomical Algorithms" Ch. 13.
    """
    l_r   = mc_deg    * DEG2RAD
    eps_r = obliquity * DEG2RAD
    return math.atan2(math.sin(l_r) * math.cos(eps_r), math.cos(l_r)) * RAD2DEG % 360.0


def _validate_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


# Same margin as the _POLAR_EPS convention declared in moira.houses: a shared
# numeric stand-in for "this latitude is the pole", not a physical threshold.
_POLAR_REFUSAL_MARGIN_DEG = 1e-6


def _validate_geodetic_inputs(
    geo_longitude: float,
    geo_latitude: float,
    obliquity: float,
    ayanamsa_deg: float,
) -> None:
    _validate_finite("geo_longitude", geo_longitude)
    _validate_finite("geo_latitude", geo_latitude)
    _validate_finite("obliquity", obliquity)
    _validate_finite("ayanamsa_deg", ayanamsa_deg)
    if not _EARTH_OBLIQUITY_MIN_DEG <= obliquity <= _EARTH_OBLIQUITY_MAX_DEG:
        raise ValueError(
            "Earth obliquity must be in [22, 25] degrees, a guarded envelope "
            f"around its terrestrial range, got {obliquity!r}"
        )
    if not -90.0 <= geo_latitude <= 90.0:
        raise ValueError(f"geo_latitude must be in [-90, 90], got {geo_latitude!r}")
    if abs(geo_latitude) > 90.0 - _POLAR_REFUSAL_MARGIN_DEG:
        raise ValueError(
            "geo_latitude is at the geographic pole, where the horizon and the "
            "ecliptic no longer define a rising Ascendant; refuse instead of "
            f"extrapolate, got {geo_latitude!r} "
            f"(limit +/-{90.0 - _POLAR_REFUSAL_MARGIN_DEG})"
        )


def _validate_zodiac(zodiac: str) -> None:
    if zodiac not in ("tropical", "sidereal"):
        raise ValueError(f"zodiac must be 'tropical' or 'sidereal', got {zodiac!r}")


def _validate_zodiac_policy(
    zodiac: str,
    *,
    ayanamsa_deg: float | None = None,
    ayanamsa_system: str | None = None,
) -> None:
    """
    Enforce that the ayanamsa belongs to the sidereal lane alone.

    The tropical lane is the ayanamsa-zero lane: Geodetic MC is geographic
    longitude with no displacement.  An ayanamsa supplied alongside
    ``zodiac="tropical"`` therefore contradicts the declared lane instead of
    being a value to tolerate or quietly drop.

    The opposite requirement — that sidereal output name its displacement — is
    checked where the displacement is resolved, because a sidereal ayanamsa of
    exactly ``0.0`` is a legal (if degenerate) claim that the lanes coincide.
    """
    if zodiac != "tropical":
        return
    if ayanamsa_deg is not None and ayanamsa_deg != 0.0:
        raise ValueError(
            "tropical zodiac must not carry an ayanamsa offset; the tropical "
            f"Geodetic MC is geographic longitude, got ayanamsa_deg={ayanamsa_deg!r}"
        )
    if ayanamsa_system is not None:
        raise ValueError(
            "tropical zodiac must not carry an ayanamsa_system; a named ayanamsa "
            f"belongs to the sidereal lane, got ayanamsa_system={ayanamsa_system!r}"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def geodetic_mc(
    geo_longitude: float,
    ayanamsa_deg: float = 0.0,
) -> float:
    """
    Geodetic MC for a geographic longitude.

    Maps a geographic longitude directly to an ecliptic zodiac degree.

    For the tropical path (``ayanamsa_deg = 0.0``):

        Geodetic MC = geo_longitude (mod 360°)

    For the sidereal path (``ayanamsa_deg > 0``):

        Geodetic MC (sidereal) = (geo_longitude − ayanamsa_deg) mod 360°

    Parameters
    ----------
    geo_longitude : Geographic longitude in decimal degrees.
                    Any value is accepted; the result is wrapped to [0°, 360°).
    ayanamsa_deg  : Ayanamsa in degrees.  Pass 0.0 (default) for tropical.
                    Pass the active ayanamsa for sidereal output.

    Returns
    -------
    float — Geodetic MC in degrees, range [0°, 360°).
    """
    _validate_finite("geo_longitude", geo_longitude)
    _validate_finite("ayanamsa_deg", ayanamsa_deg)
    return (geo_longitude - ayanamsa_deg) % 360.0


def geodetic_asc(
    geo_longitude: float,
    geo_latitude: float,
    obliquity: float,
    ayanamsa_deg: float = 0.0,
) -> float:
    """
    Geodetic Ascendant for a geographic location.

    Derives the ARMC from the tropical Geodetic MC, computes the tropical
    rising horizon intersection, and applies the zodiac displacement only to
    the returned longitude. The physical geographic meridian is independent
    of zodiac.

    Parameters
    ----------
    geo_longitude : Geographic longitude (decimal degrees, any range).
    geo_latitude  : Caller-supplied geographic latitude (decimal degrees,
                    north-positive; passed through without conversion or an
                    inferred datum; strictly inside the poles — see Notes).
    obliquity     : True obliquity of the ecliptic (degrees).
    ayanamsa_deg  : Ayanamsa in degrees. Pass 0.0 (default) for tropical; a
                    sidereal result is the tropical Ascendant minus this value.

    Returns
    -------
    float — Geodetic Ascendant in degrees, range [0°, 360°).

    Notes
    -----
    At a geographic pole the horizon no longer singles out a rising ecliptic
    degree, so latitudes within ``_POLAR_REFUSAL_MARGIN_DEG`` of |90| are
    refused with ``ValueError`` rather than answered with an extrapolation.
    Latitudes just inside that margin are computed, but their Ascendant is a
    mathematical extrapolation, not an observationally meaningful direction.
    """
    _validate_geodetic_inputs(geo_longitude, geo_latitude, obliquity, ayanamsa_deg)
    tropical_mc = geodetic_mc(geo_longitude)
    armc = _armc_from_mc(tropical_mc, obliquity)
    tropical_asc = _asc_from_armc(armc, obliquity, geo_latitude)
    return (tropical_asc - ayanamsa_deg) % 360.0


def geodetic_chart(
    geo_longitude: float,
    geo_latitude:  float,
    obliquity:     float,
    ayanamsa_deg:  float | None = None,
    zodiac:        str   = "tropical",
) -> GeodeticChart:
    """
    Build a full GeodeticChart vessel from geographic coordinates.

    Parameters
    ----------
    geo_longitude : Geographic longitude (decimal degrees, any range;
                    stored wrapped to [−180°, +180°]).
    geo_latitude  : Caller-supplied geographic latitude (decimal degrees,
                    north-positive; passed through without conversion or an
                    inferred datum).
    obliquity     : True obliquity of the ecliptic (degrees).  Use
                    ``moira.obliquity.true_obliquity(jd_tt)`` for epoch-
                    appropriate values.
    ayanamsa_deg  : Ayanamsa in degrees. Omit for tropical (equivalent to
                    ``0.0``); required for sidereal, where an explicit
                    ``0.0`` is valid when the caller declares coincident lanes.
    zodiac        : "tropical" (default) or "sidereal".  Selects the lane and
                    constrains ``ayanamsa_deg``; it is not merely a label on
                    the result.

    Returns
    -------
    GeodeticChart — immutable vessel with MC, ASC, derivation metadata, and
    provenance identifying the direct-input policy.

    Raises
    ------
    ValueError
        If ``zodiac`` is unknown, if a sidereal request omits
        ``ayanamsa_deg``, if Earth obliquity is outside [22°, 25°], or if a
        tropical request carries a nonzero offset.
    """
    _validate_zodiac(zodiac)
    _validate_zodiac_policy(zodiac, ayanamsa_deg=ayanamsa_deg)
    if zodiac == "sidereal" and ayanamsa_deg is None:
        raise ValueError(
            "ayanamsa_deg is required when zodiac='sidereal'. "
            "Pass the sidereal offset explicitly, including 0.0 if intended."
        )
    resolved_ayanamsa = 0.0 if ayanamsa_deg is None else ayanamsa_deg
    _validate_geodetic_inputs(geo_longitude, geo_latitude, obliquity, resolved_ayanamsa)
    mc  = geodetic_mc(geo_longitude, resolved_ayanamsa)
    asc = geodetic_asc(geo_longitude, geo_latitude, obliquity, resolved_ayanamsa)
    return GeodeticChart(
        geo_latitude  = geo_latitude,
        geo_longitude = wrap_longitude_deg(geo_longitude),
        mc            = mc,
        asc           = asc,
        obliquity     = obliquity,
        zodiac        = zodiac,
        ayanamsa_deg  = resolved_ayanamsa,
        provenance    = GeodeticChartProvenance(),
    )


def geodetic_chart_at_location(
    location: GeodeticLocation,
    obliquity: float,
    ayanamsa_deg: float | None = None,
    zodiac: str = "tropical",
) -> GeodeticChart:
    """Build a chart from typed coordinates and retain their source metadata.

    Latitude is passed numerically unchanged for ``unspecified``,
    ``geodetic``, and ``astronomical`` inputs. A geocentric latitude is
    rejected because this module has no declared conversion policy.
    """
    if not isinstance(location, GeodeticLocation):
        raise TypeError("location must be a GeodeticLocation")
    if location.latitude_kind == "geocentric":
        raise ValueError(
            "geocentric latitude requires an explicit conversion before Geodetic calculation"
        )
    chart = geodetic_chart(
        location.longitude_deg,
        location.latitude_deg,
        obliquity,
        ayanamsa_deg=ayanamsa_deg,
        zodiac=zodiac,
    )
    return replace(
        chart,
        provenance=replace(chart.provenance, location=location),
    )


def geodetic_chart_from_chart(
    chart,
    zodiac:          str = "tropical",
    ayanamsa_system: str | None = None,
) -> GeodeticChart:
    """
    Convenience wrapper: build a GeodeticChart from a Moira ChartContext.

    Reads two different clock coordinates from the vessel, because the two
    authorities ask for different ones: true obliquity is a TT function, while
    ``moira.sidereal.ayanamsa`` is contracted for UT and performs its own
    UT→TT step.  Feeding it ``chart.jd_tt`` would shift the epoch twice.

    Parameters
    ----------
    chart            : a ``ChartContext`` instance (from ``moira.chart``).
    zodiac           : "tropical" (default) or "sidereal".
    ayanamsa_system  : Ayanamsa system name (from ``moira.sidereal.Ayanamsa``).
                       Required when ``zodiac="sidereal"``; must be omitted for
                       tropical.

    Returns
    -------
    GeodeticChart — derived from ``chart.latitude``, ``chart.longitude``,
    and obliquity at ``chart.jd_tt``.

    Raises
    ------
    ValueError
        If ``zodiac="sidereal"`` and ``ayanamsa_system`` is not provided, or if
        ``zodiac="tropical"`` and an ``ayanamsa_system`` is provided.
    """
    _validate_zodiac(zodiac)
    _validate_zodiac_policy(zodiac, ayanamsa_system=ayanamsa_system)
    from .obliquity import true_obliquity_with_truth

    if zodiac == "sidereal" and ayanamsa_system is None:
        raise ValueError(
            "ayanamsa_system is required when zodiac='sidereal'. "
            "Pass a system name from moira.sidereal.Ayanamsa."
        )

    obliquity_truth = true_obliquity_with_truth(chart.jd_tt)
    obliquity = obliquity_truth.true_obliquity_deg
    ayanamsa_deg = 0.0

    if zodiac == "sidereal":
        from .sidereal import ayanamsa as compute_ayanamsa
        ayanamsa_deg = compute_ayanamsa(chart.jd_ut, ayanamsa_system)

    result = geodetic_chart(
        geo_longitude = chart.longitude,
        geo_latitude  = chart.latitude,
        obliquity     = obliquity,
        ayanamsa_deg  = ayanamsa_deg,
        zodiac        = zodiac,
    )
    return replace(
        result,
        provenance=GeodeticChartProvenance(
            calculation_source="chart_context",
            chart_jd_ut=chart.jd_ut,
            chart_jd_tt=chart.jd_tt,
            obliquity_timescale=obliquity_truth.input_timescale,
            mean_obliquity_model=obliquity_truth.mean_model,
            nutation_model=obliquity_truth.nutation_model,
            ayanamsa_system=ayanamsa_system,
            ayanamsa_timescale="UT" if zodiac == "sidereal" else None,
        ),
    )


# ---------------------------------------------------------------------------
# Geodetic equivalents
# ---------------------------------------------------------------------------

def geodetic_equivalents(
    planet_longitudes: dict[str, float],
    ayanamsa_deg:      float = 0.0,
) -> dict[str, float]:
    """
    Geographic longitude where each planet's position is the native Geodetic MC.

    Inverse of ``geodetic_mc``: given a planet's ecliptic longitude, return
    the geographic longitude at which that planet's degree falls exactly on
    the Geodetic MC.

    For the tropical path (``ayanamsa_deg = 0.0``):

        geographic longitude = planet tropical longitude

    For the sidereal path (``ayanamsa_deg > 0``, input is sidereal positions):

        geographic longitude = planet sidereal longitude + ayanamsa
                             = planet tropical longitude

    In both cases the geographic longitude equals the planet's tropical
    ecliptic longitude.  The ayanamsa cancels in the inversion.  The
    meaningful distinction is that the sidereal path accepts sidereal input
    and recovers the geographic anchor, while the tropical path accepts
    tropical input directly.

    Parameters
    ----------
    planet_longitudes : dict mapping body name → ecliptic longitude (degrees).
                        Tropical if ``ayanamsa_deg = 0.0``; sidereal otherwise.
    ayanamsa_deg      : Ayanamsa in degrees.  Pass 0.0 for tropical input.

    Returns
    -------
    dict mapping body name → geographic longitude in [−180°, +180°].
    """
    _validate_finite("ayanamsa_deg", ayanamsa_deg)
    result: dict[str, float] = {}
    for body, lon in planet_longitudes.items():
        if not body:
            raise ValueError("Geodetic equivalent body names must be non-empty")
        _validate_finite(f"longitude for {body!r}", lon)
        geo_lon = (lon + ayanamsa_deg) % 360.0
        result[body] = wrap_longitude_deg(geo_lon)
    return result


def geodetic_equivalents_result_from_chart(
    chart,
    bodies:          list[str] | None = None,
    zodiac:          str               = "tropical",
    ayanamsa_system: str | None        = None,
) -> GeodeticEquivalentsResult:
    """
    Convenience wrapper: geographic equivalents for natal planets from a ChartContext.

    For each planet, returns the geographic longitude at which that planet's
    ecliptic position is the native Geodetic MC.

    The ayanamsa for the sidereal path is resolved at ``chart.jd_ut``, matching
    the UT input contract of ``moira.sidereal.ayanamsa``.

    Parameters
    ----------
    chart            : a ``ChartContext`` instance.
    bodies           : list of body names to include.  Defaults to all bodies
                       present in ``chart.planets``.
    zodiac           : "tropical" (default) or "sidereal".
    ayanamsa_system  : Ayanamsa system name.  Required when ``zodiac="sidereal"``;
                       must be omitted for tropical.

    Returns
    -------
    Immutable result containing ordered source/selected/output longitudes and
    the chart epoch, zodiac lane, ayanamsa, source frame, and policy.

    A geographic meridian is zodiac-independent, so both lanes resolve the
    same anchor; ``zodiac`` selects only how the body position is expressed on
    the way into the inversion.

    Raises
    ------
    ValueError
        If ``zodiac="sidereal"`` and ``ayanamsa_system`` is not provided, or if
        ``zodiac="tropical"`` and an ``ayanamsa_system`` is provided.
    """
    _validate_zodiac(zodiac)
    _validate_zodiac_policy(zodiac, ayanamsa_system=ayanamsa_system)
    if zodiac == "sidereal" and ayanamsa_system is None:
        raise ValueError(
            "ayanamsa_system is required when zodiac='sidereal'. "
            "Pass a system name from moira.sidereal.Ayanamsa."
        )

    if bodies is None:
        bodies = list(chart.planets.keys())

    ayanamsa_deg = 0.0
    if zodiac == "sidereal":
        from .sidereal import ayanamsa as compute_ayanamsa
        ayanamsa_deg = compute_ayanamsa(chart.jd_ut, ayanamsa_system)

    _validate_finite("chart.jd_ut", chart.jd_ut)
    _validate_finite("chart.jd_tt", chart.jd_tt)
    positions: list[GeodeticEquivalentPosition] = []
    seen: set[str] = set()
    for body in bodies:
        if not isinstance(body, str) or not body.strip():
            raise ValueError("Geodetic equivalent body names must be non-empty")
        # Preserve the legacy mapping's duplicate-key behavior while exposing
        # a uniquely keyed immutable result in the detailed API.
        if body in seen:
            continue
        seen.add(body)
        source_longitude = chart.planets[body].longitude
        _validate_finite(f"longitude for {body!r}", source_longitude)
        source_tropical = source_longitude % 360.0
        selected_longitude = (
            (source_longitude - ayanamsa_deg) % 360.0
            if zodiac == "sidereal"
            else source_longitude % 360.0
        )
        # Keep the legacy inversion operations in the same order so its
        # floating-point result remains bit-for-bit compatible.
        geographic_longitude = geodetic_equivalents(
            {body: selected_longitude}, ayanamsa_deg
        )[body]
        positions.append(
            GeodeticEquivalentPosition(
                body=body,
                source_tropical_longitude_deg=source_tropical,
                selected_zodiac_longitude_deg=selected_longitude,
                geographic_longitude_deg=geographic_longitude,
            )
        )

    return GeodeticEquivalentsResult(
        positions=tuple(positions),
        provenance=GeodeticEquivalentsProvenance(
            chart_jd_ut=chart.jd_ut,
            chart_jd_tt=chart.jd_tt,
            zodiac=zodiac,
            ayanamsa_deg=ayanamsa_deg,
            ayanamsa_system=ayanamsa_system,
            ayanamsa_timescale="UT" if zodiac == "sidereal" else None,
        ),
    )


def geodetic_equivalents_from_chart(
    chart,
    bodies:          list[str] | None = None,
    zodiac:          str               = "tropical",
    ayanamsa_system: str | None        = None,
) -> dict[str, float]:
    """Compatibility wrapper returning only the geographic-longitude map."""
    return geodetic_equivalents_result_from_chart(
        chart,
        bodies=bodies,
        zodiac=zodiac,
        ayanamsa_system=ayanamsa_system,
    ).geographic_longitudes


def _ascendant_local_derivatives(
    geo_longitude_deg: float,
    geo_latitude_deg: float,
    obliquity_deg: float,
) -> GeodeticAngleDerivatives:
    """Analytic local derivative of the rising-root angle formula."""
    longitude = math.radians(geo_longitude_deg)
    latitude = math.radians(geo_latitude_deg)
    epsilon = math.radians(obliquity_deg)

    sin_l, cos_l = math.sin(longitude), math.cos(longitude)
    sin_e, cos_e = math.sin(epsilon), math.cos(epsilon)
    sin_p, cos_p = math.sin(latitude), math.cos(latitude)
    armc = math.atan2(sin_l * cos_e, cos_l)
    sin_a, cos_a = math.sin(armc), math.cos(armc)

    armc_denominator = cos_l * cos_l + sin_l * sin_l * cos_e * cos_e
    d_armc_d_longitude = cos_e / armc_denominator
    d_armc_d_obliquity = -sin_l * cos_l * sin_e / armc_denominator

    x = sin_a * cos_e * cos_p + sin_e * sin_p
    y = -cos_a * cos_p
    angle_denominator = x * x + y * y
    if angle_denominator <= 1e-24:
        raise ValueError("Ascendant sensitivity is undefined at a tangent horizon")

    dx_d_armc = cos_a * cos_e * cos_p
    dy_d_armc = sin_a * cos_p
    dx_d_obliquity = -sin_a * sin_e * cos_p + cos_e * sin_p
    dx_d_latitude = -sin_a * cos_e * sin_p + sin_e * cos_p
    dy_d_latitude = cos_a * sin_p

    d_asc_d_armc = (x * dy_d_armc - y * dx_d_armc) / angle_denominator
    d_asc_d_obliquity_direct = -y * dx_d_obliquity / angle_denominator
    d_asc_d_latitude = (
        x * dy_d_latitude - y * dx_d_latitude
    ) / angle_denominator

    return GeodeticAngleDerivatives(
        geo_longitude_deg=d_asc_d_armc * d_armc_d_longitude,
        geo_latitude_deg=d_asc_d_latitude,
        obliquity_deg=(
            d_asc_d_armc * d_armc_d_obliquity
            + d_asc_d_obliquity_direct
        ),
    )


def geodetic_chart_sensitivity(
    chart: GeodeticChart,
    uncertainty: GeodeticInputUncertainty,
) -> GeodeticSensitivityResult:
    """Estimate first-order MC/ASC output response to input uncertainty.

    The result is a local linearization, not a guaranteed uncertainty bound.
    The supplied latitude/obliquity intervals must stay inside the calculation
    domain so the local estimate does not cross a refusal boundary.
    """
    if not isinstance(chart, GeodeticChart):
        raise TypeError("chart must be a GeodeticChart")
    if not isinstance(uncertainty, GeodeticInputUncertainty):
        raise TypeError("uncertainty must be a GeodeticInputUncertainty")

    latitude_low = chart.geo_latitude - uncertainty.latitude_deg
    latitude_high = chart.geo_latitude + uncertainty.latitude_deg
    polar_limit = 90.0 - _POLAR_REFUSAL_MARGIN_DEG
    if latitude_low <= -polar_limit or latitude_high >= polar_limit:
        raise ValueError("latitude uncertainty crosses the Geodetic polar refusal boundary")
    if (
        chart.obliquity - uncertainty.obliquity_deg < _EARTH_OBLIQUITY_MIN_DEG
        or chart.obliquity + uncertainty.obliquity_deg > _EARTH_OBLIQUITY_MAX_DEG
    ):
        raise ValueError("obliquity uncertainty crosses the admitted [22, 25] degree envelope")

    mc_derivatives = GeodeticAngleDerivatives(1.0, 0.0, 0.0)
    asc_derivatives = _ascendant_local_derivatives(
        chart.geo_longitude,
        chart.geo_latitude,
        chart.obliquity,
    )
    mc_radius = (
        abs(mc_derivatives.geo_longitude_deg) * uncertainty.longitude_deg
        + abs(mc_derivatives.geo_latitude_deg) * uncertainty.latitude_deg
        + abs(mc_derivatives.obliquity_deg) * uncertainty.obliquity_deg
    )
    asc_radius = (
        abs(asc_derivatives.geo_longitude_deg) * uncertainty.longitude_deg
        + abs(asc_derivatives.geo_latitude_deg) * uncertainty.latitude_deg
        + abs(asc_derivatives.obliquity_deg) * uncertainty.obliquity_deg
    )
    return GeodeticSensitivityResult(
        base_chart=chart,
        uncertainty=uncertainty,
        mc_derivatives=mc_derivatives,
        asc_derivatives=asc_derivatives,
        mc_linearized_radius_deg=mc_radius,
        asc_linearized_radius_deg=asc_radius,
        latitude_margin_to_pole_deg=90.0 - abs(chart.geo_latitude),
    )
