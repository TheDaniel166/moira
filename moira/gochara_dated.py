"""Reader-bound Gochar snapshots; dated windows are a separate product.

Astronomy supplies complete apparent geocentric, true-ecliptic-of-date
positions. Each epoch uses its own reader-bound TT and named true ayanamsa.
Judgment remains owned by ``gochara``. Optional raw natal BAV reuses the
existing Raman 1981 encoding, without reductions or a strength threshold.
"""
from dataclasses import dataclass, field
import math
from datetime import datetime

from ._strenum import StrEnum

from ._ephemeris_time import _bind_ephemeris_time, _EphemerisTimeBasisError
from .ashtakavarga import bhinnashtakavarga
from .gochara import (
    GOCHARA_PLANETS, GocharaPosition, GocharaPolicy, GocharaBavMode,
    GocharaCompleteness, GocharaSubsystemProfile, gochara_from_positions,
    gochara_subsystem_profile, _longitude, gochara_doctrine_options,
)
from .houses import _asc_from_armc
from .julian import _local_sidereal_time_at_tt, jd_from_datetime, utc_to_ut1
from .obliquity import mean_obliquity, nutation
from .planets import planet_at
from .sidereal import Ayanamsa, _ayanamsa_at_tt, _STAR_ANCHORED
from .spk_reader import (
    KernelReader, MissingKernelError, OutOfRangeError, get_reader,
    use_reader_override,
)
from .stars import star_at

__all__ = [
    "GocharaNatalBavMode", "GocharaDatePolicy", "DEFAULT_GOCHARA_DATE_POLICY",
    "GocharaBirthLocation", "GocharaDatedPosition", "GocharaEpoch",
    "GocharaDateResult", "GocharaResourceError", "GocharaCoverageError",
    "gochara_at", "gochara_for_datetimes",
]


class GocharaResourceError(RuntimeError):
    """A required planetary, clock-identity or anchor-star resource is absent."""


class GocharaCoverageError(ValueError):
    """A requested epoch is outside the serving planetary kernel coverage."""


class GocharaNatalBavMode(StrEnum):
    """Whether dated Gochar omits or computes raw natal Bhinnashtakavarga."""

    OMIT = "omit"
    COMPUTE_RAW = "compute_raw"


def _number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


@dataclass(frozen=True, slots=True)
class GocharaBirthLocation:
    """Geographic degrees, north/east positive; poles have no unique Lagna."""
    latitude: float
    longitude: float

    def __post_init__(self):
        lat = _number("latitude", self.latitude)
        lon = _number("longitude", self.longitude)
        if not -90 < lat < 90 or not -180 <= lon <= 180:
            raise ValueError("birth latitude must be in (-90, 90), longitude in [-180, 180]")
        object.__setattr__(self, "latitude", lat)
        object.__setattr__(self, "longitude", lon)


@dataclass(frozen=True, slots=True)
class GocharaDatePolicy:
    """Astronomical composition choices, separate from textual judgment policy.

    All named Moira ayanamsas are available. Live anchors must resolve; their
    polynomial fallback is not admitted by this product. Raw BAV is opt-in.
    """
    ayanamsa_system: str = Ayanamsa.LAHIRI
    natal_bav_mode: GocharaNatalBavMode = GocharaNatalBavMode.OMIT
    gochara_policy: GocharaPolicy = field(default_factory=lambda: GocharaPolicy(
        completeness=GocharaCompleteness.REQUIRE_COMPLETE,
    ))
    longitude_origin: str = field(init=False, default="apparent_geocentric")
    longitude_frame: str = field(init=False, default="true_ecliptic_of_date")
    ayanamsa_mode: str = field(init=False, default="true")
    light_time: bool = field(init=False, default=True)
    aberration: bool = field(init=False, default=True)
    gravitational_deflection: bool = field(init=False, default=True)
    nutation: bool = field(init=False, default=True)

    def __post_init__(self):
        if not isinstance(self.ayanamsa_system, str) or self.ayanamsa_system not in Ayanamsa.ALL:
            raise ValueError("ayanamsa_system must be a named Moira ayanamsa")
        if not isinstance(self.natal_bav_mode, GocharaNatalBavMode):
            raise TypeError("natal_bav_mode must be a GocharaNatalBavMode")
        if not isinstance(self.gochara_policy, GocharaPolicy):
            raise TypeError("gochara_policy must be a GocharaPolicy")
        bav = self.gochara_policy.bav_mode
        if self.natal_bav_mode is GocharaNatalBavMode.COMPUTE_RAW and bav is GocharaBavMode.OMIT:
            raise ValueError("compute_raw contradicts Gochar BAV omission")
        if self.natal_bav_mode is GocharaNatalBavMode.OMIT and bav is GocharaBavMode.REQUIRE_ALL_RAW:
            raise ValueError("require_all_raw needs natal_bav_mode=compute_raw")

    @property
    def selected_options(self):
        """Outer composition decisions; inner policy still describes its evaluator."""
        ids = ("astronomy.reader_epochs", "bav.natal_raw_raman_1981"
               if self.natal_bav_mode is GocharaNatalBavMode.COMPUTE_RAW else "bav.omit")
        options = {o.id: o for o in gochara_doctrine_options()}
        return tuple(options[id_] for id_ in ids)


DEFAULT_GOCHARA_DATE_POLICY = GocharaDatePolicy()


@dataclass(frozen=True, slots=True)
class GocharaDatedPosition:
    """A tropical position and ayanamsa with the derived sidereal Gochar position."""

    planet: str
    tropical_longitude: float
    ayanamsa_degrees: float
    position: GocharaPosition = field(init=False)

    def __post_init__(self):
        tropical = _number("tropical_longitude", self.tropical_longitude)
        offset = _number("ayanamsa_degrees", self.ayanamsa_degrees)
        if not 0 <= tropical < 360:
            raise ValueError("tropical_longitude must be in [0, 360)")
        object.__setattr__(self, "tropical_longitude", tropical)
        object.__setattr__(self, "ayanamsa_degrees", offset)
        object.__setattr__(self, "position", GocharaPosition(self.planet, tropical - offset))


@dataclass(frozen=True, slots=True)
class GocharaEpoch:
    """Immutable clock/frame evidence and seven complete astronomical inputs.

    Direct construction validates structural consistency, not SPK authenticity.
    Use ``gochara_at`` to derive these observations from a bound reader.
    """
    jd_ut1: float
    jd_tt: float
    jd_tdb: float
    delta_t_seconds: float
    delta_t_correction_seconds: float
    tdb_minus_tt_seconds: float
    delta_t_source: str
    kernel_label: str
    planetary_ephemeris: str
    lunar_ephemeris: str
    lunar_tidal_acceleration_arcsec_per_cy2: float
    ayanamsa_system: str
    ayanamsa_degrees: float
    tropical_longitudes: tuple[float, ...]
    positions: tuple[GocharaDatedPosition, ...] = field(init=False)
    ayanamsa_method: str = field(init=False)
    ayanamsa_anchor: str | None = field(init=False)

    def __post_init__(self):
        for name in (
            "jd_ut1", "jd_tt", "jd_tdb", "delta_t_seconds", "delta_t_correction_seconds",
            "tdb_minus_tt_seconds", "ayanamsa_degrees", "lunar_tidal_acceleration_arcsec_per_cy2",
        ):
            object.__setattr__(self, name, _number(name, getattr(self, name)))
        for name in ("delta_t_source", "kernel_label", "planetary_ephemeris", "lunar_ephemeris"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a nonempty source label")
        if self.ayanamsa_system not in Ayanamsa.ALL:
            raise ValueError("ayanamsa_system must be a named Moira ayanamsa")
        # Allow two JD ulps, not a seconds-scale mismatch hidden by relative tolerance.
        tolerance = 2 * max(math.ulp(self.jd_ut1), math.ulp(self.jd_tt), math.ulp(self.jd_tdb))
        if abs((self.jd_tt - self.jd_ut1) - self.delta_t_seconds / 86400) > tolerance:
            raise ValueError("TT/UT1 coordinates contradict Delta-T receipt")
        if abs((self.jd_tdb - self.jd_tt) - self.tdb_minus_tt_seconds / 86400) > tolerance:
            raise ValueError("TDB/TT coordinates contradict conversion receipt")
        tropical = tuple(self.tropical_longitudes)
        if len(tropical) != len(GOCHARA_PLANETS):
            raise ValueError("epoch requires all seven tropical longitudes in canonical planet order")
        positions = tuple(GocharaDatedPosition(p, lon, self.ayanamsa_degrees)
                          for p, lon in zip(GOCHARA_PLANETS, tropical))
        object.__setattr__(self, "tropical_longitudes", tuple(p.tropical_longitude for p in positions))
        object.__setattr__(self, "positions", positions)
        anchor = _STAR_ANCHORED.get(self.ayanamsa_system)
        object.__setattr__(self, "ayanamsa_method", "live_star_anchor" if anchor else "polynomial_true")
        object.__setattr__(self, "ayanamsa_anchor", anchor[0] if anchor else None)


def _birth_scope(policy, birth_location):
    if not isinstance(policy, GocharaDatePolicy):
        raise TypeError("policy must be a GocharaDatePolicy")
    if birth_location is not None and not isinstance(birth_location, GocharaBirthLocation):
        raise TypeError("birth_location must be a GocharaBirthLocation")
    compute = policy.natal_bav_mode is GocharaNatalBavMode.COMPUTE_RAW
    if compute != (birth_location is not None):
        raise ValueError("birth_location is required exactly when natal_bav_mode=compute_raw")


@dataclass(frozen=True, slots=True)
class GocharaDateResult:
    """Derived natal/transit judgment, retaining every input and raw BAV source."""
    natal: GocharaEpoch
    transit: GocharaEpoch
    policy: GocharaDatePolicy = DEFAULT_GOCHARA_DATE_POLICY
    birth_location: GocharaBirthLocation | None = None
    natal_ascendant_tropical: float | None = field(init=False)
    natal_ascendant_sidereal: float | None = field(init=False)
    natal_sign_indices: tuple[tuple[str, int], ...] = field(init=False)
    bav_source: str | None = field(init=False)
    profile: GocharaSubsystemProfile = field(init=False)

    def __post_init__(self):
        _birth_scope(self.policy, self.birth_location)
        if not isinstance(self.natal, GocharaEpoch) or not isinstance(self.transit, GocharaEpoch):
            raise TypeError("natal and transit must be GocharaEpoch vessels")
        if any(e.ayanamsa_system != self.policy.ayanamsa_system for e in (self.natal, self.transit)):
            raise ValueError("epoch ayanamsas contradict the composition policy")
        asc = sidereal_asc = None
        indices = {p.planet: p.position.rashi_index for p in self.natal.positions}
        bhinna = None
        if self.birth_location is not None:
            # Reuse house geometry only, with the same reader-bound natal TT.
            dpsi, deps = nutation(self.natal.jd_tt)
            mean_eps = mean_obliquity(self.natal.jd_tt)
            eps = mean_eps + deps
            lat, lon = self.birth_location.latitude, self.birth_location.longitude
            armc = _local_sidereal_time_at_tt(self.natal.jd_ut1, self.natal.jd_tt, lon, dpsi, mean_eps)
            theta, epsilon, phi = map(math.radians, (armc, eps, lat))
            x = math.sin(theta) * math.cos(epsilon) + math.tan(phi) * math.sin(epsilon)
            y = -math.cos(theta)
            if math.hypot(x, y) < 1e-12:
                raise ValueError("birth horizon and ecliptic do not define a unique Lagna")
            asc = _asc_from_armc(armc, eps, lat)
            sidereal_asc = _longitude(asc - self.natal.ayanamsa_degrees, "natal Lagna")
            indices["Lagna"] = min(11, int(sidereal_asc / 30))
            bhinna = {p: bhinnashtakavarga(p, indices) for p in GOCHARA_PLANETS}
        snapshot = gochara_from_positions(
            self.natal.positions[1].position.sidereal_longitude,
            {p.planet: p.position.sidereal_longitude for p in self.transit.positions},
            bhinna=bhinna, policy=self.policy.gochara_policy,
        )
        for name, value in (
            ("natal_ascendant_tropical", asc), ("natal_ascendant_sidereal", sidereal_asc),
            ("natal_sign_indices", tuple(indices.items())),
            ("bav_source", "Moira Raman 1981 encoding; own natal seven bodies + Lagna; unreduced"
             if bhinna is not None else None),
            ("profile", gochara_subsystem_profile(snapshot)),
        ):
            object.__setattr__(self, name, value)


def _epoch(jd_ut1, reader, policy):
    bound = _bind_ephemeris_time(jd_ut1, reader)
    identity = bound.identity
    if any(value is None for value in (
        identity.planetary_ephemeris, identity.lunar_ephemeris,
        identity.lunar_tidal_acceleration_arcsec_per_cy2,
    )):
        raise GocharaResourceError("Gochar requires a declared planetary/lunar time identity")
    if policy.ayanamsa_system in _STAR_ANCHORED:
        anchor, target = _STAR_ANCHORED[policy.ayanamsa_system]
        try:
            offset = (star_at(anchor, bound.epoch_tt).longitude - target) % 360
        except ValueError as exc:
            raise GocharaResourceError("required Gochar live anchor catalogue is invalid") from exc
    else:
        offset = _ayanamsa_at_tt(bound.epoch_tt, policy.ayanamsa_system, "true")
    tropical = tuple(planet_at(
        p, jd_ut1, reader=reader, jd_tt=bound.epoch_tt,
        apparent=True, aberration=True, grav_deflection=True, nutation=True,
        center="geocentric", frame="ecliptic",
    ).longitude for p in GOCHARA_PLANETS)
    return GocharaEpoch(
        jd_ut1, bound.epoch_tt, bound.epoch_tdb, bound.delta_t_seconds,
        bound.delta_t_correction_seconds, bound.tdb_minus_tt_seconds,
        bound.raw_delta_t.source_product, identity.summary_label,
        identity.planetary_ephemeris, identity.lunar_ephemeris,
        identity.lunar_tidal_acceleration_arcsec_per_cy2,
        policy.ayanamsa_system, offset, tropical,
    )


def gochara_at(natal_jd_ut1: float, transit_jd_ut1: float, *,
               birth_location: GocharaBirthLocation | None = None,
               policy: GocharaDatePolicy | None = None,
               reader: KernelReader | None = None) -> GocharaDateResult:
    """Derive a complete Gochar snapshot from two UT1 Julian dates.

    For aware civil datetimes, convert each with ``jd_from_datetime`` and
    ``utc_to_ut1`` first. Neither epoch is silently assumed to be UTC. Transit
    may precede birth for retrospective comparison; this is not a forecast.
    Required resources never fall back to partial observations or another frame.
    """
    active = DEFAULT_GOCHARA_DATE_POLICY if policy is None else policy
    _birth_scope(active, birth_location)
    natal_jd = _number("natal_jd_ut1", natal_jd_ut1)
    transit_jd = _number("transit_jd_ut1", transit_jd_ut1)
    if any(not -10_000_000 <= jd <= 10_000_000 for jd in (natal_jd, transit_jd)):
        raise ValueError("epochs must be in the admitted JD range [-10000000, 10000000]")
    stage = "reader"
    try:
        bound_reader = get_reader() if reader is None else reader
        with use_reader_override(bound_reader):
            stage = "natal"
            natal = _epoch(natal_jd, bound_reader, active)
            stage = "transit"
            transit = _epoch(transit_jd, bound_reader, active)
        return GocharaDateResult(natal, transit, active, birth_location)
    except OutOfRangeError as exc:
        raise GocharaCoverageError(f"{stage} epoch is outside planetary kernel coverage") from exc
    except (MissingKernelError, _EphemerisTimeBasisError, LookupError, FileNotFoundError) as exc:
        raise GocharaResourceError(f"required Gochar {stage} ephemeris, time identity or anchor resource is unavailable") from exc


def gochara_for_datetimes(natal_dt: datetime, transit_dt: datetime, *,
                         birth_location: GocharaBirthLocation | None = None,
                         policy: GocharaDatePolicy | None = None,
                         reader: KernelReader | None = None) -> GocharaDateResult:
    """Convert two timezone-aware civil instants to UT1, then bind astronomy.

    UTC conversion uses Moira's existing leap-second/Earth-rotation policy.
    Bare dates and naive datetimes do not identify an instant and are rejected.
    """
    for name, value in (("natal_dt", natal_dt), ("transit_dt", transit_dt)):
        if not isinstance(value, datetime):
            raise TypeError(f"{name} must be a timezone-aware datetime")
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must be timezone-aware")
    return gochara_at(
        utc_to_ut1(jd_from_datetime(natal_dt)), utc_to_ut1(jd_from_datetime(transit_dt)),
        birth_location=birth_location, policy=policy, reader=reader,
    )
