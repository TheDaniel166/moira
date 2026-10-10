"""Narrow, source-defined strength components; no ephemeris side effects."""

from __future__ import annotations

from dataclasses import dataclass
from .shadbala_context import ShadbalaContextError, SEVEN, SAPTAVARGAJA_PROFILES


@dataclass(frozen=True, slots=True)
class SaptavargajaEntry:
    """One source-defined sign, relationship and award."""

    division: int
    sign_index: int
    lord: str
    dignity: str
    shashtiamsas: float


def strength_varga_sign(lon: float, n: int) -> int:
    """BPHS divisions for Saptavargaja; public generic harmonics stay separate."""
    from .varga import _varga_partition, varga_sign_index

    lon, segment, _ = _varga_partition(lon, n)
    sign = int(lon // 30)
    part = segment % n
    if n == 7:
        return (sign + (0 if sign % 2 == 0 else 6) + part) % 12
    if n == 12:
        return (sign + part) % 12
    if n == 30:
        degree = lon % 30
        edges = (
            ((5, 0), (10, 10), (18, 8), (25, 2), (30, 6))
            if sign % 2 == 0
            else ((5, 1), (12, 5), (20, 11), (25, 9), (30, 7))
        )
        return next(s for edge, s in edges if degree < edge)
    return varga_sign_index(lon, n)


def saptavargaja_breakdown(planet, longitude, positions, profile="raman_1996"):
    """Raman article 30 / BPHS 27.2-4 scale, D1 compound relationships.

    Both selected scales apply Moolatrikona to D1 only. Actual D1 degrees
    determine that state. Temporary friendship is 2,3,4,10,11,12 (Raman 25).
    """
    from .vedic_dignities import (
        MULATRIKONA_SIGN,
        MULATRIKONA_START,
        MULATRIKONA_END,
        OWN_SIGNS,
        _natural_relationship,
        _temporary_relationship,
        _compound_relationship,
    )
    from .varga import _normalize_longitude

    if profile not in SAPTAVARGAJA_PROFILES:
        raise ValueError("unknown Saptavargaja profile")
    if positions is None or any(p not in positions for p in SEVEN):
        raise ShadbalaContextError(
            "Saptavargaja requires all seven D1 relationship positions"
        )
    normalized = {p: _normalize_longitude(positions[p]) for p in SEVEN}
    lon = _normalize_longitude(longitude)
    if planet not in normalized or normalized[planet] != lon:
        raise ShadbalaContextError("Saptavargaja planet/position mismatch")
    lords = (
        "Mars",
        "Venus",
        "Mercury",
        "Moon",
        "Sun",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Saturn",
        "Jupiter",
    )
    weights = dict(
        zip(
            (
                "mulatrikona",
                "own_sign",
                "adhi_mitra",
                "mitra",
                "sama",
                "shatru",
                "adhi_shatru",
            ),
            (45.0, 30.0, 22.5, 15.0, 7.5, 3.75, 1.875)
            if profile == "raman_1996"
            else (45.0, 30.0, 20.0, 15.0, 10.0, 4.0, 2.0),
        )
    )
    d1 = int(lon // 30)
    entries = []
    for n in (1, 2, 3, 7, 9, 12, 30):
        sign = strength_varga_sign(lon, n)
        lord = lords[sign]
        if (
            n == 1
            and sign == MULATRIKONA_SIGN[planet]
            and MULATRIKONA_START[planet] <= lon % 30 < MULATRIKONA_END[planet]
        ):
            dignity = "mulatrikona"
        elif sign in OWN_SIGNS[planet]:
            dignity = "own_sign"
        else:
            temporary = _temporary_relationship(d1, int(normalized[lord] // 30))
            dignity = _compound_relationship(
                _natural_relationship(planet, lord), temporary
            )
        entries.append(SaptavargajaEntry(n, sign, lord, dignity, weights[dignity]))
    return tuple(entries)


def positional_components(planet, longitude):
    """House-independent Uchcha, Ojayugma and Drekkana owner formulas."""
    from .vedic_dignities import vedic_dignity
    from .varga import _normalize_longitude, varga_sign_index

    lon = _normalize_longitude(longitude)
    uchcha = vedic_dignity(planet, lon).exaltation_score * 60.0
    parity = 1 if planet in ('Moon', 'Venus') else 0
    ojayugma = 15.0 * sum(sign % 2 == parity for sign in
                         (int(lon // 30), varga_sign_index(lon, 9)))
    decan = int((lon % 30.0) / 10.0) + 1
    strong_decan = (1 if planet in ('Sun', 'Mars', 'Jupiter') else
                    2 if planet in ('Mercury', 'Saturn') else 3)
    drekkana = 15.0 if decan == strong_decan else 0.0
    return uchcha, ojayugma, drekkana


def kala_components(planet, context):
    """Raman 47-57,75; true declination in the stated 24-degree linear formula.

    Actual latitude can put declination outside +/-24 degrees. The formula
    remains signed there; no undisclosed clipping changes the source algebra.
    Mercury association is explicitly a Moira same-sign convention unless
    a supplied benefic/malefic classification overrides it.
    """
    context.require_complete()
    positions = dict(context.sidereal_longitudes)
    phase = (positions["Moon"] - positions["Sun"]) % 360
    moon_benefic = 84 <= phase < 264  # named start-of-eighth-tithi boundaries
    f = context.local_apparent_day_fraction
    day = min(f, 1 - f) * 120
    natha = (
        60.0
        if planet == "Mercury"
        else day
        if planet in ("Sun", "Jupiter", "Venus")
        else 60 - day
    )
    mercury_benefic = context.mercury_nature == "benefic"
    if context.mercury_nature == "same_sign_malefic_association":
        malefics = ("Sun", "Mars", "Saturn") + (() if moon_benefic else ("Moon",))
        mercury_benefic = all(
            int(positions["Mercury"] // 30) != int(positions[p] // 30) for p in malefics
        )
    benefic = (
        planet in ("Jupiter", "Venus")
        or (planet == "Moon" and moon_benefic)
        or (planet == "Mercury" and mercury_benefic)
    )
    bright = min(phase, 360 - phase) / 3
    paksha = (bright if benefic else 60 - bright) * (2 if planet == "Moon" else 1)
    lo, hi = (
        (context.sunrise_jd, context.sunset_jd)
        if context.is_day
        else (context.sunset_jd, context.next_sunrise_jd)
    )
    # Compare to constructed boundaries, avoiding a rounded quotient at thirds.
    third = sum(context.jd >= lo + (hi - lo) * i / 3 for i in (1, 2))
    lord = (
        ("Mercury", "Sun", "Saturn") if context.is_day else ("Moon", "Venus", "Mars")
    )[third]
    tribhaga = 60.0 if planet in ("Jupiter", lord) else 0.0
    amvh = sum(
        value
        for p, value in (
            (context.abda_lord, 15.0),
            (context.masa_lord, 30.0),
            (context.vara_lord, 45.0),
            (context.hora_lord, 60.0),
        )
        if p == planet
    )
    dec = dict(context.declinations)[planet]
    signed = (
        abs(dec)
        if planet == "Mercury"
        else -dec
        if planet in ("Moon", "Saturn")
        else dec
    )
    ayana = (24 + signed) * 60 / 48 * (2 if planet == "Sun" else 1)
    return natha, paksha, tribhaga, amvh, ayana
