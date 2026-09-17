"""Pinned JPL Horizons gravity policy for Stage 1 orbital elements.

Values are copied from JPL Horizons' official ``gm_Horizons.pck`` artifact
retrieved on 2026-09-15.  They stay bound to the content-derived DE440/DE441
planetary identity that supplied the state; filenames never establish that
identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._orbital_errors import OrbitalGravityModelError


HORIZONS_GM_POLICY = "HORIZONS_GM_2026_09_15"
HORIZONS_GM_SOURCE_URL = (
    "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/gm_Horizons.pck"
)
HORIZONS_GM_RETRIEVED_DATE = "2026-09-15"
HORIZONS_GM_SOURCE_BYTES = 15428
HORIZONS_GM_SOURCE_SHA256 = (
    "169cfed3b0927e73929d0a1b5c931f9afb5167a83b921064127ffc54a673df0c"
)
ADMITTED_PLANETARY_EPHEMERIDES = ("DE440", "DE441")
SECONDS_PER_DAY = 86400.0


# JPL Horizons mass parameters, km^3/s^2.  Integer keys are NAIF identities.
HORIZONS_GM_KM3_S2: dict[int, float] = {
    10: 132712440041.27942,
    1: 22031.868551400003,
    2: 324858.592,
    3: 403503.2356254802,
    4: 42828.37442560939,
    5: 126712761.8414429,
    6: 37940584.92052428,
    7: 5794556.3999999985,
    8: 6836531.640925204,
    9: 975.4308664317557,
    199: 22031.868551400003,
    299: 324858.592,
    399: 398600.43550702266,
    301: 4902.80011845755,
}


@dataclass(frozen=True, slots=True)
class _OrbitalGravity:
    """One selected two-body gravitational parameter and its source receipt."""

    rule: str
    gm_km3_s2: float
    gm_km3_day2: float
    component_naif_ids: tuple[int, ...]
    component_gm_km3_s2: tuple[float, ...]
    policy: str
    source_url: str
    retrieved_date: str
    source_sha256: str
    source_bytes: int
    planetary_ephemeris: str | None


def _require_admitted_identity(identity: object) -> str:
    planetary_ephemeris = getattr(identity, "planetary_ephemeris", None)
    summary_label = getattr(identity, "summary_label", None)
    if planetary_ephemeris not in ADMITTED_PLANETARY_EPHEMERIDES:
        raise OrbitalGravityModelError(
            planetary_ephemeris,
            summary_label,
            ADMITTED_PLANETARY_EPHEMERIDES,
        )
    return planetary_ephemeris


def select_orbital_gravity(
    *,
    center_key: str,
    body_kind: str,
    naif_id: int,
    identity: object,
) -> _OrbitalGravity:
    """Select the pinned two-body GM for one admitted body/center pairing."""

    planetary_ephemeris = _require_admitted_identity(identity)
    if center_key == "EARTH" and body_kind == "MOON" and naif_id == 301:
        rule = "EARTH_PLUS_MOON"
        components = (399, 301)
    elif center_key == "SUN" and body_kind in {"ASTEROID", "COMET"}:
        rule = "SUN_MASSLESS_TARGET"
        components = (10,)
    elif center_key == "SUN" and body_kind == "EARTH_MOON_BARYCENTER":
        rule = "SUN_PLUS_EARTH_MOON_SYSTEM"
        components = (10, 3)
    elif center_key == "SUN" and body_kind == "PLANET_SYSTEM_BARYCENTER":
        rule = "SUN_PLUS_PLANET_SYSTEM"
        components = (10, naif_id)
    elif center_key == "SUN" and body_kind == "PLANET_BODY":
        rule = "SUN_PLUS_PLANET_BODY"
        components = (10, naif_id)
    else:
        raise OrbitalGravityModelError(
            planetary_ephemeris,
            getattr(identity, "summary_label", None),
            ADMITTED_PLANETARY_EPHEMERIDES,
        )

    values = tuple(HORIZONS_GM_KM3_S2[component] for component in components)
    gm_km3_s2 = sum(values)
    return _OrbitalGravity(
        rule=rule,
        gm_km3_s2=gm_km3_s2,
        gm_km3_day2=gm_km3_s2 * SECONDS_PER_DAY**2,
        component_naif_ids=components,
        component_gm_km3_s2=values,
        policy=HORIZONS_GM_POLICY,
        source_url=HORIZONS_GM_SOURCE_URL,
        retrieved_date=HORIZONS_GM_RETRIEVED_DATE,
        source_sha256=HORIZONS_GM_SOURCE_SHA256,
        source_bytes=HORIZONS_GM_SOURCE_BYTES,
        planetary_ephemeris=planetary_ephemeris,
    )


__all__ = [
    "ADMITTED_PLANETARY_EPHEMERIDES",
    "HORIZONS_GM_KM3_S2",
    "HORIZONS_GM_POLICY",
    "HORIZONS_GM_RETRIEVED_DATE",
    "HORIZONS_GM_SOURCE_BYTES",
    "HORIZONS_GM_SOURCE_SHA256",
    "HORIZONS_GM_SOURCE_URL",
]
