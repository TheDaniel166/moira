"""Named symbolic longitudes and geometric points, separate from physical bodies.

Baker Vulcan follows the documented Solar Fire/Baker rule, not an orbit.
Priapus is the perigee of the explicitly selected Moira lunar apogee model.
The second focus is a central-focus-relative geometric vector of an ellipse;
it is neither an apocenter nor an apparent geocentric body position.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._ephemeris_time import _bind_ephemeris_time
from .julian import ut_to_tt
from .nodes import TrueLilithReductionTruth, mean_lilith, true_lilith_with_truth
from .orbits import (
    OrbitalCenter, OrbitalFrame, OrbitShape, OsculatingElements,
    osculating_elements,
)
from .planets import planet_at
from .spk_reader import KernelReader, MissingKernelError, get_active_reader

__all__ = [
    "DerivedPointDefinition", "BakerVulcanPoint", "PriapusPoint",
    "SecondFocusStatus", "OrbitalSecondFocus", "derived_point_catalog",
    "baker_vulcan_from_longitudes", "baker_vulcan_at", "mean_priapus",
    "osculating_priapus", "second_focus_from_elements", "orbital_second_focus",
]

_BAKER_SOURCE = "https://www.esotech.com.au/SFHelp/vulcan_calculation.htm"


@dataclass(frozen=True, slots=True)
class DerivedPointDefinition:
    """One admitted, explicitly named point model and its computational boundary."""

    id: str
    name: str
    kind: str
    definition: str
    kernel_required: bool
    source: str


def derived_point_catalog() -> tuple[DerivedPointDefinition, ...]:
    """Return model-specific identities without adding fictitious NAIF bodies."""
    return (
        DerivedPointDefinition(
            "baker_vulcan", "Baker Vulcan", "symbolic_longitude",
            "Mercury moved 3 degrees toward Sun, clamped at Sun; longitude only.",
            True, _BAKER_SOURCE,
        ),
        DerivedPointDefinition(
            "mean_priapus", "Mean Priapus", "mean_lunar_perigee",
            "Antipode of Moira mean lunar apogee in the same selected frame.",
            False, "moira.nodes.mean_lilith; IERS Conventions 2003 section 5.7.2",
        ),
        DerivedPointDefinition(
            "osculating_priapus", "Osculating Priapus", "osculating_lunar_perigee",
            "Antipode of Moira osculating lunar apogee, retaining its source truth.",
            True, "moira.nodes.true_lilith_with_truth",
        ),
        DerivedPointDefinition(
            "orbital_second_focus", "Orbital second focus", "geometric_point",
            "F2 = -2 a e_vector, relative to the selected central focus; elliptic only.",
            True, "Euclidean ellipse geometry; moira.orbits.osculating_elements",
        ),
    )


@dataclass(frozen=True, slots=True)
class BakerVulcanPoint:
    """Longitude-only Baker convention with its actual input longitudes and clock."""

    longitude: float
    sun_longitude: float
    mercury_longitude: float
    frame: str
    jd_ut: float | None = None
    epoch_tt: float | None = None
    epoch_tdb: float | None = None
    kernel_identity: str | None = None
    model: str = "baker_vulcan"
    kind: str = "symbolic_longitude"
    source: str = _BAKER_SOURCE


@dataclass(frozen=True, slots=True)
class PriapusPoint:
    """Selected lunar perigee, with the unmodified parent apogee receipt."""

    name: str
    model: str
    longitude: float
    speed: float
    jd_ut: float
    epoch_tt: float
    frame: str
    speed_method: str
    source_apogee_longitude: float
    source_apogee_truth: TrueLilithReductionTruth | None
    kind: str = "lunar_perigee"


class SecondFocusStatus(str, Enum):
    """Whether an elliptic second focus has an admitted direction or vector."""

    DEFINED = "DEFINED"
    COINCIDENT_FOCI = "COINCIDENT_FOCI"
    CIRCULAR_DIRECTION_UNDEFINED = "CIRCULAR_DIRECTION_UNDEFINED"
    NON_ELLIPTIC = "NON_ELLIPTIC"


@dataclass(frozen=True, slots=True)
class OrbitalSecondFocus:
    """Central-focus-relative geometry retaining the complete source elements."""

    status: SecondFocusStatus
    vector_au: tuple[float, float, float] | None
    longitude: float | None
    latitude: float | None
    distance_au: float | None
    source_elements: OsculatingElements
    model: str = "elliptic_second_focus"
    kind: str = "geometric_point"
    origin: str = "selected_central_focus"
    formula: str = "F2 = -2 a e_vector"


def _finite_real(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite real number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be a finite real number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite real number")
    return result


def _reader_or_active(reader: KernelReader | None) -> KernelReader:
    resolved = get_active_reader() if reader is None else reader
    if resolved is None:
        raise MissingKernelError("Pass a reader explicitly or use the Moira facade.")
    return resolved


def baker_vulcan_from_longitudes(
    sun_longitude: float, mercury_longitude: float,
) -> BakerVulcanPoint:
    """Apply Baker's 3-degree rule to longitudes in one caller-supplied frame.

    Inputs are normalized separately before subtraction. The shortest arc
    selects the side of Sun; exactly antipodal inputs are ambiguous and raise
    ValueError. No distance, latitude, speed, or physical orbit is inferred.
    """
    sun = _finite_real(sun_longitude, "sun_longitude") % 360.0
    mercury = _finite_real(mercury_longitude, "mercury_longitude") % 360.0
    separation = (mercury - sun + 180.0) % 360.0 - 180.0
    if abs(separation) == 180.0:
        raise ValueError("Antipodal Sun/Mercury inputs have no unique toward-Sun arc")
    offset = math.copysign(max(abs(separation) - 3.0, 0.0), separation)
    return BakerVulcanPoint(
        longitude=(sun + offset) % 360.0,
        sun_longitude=sun, mercury_longitude=mercury,
        frame="caller_supplied_common_longitude_frame",
    )


def baker_vulcan_at(
    jd_ut: float, *, reader: KernelReader | None = None,
) -> BakerVulcanPoint:
    """Apply Baker's rule to Moira apparent geocentric true-of-date longitudes.

    The input epoch is UT1; Sun and Mercury use the ordinary admitted planetary
    reduction defaults. The resulting symbolic longitude is not itself a
    received-light or gravitationally deflected physical body.
    """
    epoch = _finite_real(jd_ut, "jd_ut")
    resolved = _reader_or_active(reader)
    bound = _bind_ephemeris_time(epoch, resolved)
    sun = planet_at("Sun", epoch, reader=resolved)
    mercury = planet_at("Mercury", epoch, reader=resolved)
    result = baker_vulcan_from_longitudes(sun.longitude, mercury.longitude)
    return BakerVulcanPoint(
        longitude=result.longitude, sun_longitude=result.sun_longitude,
        mercury_longitude=result.mercury_longitude,
        frame="apparent_geocentric_true_ecliptic_of_date_inputs",
        jd_ut=epoch, epoch_tt=bound.epoch_tt, epoch_tdb=bound.epoch_tdb,
        kernel_identity=bound.identity.summary_label,
    )


def mean_priapus(jd_ut: float, *, nutation: bool = True) -> PriapusPoint:
    """Return the mean lunar perigee, exactly opposite the selected mean apogee.

    The inherited IERS polynomial speed excludes the derivative of nutation,
    even when nutation=True. This is not Selena or interpolated/natural Priapus.
    """
    epoch = _finite_real(jd_ut, "jd_ut")
    if not isinstance(nutation, bool):
        raise ValueError("nutation must be a Boolean")
    apogee = mean_lilith(epoch, nutation=nutation)
    return PriapusPoint(
        name="Mean Priapus", model="mean_priapus",
        longitude=(apogee.longitude + 180.0) % 360.0, speed=apogee.speed,
        jd_ut=epoch, epoch_tt=ut_to_tt(epoch),
        frame=("true_ecliptic_and_equinox_of_date" if nutation
               else "mean_ecliptic_and_equinox_of_date"),
        speed_method="IERS_mean_apogee_polynomial_excluding_nutation_derivative",
        source_apogee_longitude=apogee.longitude, source_apogee_truth=None,
    )


def osculating_priapus(
    jd_ut: float, *, reader: KernelReader | None = None,
) -> PriapusPoint:
    """Return the osculating lunar perigee using the existing true-apogee model.

    The antipodal translation preserves the apogee's signed longitude speed,
    clock, Earth-Moon GM, frame and kernel identity without a second solver.
    """
    epoch = _finite_real(jd_ut, "jd_ut")
    apogee = true_lilith_with_truth(epoch, reader=_reader_or_active(reader))
    return PriapusPoint(
        name="Osculating Priapus", model="osculating_priapus",
        longitude=(apogee.result.longitude + 180.0) % 360.0,
        speed=apogee.result.speed, jd_ut=epoch, epoch_tt=apogee.truth.jd_tt,
        frame=apogee.truth.frame, speed_method=apogee.truth.speed_method,
        source_apogee_longitude=apogee.result.longitude,
        source_apogee_truth=apogee.truth,
    )


def second_focus_from_elements(elements: OsculatingElements) -> OrbitalSecondFocus:
    """Derive F2 = -2 a e_vector from admitted strict orbital elements.

    Coordinates use the source frame and central focus, without light time or
    observer translation. Non-elliptic conics return NON_ELLIPTIC with no vector
    or distance. At exactly zero eccentricity both foci coincide. For nonzero
    eccentricity below the source circular threshold only 2ae is available:
    the core deliberately withholds the undefined periapsis direction.
    """
    if elements.shape is not OrbitShape.ELLIPTIC:
        return OrbitalSecondFocus(
            SecondFocusStatus.NON_ELLIPTIC, None, None, None, None, elements,
        )
    a = elements.semi_major_axis_au
    e = elements.eccentricity
    if a is None or not math.isfinite(a) or a <= 0 or not 0 <= e < 1:
        raise ValueError("Elliptic source elements require finite a > 0 and 0 <= e < 1")
    distance = 2.0 * (a * e)
    if not math.isfinite(distance):
        raise ValueError("Second-focus distance is not finite")
    if e == 0:
        return OrbitalSecondFocus(
            SecondFocusStatus.COINCIDENT_FOCI, (0.0, 0.0, 0.0),
            None, None, 0.0, elements,
        )
    if e < elements.provenance.singularity_thresholds.circular_e_tolerance:
        return OrbitalSecondFocus(
            SecondFocusStatus.CIRCULAR_DIRECTION_UNDEFINED,
            None, None, None, distance, elements,
        )
    lon = elements.pericenter_ecliptic_lon_deg
    lat = elements.pericenter_ecliptic_lat_deg
    if (lon is None or lat is None or not all(map(math.isfinite, (lon, lat)))
            or abs(lat) > 90.0):
        raise ValueError("Noncircular source elements require finite periapsis direction")
    if abs(lat) == 90.0:
        return OrbitalSecondFocus(
            SecondFocusStatus.DEFINED, (0.0, 0.0, -math.copysign(distance, lat)),
            None, -lat, distance, elements,
        )
    longitude = (lon + 180.0) % 360.0
    latitude = -lat
    lam, beta = math.radians(longitude), math.radians(latitude)
    vector = (
        distance * math.cos(beta) * math.cos(lam),
        distance * math.cos(beta) * math.sin(lam),
        distance * math.sin(beta),
    )
    return OrbitalSecondFocus(
        SecondFocusStatus.DEFINED, vector, longitude, latitude, distance, elements,
    )


def orbital_second_focus(
    body: str | int, jd_ut: float, *, center: OrbitalCenter,
    frame: OrbitalFrame, reader: KernelReader | None = None,
) -> OrbitalSecondFocus:
    """Compute a second focus using strict core body, center and frame admission.

    Center and frame are required choices, just as in osculating_elements.
    Its typed resource, identity, coverage and time errors propagate unchanged.
    """
    return second_focus_from_elements(osculating_elements(
        body, jd_ut, center=center, frame=frame, reader=reader,
    ))
