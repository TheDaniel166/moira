"""Uranian and Hamburg School hypothetical-body positions.

The eight Hamburg points use James Neely's revised 1980 orbital elements.
Transpluto is a separate hypothetical orbit, using the elements published by
Sevin and Strubell in 1952. Each element set defines an unperturbed
heliocentric two-body orbit. Moira then uses its active planetary kernel for
the real Sun/Earth geometry and applies the same apparent-place reduction used
by the planetary engine.

These are conventional hypothetical positions. They are not physical-body
states from JPL/NAIF and must not be presented as discovered trans-Neptunian
objects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ._ephemeris_time import _ut1_to_ephemeris_tt
from .constants import Body, DEG2RAD, KM_PER_AU, sign_of
from .coordinates import mat_vec_mul, precession_matrix_equatorial, vec_add
from .obliquity import mean_obliquity
from .planets import (
    _apparent_geocentric_ecliptic,
    _barycentric,
    _build_apparent_context,
    _deflectors_for_body,
)
from .spk_reader import KernelReader, MissingKernelError, get_active_reader

__all__ = [
    "UranianBody",
    "UranianPosition",
    "uranian_at",
    "all_uranian_at",
    "list_uranian",
]


_GAUSSIAN_MEAN_MOTION_DEG_PER_DAY = 0.9856076686
_LONGITUDE_RATE_STEP_DAYS = 2.0e-3
_J1900 = 2415020.0

URANIAN_MODEL = "fixed_keplerian_orbit_apparent_geocentric"
URANIAN_FRAME = "apparent_geocentric_true_ecliptic_of_date"


class UranianBody:
    """Canonical identifiers for the admitted hypothetical bodies."""

    CUPIDO = "Cupido"
    HADES = "Hades"
    ZEUS = "Zeus"
    KRONOS = "Kronos"
    APOLLON = "Apollon"
    ADMETOS = "Admetos"
    VULKANUS = "Vulkanus"
    POSEIDON = "Poseidon"
    TRANSPLUTO = "Transpluto"

    HAMBURG: tuple[str, ...] = (
        CUPIDO,
        HADES,
        ZEUS,
        KRONOS,
        APOLLON,
        ADMETOS,
        VULKANUS,
        POSEIDON,
    )
    ALL: tuple[str, ...] = HAMBURG + (TRANSPLUTO,)


@dataclass(frozen=True, slots=True)
class UranianOrbitElements:
    """Fixed elements defining one conventional unperturbed orbit.

    ``epoch_jd_tt`` is the epoch of mean anomaly. ``equinox_jd_tt`` defines
    the mean ecliptic/equinox in which the angular elements are expressed.
    Angles are degrees and ``semimajor_axis_au`` is astronomical units.
    """

    epoch_jd_tt: float
    equinox_jd_tt: float
    mean_anomaly_deg: float
    semimajor_axis_au: float
    eccentricity: float
    argument_of_perihelion_deg: float
    ascending_node_deg: float
    inclination_deg: float
    body_group: str
    source_family: str

    @property
    def mean_motion_deg_per_day(self) -> float:
        return _GAUSSIAN_MEAN_MOTION_DEG_PER_DAY / self.semimajor_axis_au**1.5

    @property
    def period_years(self) -> float:
        return 360.0 / self.mean_motion_deg_per_day / 365.25


_NEELY_SOURCE = "neely_1980_hamburg_revised"
_TRANSPLUTO_SOURCE = "sevin_strubell_1952_transpluto"


def _hamburg(
    mean_anomaly: float,
    semimajor_axis: float,
    eccentricity: float,
    argument_of_perihelion: float,
    ascending_node: float,
    inclination: float,
) -> UranianOrbitElements:
    return UranianOrbitElements(
        epoch_jd_tt=_J1900,
        equinox_jd_tt=_J1900,
        mean_anomaly_deg=mean_anomaly,
        semimajor_axis_au=semimajor_axis,
        eccentricity=eccentricity,
        argument_of_perihelion_deg=argument_of_perihelion,
        ascending_node_deg=ascending_node,
        inclination_deg=inclination,
        body_group="hamburg_eight",
        source_family=_NEELY_SOURCE,
    )


# Neely's revised Hamburg elements (Matrix Journal VII, 1980). The Kronos
# semimajor axis is 64.81690 AU, the established seorbel/swetest convention.
# Transpluto is intentionally separate and retains its exact source-era Julian
# epoch/equinox values rather than inheriting the Hamburg J1900 frame.
_URANIAN_ELEMENTS: dict[str, UranianOrbitElements] = {
    UranianBody.CUPIDO: _hamburg(163.7409, 40.99837, 0.00460, 171.4333, 129.8325, 1.0833),
    UranianBody.HADES: _hamburg(27.6496, 50.66744, 0.00245, 148.1796, 161.3339, 1.0500),
    UranianBody.ZEUS: _hamburg(165.1232, 59.21436, 0.00120, 299.0440, 0.0, 0.0),
    UranianBody.KRONOS: _hamburg(169.0193, 64.81690, 0.00305, 208.8801, 0.0, 0.0),
    UranianBody.APOLLON: _hamburg(138.0533, 70.29949, 0.0, 0.0, 0.0, 0.0),
    UranianBody.ADMETOS: _hamburg(351.3350, 73.62765, 0.0, 0.0, 0.0, 0.0),
    UranianBody.VULKANUS: _hamburg(55.8983, 77.25568, 0.0, 0.0, 0.0, 0.0),
    UranianBody.POSEIDON: _hamburg(165.5163, 83.66907, 0.0, 0.0, 0.0, 0.0),
    UranianBody.TRANSPLUTO: UranianOrbitElements(
        epoch_jd_tt=2368547.66,
        equinox_jd_tt=2431456.5,
        mean_anomaly_deg=0.0,
        semimajor_axis_au=77.775,
        eccentricity=0.3,
        argument_of_perihelion_deg=0.7,
        ascending_node_deg=0.0,
        inclination_deg=0.0,
        body_group="transpluto",
        source_family=_TRANSPLUTO_SOURCE,
    ),
}


@dataclass(frozen=True, slots=True)
class UranianPosition:
    """Apparent geocentric position of one conventional hypothetical body."""

    name: str
    longitude: float
    latitude: float
    distance_au: float
    speed: float
    retrograde: bool
    body_group: str
    source_family: str
    model: str = URANIAN_MODEL
    frame: str = URANIAN_FRAME
    sign: str = field(init=False)
    sign_symbol: str = field(init=False)
    sign_degree: float = field(init=False)

    def __post_init__(self) -> None:
        sign, symbol, degree = sign_of(self.longitude)
        object.__setattr__(self, "sign", sign)
        object.__setattr__(self, "sign_symbol", symbol)
        object.__setattr__(self, "sign_degree", degree)

    def __repr__(self) -> str:
        deg = int(self.sign_degree)
        mins = int((self.sign_degree - deg) * 60)
        motion = "R" if self.retrograde else "D"
        return (
            f"{self.name}: {self.sign_symbol}{self.sign} "
            f"{deg:02d}°{mins:02d}'  (lon {self.longitude:.4f}°, "
            f"lat {self.latitude:+.4f}°, speed {self.speed:+.5f}°/day {motion})"
        )


def _transpose(matrix):
    return tuple(tuple(matrix[row][column] for row in range(3)) for column in range(3))


def _solve_eccentric_anomaly(mean_anomaly_rad: float, eccentricity: float) -> float:
    """Solve Kepler's equation for the admitted low-eccentricity orbits."""

    eccentric_anomaly = mean_anomaly_rad
    for _ in range(12):
        residual = (
            eccentric_anomaly
            - eccentricity * math.sin(eccentric_anomaly)
            - mean_anomaly_rad
        )
        correction = residual / (1.0 - eccentricity * math.cos(eccentric_anomaly))
        eccentric_anomaly -= correction
        if abs(correction) < 1.0e-14:
            return eccentric_anomaly
    raise ArithmeticError("Uranian Kepler solver did not converge")


def _heliocentric_icrf_km(elements: UranianOrbitElements, jd_tt: float):
    """Materialize the source orbit as a heliocentric ICRF vector in km."""

    mean_anomaly = (
        elements.mean_anomaly_deg
        + elements.mean_motion_deg_per_day * (jd_tt - elements.epoch_jd_tt)
    ) % 360.0
    eccentric_anomaly = _solve_eccentric_anomaly(mean_anomaly * DEG2RAD, elements.eccentricity)

    x_orbit = elements.semimajor_axis_au * (
        math.cos(eccentric_anomaly) - elements.eccentricity
    )
    y_orbit = (
        elements.semimajor_axis_au
        * math.sqrt(1.0 - elements.eccentricity**2)
        * math.sin(eccentric_anomaly)
    )

    argument = elements.argument_of_perihelion_deg * DEG2RAD
    node = elements.ascending_node_deg * DEG2RAD
    inclination = elements.inclination_deg * DEG2RAD
    cos_arg, sin_arg = math.cos(argument), math.sin(argument)
    cos_node, sin_node = math.cos(node), math.sin(node)
    cos_inc, sin_inc = math.cos(inclination), math.sin(inclination)

    # Periapsis and transverse unit vectors in the elements' source ecliptic.
    periapsis = (
        cos_node * cos_arg - sin_node * sin_arg * cos_inc,
        sin_node * cos_arg + cos_node * sin_arg * cos_inc,
        sin_arg * sin_inc,
    )
    transverse = (
        -cos_node * sin_arg - sin_node * cos_arg * cos_inc,
        -sin_node * sin_arg + cos_node * cos_arg * cos_inc,
        cos_arg * sin_inc,
    )
    x_ecl = x_orbit * periapsis[0] + y_orbit * transverse[0]
    y_ecl = x_orbit * periapsis[1] + y_orbit * transverse[1]
    z_ecl = x_orbit * periapsis[2] + y_orbit * transverse[2]

    source_obliquity = mean_obliquity(elements.equinox_jd_tt) * DEG2RAD
    source_equatorial = (
        x_ecl,
        y_ecl * math.cos(source_obliquity) - z_ecl * math.sin(source_obliquity),
        y_ecl * math.sin(source_obliquity) + z_ecl * math.cos(source_obliquity),
    )
    source_to_icrf = _transpose(precession_matrix_equatorial(elements.equinox_jd_tt))
    x_icrf, y_icrf, z_icrf = mat_vec_mul(source_to_icrf, source_equatorial)
    return x_icrf * KM_PER_AU, y_icrf * KM_PER_AU, z_icrf * KM_PER_AU


def _position_at_tt(name: str, jd_tt: float, reader: KernelReader, context):
    elements = _URANIAN_ELEMENTS[name]

    def barycentric_fn(_body_name: str, sample_tt: float, active_reader: KernelReader):
        sun_ssb = _barycentric(
            Body.SUN,
            sample_tt,
            active_reader,
            context.vector_cache,
        )
        return vec_add(sun_ssb, _heliocentric_icrf_km(elements, sample_tt))

    if context.earth_ssb is None or context.earth_vel is None:
        raise RuntimeError("Uranian apparent-place context lacks Earth state")
    return _apparent_geocentric_ecliptic(
        name,
        jd_tt,
        reader,
        barycentric_fn=barycentric_fn,
        deflectors=_deflectors_for_body(name, jd_tt, reader, context),
        earth_ssb=context.earth_ssb,
        earth_vel=context.earth_vel,
        obliquity=context.obliquity,
        rot_mat=context.rot_mat,
    )


def _resolve_reader(reader: KernelReader | None) -> KernelReader:
    if reader is not None:
        return reader
    active = get_active_reader()
    if active is None:
        raise MissingKernelError(
            "No planetary kernel is provided and no active reader context was found. "
            "Pass a reader explicitly or use the Moira facade."
        )
    return active


def _validate_inputs(name: str, jd_ut: float) -> UranianOrbitElements:
    try:
        elements = _URANIAN_ELEMENTS[name]
    except KeyError:
        valid = ", ".join(_URANIAN_ELEMENTS)
        raise KeyError(f"Unknown Uranian body {name!r}. Valid names: {valid}") from None
    if not math.isfinite(jd_ut):
        raise ValueError("jd_ut must be finite")
    return elements


def _positions_for_names(
    names: tuple[str, ...],
    jd_ut: float,
    reader: KernelReader,
) -> dict[str, UranianPosition]:
    jd_tt = _ut1_to_ephemeris_tt(jd_ut, reader)
    samples = (
        jd_tt - _LONGITUDE_RATE_STEP_DAYS,
        jd_tt,
        jd_tt + _LONGITUDE_RATE_STEP_DAYS,
    )
    contexts = {
        sample: _build_apparent_context(sample, reader, apparent=True, nutation=True)
        for sample in samples
    }

    results: dict[str, UranianPosition] = {}
    for name in names:
        elements = _URANIAN_ELEMENTS[name]
        longitude, latitude, distance_km = _position_at_tt(
            name,
            jd_tt,
            reader,
            contexts[jd_tt],
        )
        longitude_minus = _position_at_tt(
            name,
            samples[0],
            reader,
            contexts[samples[0]],
        )[0]
        longitude_plus = _position_at_tt(
            name,
            samples[2],
            reader,
            contexts[samples[2]],
        )[0]
        longitude_delta = (longitude_plus - longitude_minus + 540.0) % 360.0 - 180.0
        speed = longitude_delta / (2.0 * _LONGITUDE_RATE_STEP_DAYS)
        results[name] = UranianPosition(
            name=name,
            longitude=longitude,
            latitude=latitude,
            distance_au=distance_km / KM_PER_AU,
            speed=speed,
            retrograde=speed < 0.0,
            body_group=elements.body_group,
            source_family=elements.source_family,
        )
    return results


def uranian_at(
    name: str,
    jd_ut: float,
    reader: KernelReader | None = None,
) -> UranianPosition:
    """Return one apparent geocentric hypothetical-body position.

    ``jd_ut`` is UT1. A planetary kernel is required for Earth/Sun observer
    geometry; the hypothetical body itself is generated only from the
    source-receipted fixed orbital elements above.
    """

    _validate_inputs(name, jd_ut)
    return _positions_for_names((name,), jd_ut, _resolve_reader(reader))[name]


def all_uranian_at(
    jd_ut: float,
    reader: KernelReader | None = None,
) -> dict[str, UranianPosition]:
    """Return all nine positions in canonical Hamburg-plus-Transpluto order."""

    if not math.isfinite(jd_ut):
        raise ValueError("jd_ut must be finite")
    return _positions_for_names(UranianBody.ALL, jd_ut, _resolve_reader(reader))


def list_uranian() -> list[str]:
    """Return the admitted hypothetical-body names in canonical order."""

    return list(UranianBody.ALL)
