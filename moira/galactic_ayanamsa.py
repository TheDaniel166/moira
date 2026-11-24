"""Galactic anchor conventions for Moira's typed sidereal calculations.

Owns the preset definitions, the reduction of each anchor to an ecliptic
longitude, and its provenance. Uses Moira's fixed Sgr A* catalogue direction,
IAU 2006 precession and obliquity, and IAU 2000A nutation in Moira's 06A stack.
The Galactic-plane presets use the published poles specified below.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .ayanamsa_doctrine import (
    FAMILY_GALACTIC_ANCHOR,
    LAYER_MODERN_CONVENTION,
    AyanamsaDoctrine,
    GalacticAyanamsa,
    _DoctrinalResolution,
    polar_longitude,
)
from .constants import J2000
from .coordinates import (
    Vec3,
    icrf_to_ecliptic,
    mat_vec_mul,
    nutation_matrix_from_terms,
    precession_matrix_equatorial,
    rot_x_axis,
)
from .cosmic_references import cosmic_reference_definition
from .julian import centuries_from_j2000
from .obliquity import mean_obliquity, nutation

__all__ = ["GalacticAyanamsa"]

_SAGITTARIUS_A_ID = "sagittarius_a_star"
_MULA_MIDPOINT_DEG = 240.0 + 20.0 / 3.0
_P03_LIMIT_CENTURIES = 50.0
_ASTRODIENST_URL = "https://www.astro.com/swisseph/swisseph.htm"
_WILHELM_2001_URL = "https://www.indiadivine.org/content/topic/1178279-ayanamsha-and-galactic-center/"


@dataclass(frozen=True, slots=True)
class _GalacticPole:
    """Published ICRS north pole of a specific plane at J2000."""

    identity: str
    ra_deg: float
    dec_deg: float
    authority: str
    source_url: str
    angle_uncertainties_deg: tuple[float, float] | None = None


# Liu et al. (2024), Eqs. (30) and (35). Subtract 90° from the equatorial
# ascending node and subtract the plane inclination from 90° for declination.
_ALLWISE_2024 = _GalacticPole(
    "allwise_2024", 192.936, 26.602,
    "Liu et al. (2024), AJ 168:170, section 5",
    "https://doi.org/10.3847/1538-3881/ad6dd5",
    (0.055, 0.032),
)
# Liu, Zhu & Zhang (2011), section 4. The proposed pole is the closest to
# the transformed 1958 pole whose equator goes through the J2000 Sgr A* vector.
_LIU_2011 = _GalacticPole(
    "liu_zhu_zhang_2011", 192.9029799920833, 27.1031092144444,
    "Liu, Zhu & Zhang (2011), A&A 526 A16, section 4",
    "https://arxiv.org/html/1010.3773",
)


@dataclass(frozen=True, slots=True)
class _Preset:
    """Sidereal target, projection, and source for one selection."""

    name: str
    target_deg: float
    definition: str
    convention_url: str
    pole: _GalacticPole | None = None
    hour_circle: bool = False
    caveats: tuple[str, ...] = ()

    @property
    def coordinate(self) -> str:
        """Return the coordinate used to fix the sidereal target."""
        if self.pole is not None:
            return "galactic_node"
        return "polar" if self.hour_circle else "ecliptic"


_PRESETS = {
    "centre_sagittarius": _Preset(
        "Galactic Centre at 0° Sagittarius", 240.0,
        "Fix the ecliptic longitude of Sgr A* at 0° Sagittarius.",
        _ASTRODIENST_URL,
    ),
    "centre_gil_brand": _Preset(
        "Galactic Centre (Gil Brand)",
        210.0 + 90.0 * (3.0 - math.sqrt(5.0)) / 2.0,
        "Fix Sgr A* at the golden section from 0° Scorpio toward 0° Aquarius, "
        "with the shorter segment on the Scorpio side.",
        "https://www.astrologie-zentrum.net/index.php/de/publikationen?catid=8&id=5%3Aumrechnung&view=article",
    ),
    "centre_cochrane": _Preset(
        "Galactic Centre (Cochrane)", 270.0,
        "Fix the ecliptic longitude of Sgr A* at 0° Capricorn.",
        "https://www.astrosoftware.com/cpnew/a_and_v/ayanamsha.html",
    ),
    "centre_wilhelm": _Preset(
        "Galactic Centre (Wilhelm Dhruva)", _MULA_MIDPOINT_DEG,
        "Fix the ecliptic point at Sgr A*'s right ascension at 6°40′ Sagittarius.",
        _ASTRODIENST_URL,
        hour_circle=True,
        caveats=("Astrodienst documents the hour-circle construction.",),
    ),
    "centre_mid_mula": _Preset(
        "Galactic Centre at Mid-Mūla", _MULA_MIDPOINT_DEG,
        "Fix the direct ecliptic longitude of Sgr A* at 6°40′ Sagittarius.",
        _WILHELM_2001_URL,
        caveats=("Wilhelm's 2001 custom offset supports a direct interpretation "
                 "to within about 5 arcseconds at J2000.",),
    ),
    "equator_allwise_2024": _Preset(
        "Galactic Equator (AllWISE 2024)", 240.0,
        "Fix the Sagittarius-side ecliptic node of the AllWISE plane at 0° Sagittarius.",
        _ASTRODIENST_URL,
        pole=_ALLWISE_2024,
        caveats=("Uses the 0° Sagittarius convention with the Gaia-calibrated AllWISE plane fit.",),
    ),
    "equator_liu_2011": _Preset(
        "Galactic Equator (Liu 2011)", 240.0,
        "Fix the Sagittarius-side ecliptic node of the 2011 proposed plane at 0° Sagittarius.",
        _ASTRODIENST_URL,
        pole=_LIU_2011,
    ),
    "equator_liu_2011_mid_mula": _Preset(
        "Galactic Equator Mid-Mūla (Liu 2011)", _MULA_MIDPOINT_DEG,
        "Fix the Sagittarius-side ecliptic node of the 2011 proposed plane at 6°40′ Sagittarius "
        "and the antipodal node at 6°40′ Gemini.",
        _ASTRODIENST_URL,
        pole=_LIU_2011,
    ),
}


def _get_preset(preset: str) -> _Preset:
    if not isinstance(preset, str) or preset not in _PRESETS:
        choices = ", ".join(_PRESETS)
        raise ValueError(f"Unknown Galactic ayanamsa preset {preset!r}. Choose one of {choices}.")
    return _PRESETS[preset]


def _galactic_doctrine(system: GalacticAyanamsa) -> AyanamsaDoctrine:
    preset = _get_preset(system.preset)
    if preset.pole is None:
        reference = cosmic_reference_definition(_SAGITTARIUS_A_ID)
        identity = reference.name
        sources = (*reference.citation_urls, preset.convention_url)
        caveats = ("Uses the fixed ICRS catalogue direction at J2000.", *preset.caveats)
    else:
        identity = preset.pole.authority
        sources = (preset.pole.source_url, preset.convention_url)
        caveats = preset.caveats

    return AyanamsaDoctrine(
        system=preset.name,
        family=FAMILY_GALACTIC_ANCHOR,
        layer=LAYER_MODERN_CONVENTION,
        definition=preset.definition,
        anchor_identification=identity,
        anchor_target_deg=preset.target_deg,
        anchor_coordinate=preset.coordinate,
        sources=sources,
        caveats=caveats,
    )


def _icrs_direction(ra_deg: float, dec_deg: float) -> Vec3:
    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)
    cos_dec = math.cos(dec)
    return (cos_dec * math.cos(ra), cos_dec * math.sin(ra), math.sin(dec))


def _resolve_galactic_ayanamsa(
    jd_tt: float, system: GalacticAyanamsa, mode: str,
) -> _DoctrinalResolution:
    """Project the chosen fixed ICRS anchor in the requested ecliptic of date."""
    # The shared precession matrix switches to Vondrák outside this interval.
    # This technique uses the coherent P03 precession and obliquity pair.
    if abs(centuries_from_j2000(jd_tt)) > _P03_LIMIT_CENTURIES:
        raise ValueError("Galactic ayanamsas require a TT date within ±50 Julian centuries of J2000")

    preset = _get_preset(system.preset)
    pole = preset.pole
    if pole is None:
        reference = cosmic_reference_definition(_SAGITTARIUS_A_ID)
        ra_deg, dec_deg = reference.icrs_ra_deg, reference.icrs_dec_deg
        anchor_id = reference.reference_id
        anchor_epoch = reference.source_epoch_jd_tt
        anchor_authority = reference.coordinate_authority
        anchor_url = reference.citation_urls[0]
        anchor_kind = "physical_compact_source"
    else:
        ra_deg, dec_deg = pole.ra_deg, pole.dec_deg
        anchor_id = pole.identity
        anchor_epoch = J2000
        anchor_authority = pole.authority
        anchor_url = pole.source_url
        anchor_kind = "galactic_plane"

    equatorial = mat_vec_mul(precession_matrix_equatorial(jd_tt), _icrs_direction(ra_deg, dec_deg))
    obliquity_deg = mean_obliquity(jd_tt)
    dpsi = None
    equinox = "mean_of_date"
    if mode == "true":
        dpsi, deps = nutation(jd_tt)
        equatorial = mat_vec_mul(nutation_matrix_from_terms(obliquity_deg, dpsi, deps), equatorial)
        obliquity_deg += deps
        equinox = "true_of_date"

    if pole is None:
        longitude, latitude, _ = icrf_to_ecliptic(equatorial, obliquity_deg)
        direct_longitude = longitude
        if preset.hour_circle:
            if equatorial[0] == equatorial[1] == 0.0:
                raise ValueError("Sgr A* at a celestial pole has no defined hour circle")
            longitude = polar_longitude(longitude, latitude, obliquity_deg)
        projection_terms = (
            ("sgr_a_ecliptic_longitude_deg", direct_longitude),
            ("sgr_a_ecliptic_latitude_deg", latitude),
        )
        if preset.hour_circle:
            projection_terms += (("sgr_a_polar_longitude_deg", longitude),)
    else:
        pole_x, pole_y, _ = mat_vec_mul(rot_x_axis(math.radians(obliquity_deg)), equatorial)
        # In ecliptic axes the oriented intersection north_ecliptic × north_galactic
        # is (-pole_y, pole_x, 0). It is on the Sgr A* side at J2000 for both
        # published poles. Keep that orientation as the equinox moves.
        if pole_x == pole_y == 0.0:
            raise ValueError("Coincident ecliptic and Galactic planes have no unique node")
        longitude = math.degrees(math.atan2(pole_x, -pole_y)) % 360.0
        projection_terms = (("opposite_node_tropical_longitude_deg", (longitude + 180.0) % 360.0),)
        if pole.angle_uncertainties_deg is not None:
            ra_uncertainty, dec_uncertainty = pole.angle_uncertainties_deg
            projection_terms += (
                ("pole_ra_uncertainty_deg", ra_uncertainty),
                ("pole_dec_uncertainty_deg", dec_uncertainty),
            )

    return _DoctrinalResolution(
        value_deg=longitude - preset.target_deg,
        effective_path=f"fixed_icrs_{preset.coordinate}_of_date",
        anchor_target_deg=preset.target_deg,
        anchor_tropical_longitude_deg=longitude,
        anchor_source_mode="fixed_icrs_geometry",
        nutation_longitude_deg=dpsi,
        terms=(
            ("preset", system.preset),
            ("anchor_kind", anchor_kind),
            ("anchor_id", anchor_id),
            ("anchor_coordinate", preset.coordinate),
            ("anchor_icrs_ra_deg", ra_deg),
            ("anchor_icrs_dec_deg", dec_deg),
            ("anchor_reference_epoch_jd_tt", anchor_epoch),
            ("anchor_source_frame", "ICRS"),
            ("anchor_coordinate_authority", anchor_authority),
            ("anchor_coordinate_source_url", anchor_url),
            ("sidereal_target_source_url", preset.convention_url),
            ("equinox", equinox),
            ("obliquity_deg", obliquity_deg),
            ("precession_model", "IAU 2006 P03 with frame bias"),
            ("correction_policy", "fixed_icrs_with_2000a_nutation" if mode == "true" else "fixed_icrs_mean"),
            *projection_terms,
        ),
    )
