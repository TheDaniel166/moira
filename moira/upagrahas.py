"""
Moira — Upagraha Engine (sub-planets)
======================================

Archetype: Engine

Purpose
-------
Computes the classical upagrahas in their two source-distinct groups:

**Group A — kalavelas (time-division upagrahas)**, BPHS Ch. 3 (Santhanam)
66-70: the day (sunrise-to-sunset) or night (sunset-to-next-sunrise) arc is
divided into eight equal parts; parts 1-7 take the seven planets in
weekday order starting from the day lord (day) or from the lord of the
5th weekday counted inclusively (night); the 8th part is lordless.
Kala = the Sun's portion, Mrityu = Mars's, Ardhaprahara = Mercury's,
Yamaghantaka = Jupiter's, Gulika = Saturn's (Moon's and Venus's portions
carry no kalavela).  Each upagraha materializes as **the ascendant degree
rising at its portion's defining instant** (BPHS 3.70 — every consulted
source concurs on the lagna materialization).

**Group B — Sun-derived upagrahas**, BPHS Ch. 3.61-64: an exact arithmetic
chain from the Sun's longitude — Dhuma = Sun + 133°20'; Vyatipata =
360° − Dhuma; Parivesha = Vyatipata + 180°; Indrachapa = 360° − Parivesha;
Upaketu = Indrachapa + 16°40'.  The verse states its own self-check:
**Upaketu + 30° ≡ Sun** — enforced here as a source-owned invariant.

Ambiguity policy (declared; the primaries genuinely disagree)
-------------------------------------------------------------
* ``portion_point``: the defining instant within the portion —
  ``'beginning'`` (default; BPHS 3.70 "the degree ascending at the time of
  START of Gulika's portion", Santhanam emphatic three times) |
  ``'middle'`` (PVR/JHora Gulika default) | ``'end'`` (Uttara Kalamrita
  I.8; Jataka Parijata commentary; Prasna Marga).  Applied symmetrically
  day and night — no source states a day/night asymmetry.
* ``mandi_mode``: ``'alias_of_gulika'`` (default; BPHS Ch. 4.15
  quarter-verse "Mandi is merely another name of the same"; Phaladeepika;
  Prasna Marga practice) | ``'distinct_kalidasa_table'`` (Uttara Kalamrita
  I.7: day offsets [26,22,18,14,10,6,2] ghatis x D/30 after sunrise,
  night [10,6,2,26,22,18,14] x D/30 after sunset, Sun..Sat — a genuinely
  third scheme, not reproducible from the 8-fold division).
* ``lord_sequence``: ``'contiguous'`` (default; BPHS/UK/JP/PM — seven
  lords in parts 1-7, part 8 lordless) | ``'lordless_after_saturn'``
  (PVR/JHora: the part after Saturn's is lordless, then the Sun resumes;
  never moves Gulika, shifts the other kalavelas on most days).
* Weekday: the Vedic day runs sunrise to sunrise — a night belongs to the
  weekday of the preceding sunrise (JP's Friday-night worked example).
* The dignity table sometimes circulated for Group B is NOT BPHS
  (Santhanam attributes it to Jatakalankara) and is not implemented.

Sources
-------
BPHS Ch. 3.61-70 (Santhanam, both archive.org scans); Jataka Parijata
Adh. II.6 + commentary; Uttara Kalamrita I.7-8; Phaladeepika Ch. 25.2-5;
Prasna Marga Ch. 5.14-16 (Raman); PVR Narasimha Rao (JHora conventions).
"""

import math
from dataclasses import dataclass

__all__ = [
    "UpagrahaPolicy",
    "SunBasedUpagrahas",
    "KalavelaUpagraha",
    "KalavelaResult",
    "sun_based_upagrahas",
    "kalavela_upagrahas",
]

# Weekday-lord cycle (index 0 = Sunday).
_WEEKDAY_LORDS: tuple[str, ...] = (
    'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
)

# Kalavela <-> planet portion (BPHS 3.66-69).  Moon and Venus portions
# carry no kalavela.
_KALAVELA_OF_PLANET: dict[str, str] = {
    'Sun': 'Kala',
    'Mars': 'Mrityu',
    'Mercury': 'Ardhaprahara',
    'Jupiter': 'Yamaghantaka',
    'Saturn': 'Gulika',
}

# Uttara Kalamrita I.7 Mandi table: ghatis after sunrise (day) / after
# sunset (night) on a nominal 30-ghati arc, indexed Sunday..Saturday.
_KALIDASA_MANDI_DAY_GHATIS: tuple[float, ...] = (26.0, 22.0, 18.0, 14.0, 10.0, 6.0, 2.0)
_KALIDASA_MANDI_NIGHT_GHATIS: tuple[float, ...] = (10.0, 6.0, 2.0, 26.0, 22.0, 18.0, 14.0)


@dataclass(frozen=True, slots=True)
class UpagrahaPolicy:
    """Explicit doctrine switches (defaults are BPHS-primary)."""

    portion_point: str = 'beginning'
    mandi_mode: str = 'alias_of_gulika'
    lord_sequence: str = 'contiguous'

    def __post_init__(self) -> None:
        if self.portion_point not in ('beginning', 'middle', 'end'):
            raise ValueError(
                f"portion_point must be 'beginning', 'middle', or 'end', "
                f"got {self.portion_point!r}"
            )
        if self.mandi_mode not in ('alias_of_gulika', 'distinct_kalidasa_table'):
            raise ValueError(
                f"mandi_mode must be 'alias_of_gulika' or "
                f"'distinct_kalidasa_table', got {self.mandi_mode!r}"
            )
        if self.lord_sequence not in ('contiguous', 'lordless_after_saturn'):
            raise ValueError(
                f"lord_sequence must be 'contiguous' or "
                f"'lordless_after_saturn', got {self.lord_sequence!r}"
            )


# ---------------------------------------------------------------------------
# Group B — Sun-derived (BPHS 3.61-64): exact arithmetic, no options
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SunBasedUpagrahas:
    """
    The five Sun-derived upagrahas (same zodiacal frame as the input Sun:
    sidereal in, sidereal out).

    The BPHS 3.64 self-check (Upaketu + 30° ≡ Sun) is enforced at
    construction — a rare source-owned invariant.
    """

    sun_longitude: float
    dhuma: float
    vyatipata: float
    parivesha: float
    indrachapa: float
    upaketu: float

    def __post_init__(self) -> None:
        residual = abs(
            ((self.upaketu + 30.0) - self.sun_longitude + 180.0) % 360.0
            - 180.0
        )
        if residual > 1e-9:
            raise ValueError(
                "BPHS 3.64 self-check failed: Upaketu + 30 deg must equal "
                f"the Sun's longitude (residual {residual} deg)"
            )


def sun_based_upagrahas(sun_sidereal_lon: float) -> SunBasedUpagrahas:
    """
    Compute Dhuma, Vyatipata, Parivesha, Indrachapa, and Upaketu from the
    Sun's longitude per BPHS 3.61-64.

    Chain: Dhuma = Sun + 133°20'; Vyatipata = 360° − Dhuma; Parivesha =
    Vyatipata + 180°; Indrachapa = 360° − Parivesha; Upaketu =
    Indrachapa + 16°40'.  Verse-stated identity: Upaketu + 30° ≡ Sun.
    """
    sun = sun_sidereal_lon % 360.0
    dhuma = (sun + 133.0 + 20.0 / 60.0) % 360.0
    vyatipata = (360.0 - dhuma) % 360.0
    parivesha = (vyatipata + 180.0) % 360.0
    indrachapa = (360.0 - parivesha) % 360.0
    upaketu = (indrachapa + 16.0 + 40.0 / 60.0) % 360.0
    return SunBasedUpagrahas(
        sun_longitude=sun,
        dhuma=dhuma,
        vyatipata=vyatipata,
        parivesha=parivesha,
        indrachapa=indrachapa,
        upaketu=upaketu,
    )


# ---------------------------------------------------------------------------
# Group A — kalavelas (BPHS 3.66-70): time-division + lagna materialization
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KalavelaUpagraha:
    """
    One kalavela upagraha, materialized as the ascendant at its defining
    instant (BPHS 3.70).

    Attributes
    ----------
    name : str
        'Gulika' | 'Kala' | 'Mrityu' | 'Ardhaprahara' | 'Yamaghantaka'
        | 'Mandi' (when distinct by policy).
    portion_planet : str or None
        The planet whose portion defines it (None for the Kalidasa-table
        Mandi, which is not an 8th-division portion).
    part_index : int or None
        1-8 position of the portion within the arc (None for table Mandi).
    defining_jd : float
        UT Julian date of the defining instant.
    sidereal_longitude : float
        Sidereal ascendant longitude at the defining instant.
    tropical_longitude : float
        Tropical ascendant longitude at the defining instant.
    """

    name: str
    portion_planet: str | None
    part_index: int | None
    defining_jd: float
    sidereal_longitude: float
    tropical_longitude: float


@dataclass(frozen=True, slots=True)
class KalavelaResult:
    """
    All kalavela upagrahas for one birth.

    Attributes
    ----------
    is_day_birth : bool
    weekday_index : int
        0 = Sunday, of the governing sunrise's day (a night belongs to the
        weekday of the preceding sunrise).
    arc_start_jd / arc_end_jd : float
        The containing day-arc or night-arc bounds (UT JD).
    policy : UpagrahaPolicy
    upagrahas : dict[str, KalavelaUpagraha]
    """

    is_day_birth: bool
    weekday_index: int
    arc_start_jd: float
    arc_end_jd: float
    ayanamsa_system: str
    policy: UpagrahaPolicy
    upagrahas: dict[str, KalavelaUpagraha]


def _sun_events(jd: float, lat: float, lon: float, reader) -> dict[str, float]:
    from .rise_set import find_phenomena

    return find_phenomena('Sun', jd, lat, lon)


def _solar_frame(
    jd_ut: float, lat: float, lon: float, reader,
) -> tuple[float, float, float]:
    """
    Return (sunrise_before, sunset_after_that_sunrise, next_sunrise)
    bracketing *jd_ut*.
    """
    rises: list[float] = []
    sets: list[float] = []
    for offset in (-2.0, -1.0, 0.0):
        events = _sun_events(jd_ut + offset, lat, lon, reader)
        if 'Rise' in events:
            rises.append(events['Rise'])
        if 'Set' in events:
            sets.append(events['Set'])
    past_rises = [r for r in rises if r <= jd_ut]
    future_rises = [r for r in rises if r > jd_ut]
    if not past_rises or not future_rises:
        raise ValueError(
            "Could not bracket the birth between sunrises — polar "
            "conditions or kernel coverage issue."
        )
    sunrise_prev = max(past_rises)
    sunrise_next = min(future_rises)
    following_sets = [s for s in sets if s > sunrise_prev]
    if not following_sets:
        raise ValueError("No sunset found after the governing sunrise.")
    sunset = min(following_sets)
    return sunrise_prev, sunset, sunrise_next


def _ascendant_at(
    jd_ut: float, lat: float, lon: float, ayanamsa_system: str,
) -> tuple[float, float]:
    """(sidereal, tropical) ascendant longitude at *jd_ut*."""
    from .houses import calculate_houses
    from .constants import HouseSystem
    from .sidereal import tropical_to_sidereal

    asc_trop = calculate_houses(
        jd_ut, lat, lon, system=HouseSystem.EQUAL,
    ).asc % 360.0
    asc_sid = tropical_to_sidereal(
        asc_trop, jd_ut, system=ayanamsa_system,
    ) % 360.0
    return asc_sid, asc_trop


def _part_lords(start_lord_index: int, sequence_mode: str) -> list[str | None]:
    """The eight part-lords for one arc (None = lordless part)."""
    cycle = [
        _WEEKDAY_LORDS[(start_lord_index + i) % 7] for i in range(7)
    ]
    if sequence_mode == 'contiguous':
        return cycle + [None]        # parts 1-7 lorded, 8th lordless
    # PVR/JHora: the part after Saturn's is lordless; the remaining lords
    # continue after it.  Saturn's position in the cycle stays unchanged.
    saturn_pos = cycle.index('Saturn')
    return (
        cycle[:saturn_pos + 1]
        + [None]
        + cycle[saturn_pos + 1:]
    )


def kalavela_upagrahas(
    jd_ut: float,
    latitude: float,
    longitude: float,
    ayanamsa_system: str = 'Lahiri',
    policy: UpagrahaPolicy | None = None,
    reader=None,
) -> KalavelaResult:
    """
    Compute the kalavela upagrahas (Gulika, Kala, Mrityu, Ardhaprahara,
    Yamaghantaka, and Mandi per policy) for a birth moment and place.

    The containing day- or night-arc is divided into eight equal parts
    (BPHS 3.66-69); each upagraha's defining instant is the policy-selected
    point of its planet's portion; its longitude is the ascendant rising
    at that instant (BPHS 3.70).
    """
    policy = policy or UpagrahaPolicy()
    sunrise, sunset, next_sunrise = _solar_frame(
        jd_ut, latitude, longitude, reader,
    )
    is_day = jd_ut < sunset
    # The doctrine is the weekday at the governing *local* sunrise.  No civil
    # timezone is available at this engine boundary, so use the same explicit
    # local-mean-solar convention as planetary_hours: longitude / 360 day.
    weekday_index = math.floor(sunrise + longitude / 360.0 + 1.5) % 7

    if is_day:
        arc_start, arc_end = sunrise, sunset
        start_lord_index = weekday_index
    else:
        arc_start, arc_end = sunset, next_sunrise
        # Night: lords start from the 5th weekday lord counted inclusively.
        start_lord_index = (weekday_index + 4) % 7

    duration = arc_end - arc_start
    part = duration / 8.0
    lords = _part_lords(start_lord_index, policy.lord_sequence)
    fraction = {'beginning': 0.0, 'middle': 0.5, 'end': 1.0}[policy.portion_point]

    upagrahas: dict[str, KalavelaUpagraha] = {}
    for part_index, lord in enumerate(lords, start=1):
        if lord not in _KALAVELA_OF_PLANET:
            continue
        name = _KALAVELA_OF_PLANET[lord]
        t = arc_start + (part_index - 1) * part + fraction * part
        asc_sid, asc_trop = _ascendant_at(t, latitude, longitude, ayanamsa_system)
        upagrahas[name] = KalavelaUpagraha(
            name=name,
            portion_planet=lord,
            part_index=part_index,
            defining_jd=t,
            sidereal_longitude=asc_sid,
            tropical_longitude=asc_trop,
        )

    if policy.mandi_mode == 'alias_of_gulika':
        g = upagrahas['Gulika']
        upagrahas['Mandi'] = KalavelaUpagraha(
            name='Mandi',
            portion_planet='Saturn',
            part_index=g.part_index,
            defining_jd=g.defining_jd,
            sidereal_longitude=g.sidereal_longitude,
            tropical_longitude=g.tropical_longitude,
        )
    else:
        # Uttara Kalamrita I.7 table: ghatis after arc start, scaled by
        # the actual arc length over the nominal 30 ghatis.
        table = (
            _KALIDASA_MANDI_DAY_GHATIS if is_day
            else _KALIDASA_MANDI_NIGHT_GHATIS
        )
        ghatis = table[weekday_index]
        t = arc_start + duration * (ghatis / 30.0)
        asc_sid, asc_trop = _ascendant_at(t, latitude, longitude, ayanamsa_system)
        upagrahas['Mandi'] = KalavelaUpagraha(
            name='Mandi',
            portion_planet=None,
            part_index=None,
            defining_jd=t,
            sidereal_longitude=asc_sid,
            tropical_longitude=asc_trop,
        )

    return KalavelaResult(
        is_day_birth=is_day,
        weekday_index=weekday_index,
        arc_start_jd=arc_start,
        arc_end_jd=arc_end,
        ayanamsa_system=ayanamsa_system,
        policy=policy,
        upagrahas=upagrahas,
    )
