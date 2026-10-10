"""Explicit inputs for source-defined Shadbala components.

Raman 1996 articles 30, 47-57 and 75 govern the repaired components.
The retained ingress-based year/month lords and osculating Chesta inputs
are separately identified Moira conventions, not Raman's worked ephemeris.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
SAPTAVARGAJA_PROFILES = ("raman_1996", "bphs_santhanam_27")


class ShadbalaContextError(ValueError):
    """A full strength cannot be computed from missing/incompatible evidence."""


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


@dataclass(frozen=True, slots=True)
class ShadbalaContext:
    """Immutable, same-epoch geometry and motion evidence; angles in degrees.

    Supplied contexts do not query an ephemeris. None solar endpoints mean
    Tribhaga is unavailable: callers can inspect the context, but cannot
    claim a full Shadbala or sufficiency ranking from it.
    """

    jd: float
    ayanamsa_system: str
    sidereal_longitudes: tuple[tuple[str, float], ...]
    declinations: tuple[tuple[str, float], ...]
    chesta_values: tuple[tuple[str, float], ...]
    local_apparent_day_fraction: float
    sunrise_jd: float | None
    sunset_jd: float | None
    next_sunrise_jd: float | None
    abda_lord: str
    masa_lord: str
    vara_lord: str
    hora_lord: str | None = None
    provenance: str = "supplied"
    observer_latitude: float | None = None
    observer_longitude: float | None = None
    longitude_frame: str = "apparent_geocentric_true_ecliptic_of_date_sidereal"
    declination_frame: str = "apparent_geocentric_true_equator_of_date"
    mercury_nature: str = "same_sign_malefic_association"
    vara_basis: str = "supplied"
    vara_jd_utc: float | None = None

    def __post_init__(self):
        if (
            not _finite_number(self.jd)
            or not isinstance(self.ayanamsa_system, str)
            or not self.ayanamsa_system
        ):
            raise ShadbalaContextError("finite epoch and named ayanamsa required")
        for name, pairs, lower, upper in (
            ("sidereal_longitudes", self.sidereal_longitudes, 0, 360),
            ("declinations", self.declinations, -90, 90),
            ("chesta_values", self.chesta_values, 0, 60),
        ):
            if (
                not isinstance(pairs, tuple)
                or len(pairs) != 7
                or any(not isinstance(p, tuple) or len(p) != 2 for p in pairs)
                or {p for p, _ in pairs} != set(SEVEN)
            ):
                raise ShadbalaContextError(
                    f"{name} must contain seven unique immutable planet pairs"
                )
            for _, value in pairs:
                if (
                    not _finite_number(value)
                    or not lower <= value <= upper
                    or (name == "sidereal_longitudes" and value == upper)
                ):
                    raise ShadbalaContextError(f"invalid {name}")
        f = self.local_apparent_day_fraction
        if not _finite_number(f) or not 0 <= f < 1:
            raise ShadbalaContextError("local apparent solar fraction must be in [0,1)")
        events = (self.sunrise_jd, self.sunset_jd, self.next_sunrise_jd)
        if any(x is not None for x in events):
            if (
                any(not _finite_number(x) for x in events)
                or not events[0] < events[1] < events[2]
                or not events[0] <= self.jd < events[2]
            ):
                raise ShadbalaContextError(
                    "solar events must bracket the epoch in sunrise order"
                )
        for name in ("abda_lord", "masa_lord", "vara_lord", "hora_lord"):
            value = getattr(self, name)
            if value not in SEVEN and not (name == "hora_lord" and value is None):
                raise ShadbalaContextError(f"invalid {name}")
        if self.provenance not in ("supplied", "serving_reader_derived"):
            raise ShadbalaContextError("unknown context provenance")
        if self.vara_basis == "civil_utc_midnight":
            from .julian import utc_to_ut1
            from .shadbala import _weekday_lord

            if (not _finite_number(self.vara_jd_utc)
                    or utc_to_ut1(self.vara_jd_utc) != self.jd
                    or _weekday_lord(self.vara_jd_utc) != self.vara_lord):
                raise ShadbalaContextError("civil UTC Vara evidence disagrees with epoch/lord")
        elif self.vara_basis != "supplied" or self.vara_jd_utc is not None:
            raise ShadbalaContextError("unknown or inconsistent Vara basis")
        if (
            self.longitude_frame != "apparent_geocentric_true_ecliptic_of_date_sidereal"
            or self.declination_frame != "apparent_geocentric_true_equator_of_date"
        ):
            raise ShadbalaContextError("incompatible Shadbala coordinate frame")
        if self.mercury_nature not in (
            "benefic",
            "malefic",
            "same_sign_malefic_association",
        ):
            raise ShadbalaContextError("unknown Mercury nature convention")
        for name, limit in (("observer_latitude", 90), ("observer_longitude", 180)):
            value = getattr(self, name)
            if value is not None and (not _finite_number(value) or abs(value) > limit):
                raise ShadbalaContextError(f"invalid {name}")
        if self.provenance == "serving_reader_derived" and (
            self.observer_latitude is None or self.observer_longitude is None
        ):
            raise ShadbalaContextError(
                "derived context requires its observer provenance"
            )

    @property
    def missing_components(self) -> tuple[str, ...]:
        """Explicit unavailability; no zero award stands in for missing events."""
        return ("tribhaga",) if self.sunrise_jd is None else ()

    @property
    def is_day(self) -> bool:
        """Day/night from supplied sunrise geometry, with half-open boundaries."""
        self.require_complete()
        return self.jd < self.sunset_jd

    def require_complete(self) -> None:
        if self.missing_components:
            raise ShadbalaContextError(
                "Shadbala unavailable: missing sunrise/sunset geometry for tribhaga"
            )

    def check_positions(self, jd, system, positions):
        """Reject accidental cross-epoch/frame/chart composition."""
        if jd != self.jd or system != self.ayanamsa_system:
            raise ShadbalaContextError("Shadbala context epoch/ayanamsa mismatch")
        own = dict(self.sidereal_longitudes)
        for planet, lon in positions.items():
            if (
                planet not in own
                or not _finite_number(lon)
                or abs(own[planet] - lon % 360) > 1e-9
            ):
                raise ShadbalaContextError("Shadbala context position mismatch")


def derive_shadbala_context(
    jd: float,
    latitude: float,
    longitude: float,
    *,
    ayanamsa_system: str = "Lahiri",
    hora_lord: str | None = None,
    jd_utc: float | None = None,
    reader=None,
) -> ShadbalaContext:
    """Derive all supporting evidence once through the caller's serving reader.

    Standard Sun horizon -0.8333 degrees; local apparent time from the Sun's
    hour angle. Polar event absence remains visible in missing_components.
    Vara follows civil UTC midnight, matching dated Panchanga. Supply the
    original UTC JD when available; UT1-only callers use the time owner's
    inverse. This weekday convention does not alter the UT1 geometry.
    """
    from .spk_reader import get_reader, use_reader_override
    from .planets import planet_at
    from .sidereal import tropical_to_sidereal
    from .rise_set import find_phenomena, _lst, _body_ra_dec
    from .shadbala import chesta_bala, _sankranti_jd, _weekday_lord
    from .julian import _ut1_to_utc, utc_to_ut1

    if any(not _finite_number(x) for x in (jd, latitude, longitude)):
        raise ShadbalaContextError("epoch and observer must be finite numbers")
    if abs(latitude) > 90 or abs(longitude) > 180:
        raise ShadbalaContextError("observer outside geographic range")
    civil_jd = _ut1_to_utc(jd) if jd_utc is None else jd_utc
    if not _finite_number(civil_jd) or utc_to_ut1(civil_jd) != jd:
        raise ShadbalaContextError("UTC weekday epoch must identify the same UT1 instant")
    bound = get_reader() if reader is None else reader
    with use_reader_override(bound):
        planets = {p: planet_at(p, jd, reader=bound) for p in SEVEN}
        positions = {
            p: tropical_to_sidereal(v.longitude, jd, system=ayanamsa_system)
            for p, v in planets.items()
        }
        equatorial = {p: _body_ra_dec(jd, p) for p in SEVEN}
        fraction = ((_lst(jd, longitude) - equatorial["Sun"][0] + 180) % 360) / 360
        events = [
            find_phenomena("Sun", jd + offset, latitude, longitude)
            for offset in (-1.0, 0.0, 1.0)
        ]
        rises = sorted(e["Rise"] for e in events if "Rise" in e)
        sets = sorted(e["Set"] for e in events if "Set" in e)
        before = [r for r in rises if r <= jd]
        after = [r for r in rises if r > jd]
        sunrise = sunset = next_sunrise = None
        if before and after:
            lo, hi = before[-1], after[0]
            setting = [s for s in sets if lo < s < hi]
            if setting:
                sunrise, sunset, next_sunrise = lo, setting[0], hi
        chesta = {
            p: chesta_bala(
                p,
                planet_sidereal_lon=positions[p],
                sun_sidereal_lon=positions["Sun"],
                jd=jd,
                ayanamsa_system=ayanamsa_system,
                reader=bound,
            )
            for p in SEVEN
        }
        abda = _weekday_lord(_sankranti_jd(0.0, jd, ayanamsa_system, window_days=370.0))
        masa = _weekday_lord(
            _sankranti_jd(
                float(int(positions["Sun"] // 30) * 30),
                jd,
                ayanamsa_system,
                window_days=32.0,
            )
        )
        return ShadbalaContext(
            jd,
            ayanamsa_system,
            tuple(positions.items()),
            tuple((p, equatorial[p][1]) for p in SEVEN),
            tuple(chesta.items()),
            fraction,
            sunrise,
            sunset,
            next_sunrise,
            abda,
            masa,
            _weekday_lord(civil_jd),
            hora_lord,
            "serving_reader_derived",
            latitude,
            longitude,
            vara_basis="civil_utc_midnight",
            vara_jd_utc=civil_jd,
        )


__all__ = [
    "ShadbalaContext",
    "ShadbalaContextError",
    "derive_shadbala_context",
    "SAPTAVARGAJA_PROFILES",
]
