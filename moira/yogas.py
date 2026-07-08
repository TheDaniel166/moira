"""
Moira — Yoga Engine
====================

Archetype: Engine

Purpose
-------
Detects classical Vedic planetary combinations (yogas) and reports each as
a *proof object*: every formation condition individually evaluated with
what was actually observed, every cancellation (bhanga) rule evaluated
first-class, and the source citation carried on the result.  A yoga is
never a bare boolean — the derivation is the product.

Governing object
----------------
A yoga is a named classical rule.  Its evaluation yields:

  * ``conditions``    — the formation clauses, each with observed truth;
  * ``cancellations`` — the bhanga clauses, likewise evaluated;
  * ``formed``        — all formation clauses hold;
  * ``cancelled``     — formed, but a bhanga clause holds;
  * ``present``       — formed, not cancelled, not precedence-suppressed;
  * ``suppressed_by`` — the doctrine-level precedence suppressor, if any
                        (Nabhasa yogas are exclusive per BPHS).

Ambiguity policy (declared before implementation)
-------------------------------------------------
* House frame: whole-sign houses from the sidereal lagna sign — the
  classical yoga frame.  Moon-referenced yogas count whole signs from the
  Moon.  No cusp arithmetic participates.
* Benefic/malefic doctrine: BPHS Ch. 3 conditional classification —
  Jupiter and Venus benefic; Sun, Mars, Saturn malefic; the Moon benefic
  when waxing and malefic when waning; Mercury benefic unless conjoined
  with a malefic.  ``YogaPolicy`` makes both conditionals explicit and
  overridable.
* Aspects: Vedic full sign aspects (graha drishti) — every planet aspects
  the 7th sign; Mars also 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th.
  Fractional aspect weights do not participate in yoga formation.
* Participants: the seven classical planets.  Rahu/Ketu participate only
  where a specific rule names them (none in this engine's families).
* All longitudes are sidereal; conversion is the caller's responsibility.

Tradition and sources
---------------------
Parashara, "Brihat Parashara Hora Shastra" (BPHS), Santhanam translation —
primary authority (Nabhasa Adhyaya; Raja Yoga Adhyayas; Ch. 3 benefic
doctrine).  Mantreswara, "Phaladeepika" Ch. 6-7 — secondary.  Varahamihira,
"Brihat Jataka" Ch. 12-13 — classical cross-check.  B.V. Raman, "Three
Hundred Important Combinations" (1947) — engineering reference.  Each
YogaResult carries its own citation.

Boundary declaration
--------------------
Owns: yoga rule evaluation, the YogaCondition/YogaResult/YogaChartResult
      vessels, YogaPolicy, and the family evaluators.
Delegates: dignity ranks to ``moira.vedic_dignities``; nothing else.

Import-time side effects: None
"""

import math
from dataclasses import dataclass, field

__all__ = [
    "YogaPolicy",
    "YogaCondition",
    "YogaResult",
    "YogaChartResult",
    "benefic_malefic_classification",
    "pancha_mahapurusha_yogas",
    "chandra_yogas",
    "surya_yogas",
    "nabhasa_yogas",
    "raja_yogas",
    "dhana_yogas",
    "evaluate_yogas",
]

_SEVEN_PLANETS: tuple[str, ...] = (
    'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
)

_KENDRA_HOUSES: frozenset[int] = frozenset({1, 4, 7, 10})
_TRIKONA_HOUSES: frozenset[int] = frozenset({1, 5, 9})
_DUSTHANA_HOUSES: frozenset[int] = frozenset({6, 8, 12})

# Classical rasi lords by 0-based sign index (no nodal lordships).
_RASI_LORDS: tuple[str, ...] = (
    'Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury',
    'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter',
)

# Vedic full sign aspects (graha drishti): sign distances (1-based,
# counted inclusively from the aspecting planet) receiving a full aspect.
_FULL_ASPECT_DISTANCES: dict[str, frozenset[int]] = {
    'Sun':     frozenset({7}),
    'Moon':    frozenset({7}),
    'Mars':    frozenset({4, 7, 8}),
    'Mercury': frozenset({7}),
    'Jupiter': frozenset({5, 7, 9}),
    'Venus':   frozenset({7}),
    'Saturn':  frozenset({3, 7, 10}),
}


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class YogaPolicy:
    """
    Explicit doctrine switches for yoga evaluation.

    moon_benefic_mode : str
        ``'paksha'`` (BPHS Ch. 3: waxing benefic, waning malefic — default)
        or ``'always_benefic'``.
    mercury_benefic_mode : str
        ``'conditional'`` (BPHS Ch. 3: malefic when conjoined with a
        malefic — default) or ``'always_benefic'``.
    mahapurusha_reference : str
        ``'lagna'`` (kendra from lagna only — BPHS) or ``'lagna_or_moon'``
        (Phaladeepika/Raman admit kendras from the Moon as well).
    """

    moon_benefic_mode: str = 'paksha'
    mercury_benefic_mode: str = 'conditional'
    mahapurusha_reference: str = 'lagna'
    # Gajakesari: 'parashara' (BPHS 36.3-4 — kendra from lagna OR Moon,
    # plus benefic association and freedom from debilitation, combustion,
    # and inimical sign) or 'common' (PD 6.14 / Raman #1 — plain Jupiter
    # in kendra from the Moon, no gates).
    gajakesari_mode: str = 'parashara'
    # Budhaditya: Raman's >= 10 deg elongation caveat is modern, not mula
    # (Saravali 15.4 imposes none) — off by default.
    budhaditya_combustion_cancel: bool = False
    # Viparita Raja formulation — the three primaries define incompatible
    # house-sets: 'phaladeepika' (each dusthana lord in ANY of 6/8/12 —
    # PD 6.57, the naming source; default), 'uttara_kalamrita' (each lord
    # in the OTHER two dusthanas, with UK IV.22's unassociation clause),
    # 'raman' (each lord in its OWN dusthana, #109-111).
    viparita_mode: str = 'phaladeepika'

    def __post_init__(self) -> None:
        if self.moon_benefic_mode not in ('paksha', 'always_benefic'):
            raise ValueError(
                f"moon_benefic_mode must be 'paksha' or 'always_benefic', "
                f"got {self.moon_benefic_mode!r}"
            )
        if self.mercury_benefic_mode not in ('conditional', 'always_benefic'):
            raise ValueError(
                f"mercury_benefic_mode must be 'conditional' or "
                f"'always_benefic', got {self.mercury_benefic_mode!r}"
            )
        if self.mahapurusha_reference not in ('lagna', 'lagna_or_moon'):
            raise ValueError(
                f"mahapurusha_reference must be 'lagna' or 'lagna_or_moon', "
                f"got {self.mahapurusha_reference!r}"
            )
        if self.gajakesari_mode not in ('parashara', 'common'):
            raise ValueError(
                f"gajakesari_mode must be 'parashara' or 'common', "
                f"got {self.gajakesari_mode!r}"
            )
        if self.viparita_mode not in (
            'phaladeepika', 'uttara_kalamrita', 'raman',
        ):
            raise ValueError(
                f"viparita_mode must be 'phaladeepika', 'uttara_kalamrita', "
                f"or 'raman', got {self.viparita_mode!r}"
            )


# ---------------------------------------------------------------------------
# Result vessels — the proof objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class YogaCondition:
    """
    One evaluated clause of a yoga rule.

    Attributes
    ----------
    description : str
        The rule clause in words (source-faithful).
    satisfied : bool
        Whether the chart satisfies it.
    observed : str
        What was actually found in the chart (the evidence).
    """

    description: str
    satisfied: bool
    observed: str


@dataclass(frozen=True, slots=True)
class YogaResult:
    """
    Full evaluation of one yoga — the proof object.

    Attributes
    ----------
    name : str
        Classical yoga name (e.g. ``'Ruchaka'``, ``'Gajakesari'``).
    family : str
        ``'pancha_mahapurusha'`` | ``'chandra'`` | ``'surya'`` |
        ``'nabhasa'`` | ``'raja'`` | ``'dhana'``.
    formed : bool
        All formation conditions satisfied.
    cancelled : bool
        Formed, but at least one cancellation clause holds.
    present : bool
        ``formed and not cancelled and suppressed_by is None``.
    conditions : tuple[YogaCondition, ...]
        Every formation clause, satisfied or not.
    cancellations : tuple[YogaCondition, ...]
        Every bhanga clause evaluated (empty when the source defines none).
    participants : tuple[str, ...]
        Planets forming the yoga (empty when not formed).
    houses_involved : tuple[int, ...]
        Whole-sign houses (from the yoga's own reference point) involved.
    source : str
        Primary-source citation for the rule as implemented.
    suppressed_by : str or None
        Name of the yoga that suppresses this one under the source's
        precedence doctrine (Nabhasa exclusivity), else None.
    notes : str
        Doctrine notes (variant readings, policy switches applied).
    """

    name: str
    family: str
    formed: bool
    cancelled: bool
    present: bool
    conditions: tuple[YogaCondition, ...]
    cancellations: tuple[YogaCondition, ...] = ()
    participants: tuple[str, ...] = ()
    houses_involved: tuple[int, ...] = ()
    source: str = ''
    suppressed_by: str | None = None
    notes: str = ''

    def __post_init__(self) -> None:
        if self.present and not self.formed:
            raise ValueError(
                f"YogaResult {self.name!r}: present requires formed"
            )
        if self.present and self.cancelled:
            raise ValueError(
                f"YogaResult {self.name!r}: present and cancelled are exclusive"
            )
        if self.cancelled and not self.formed:
            raise ValueError(
                f"YogaResult {self.name!r}: cancelled requires formed"
            )


@dataclass(frozen=True, slots=True)
class YogaChartResult:
    """
    Every evaluated yoga for one chart.

    Attributes
    ----------
    lagna_sign_index : int
        Whole-sign lagna (0 = Aries) used as the house frame.
    policy : YogaPolicy
    yogas : tuple[YogaResult, ...]
        Every yoga the engine evaluated — present or not — so partial
        formations remain visible.
    present_names : tuple[str, ...]
        Names of the yogas with ``present=True`` (convenience).
    """

    lagna_sign_index: int
    policy: YogaPolicy
    yogas: tuple[YogaResult, ...]
    present_names: tuple[str, ...]

    def __post_init__(self) -> None:
        expected = tuple(y.name for y in self.yogas if y.present)
        if tuple(self.present_names) != expected:
            raise ValueError(
                "YogaChartResult.present_names must match the present yogas"
            )


# ---------------------------------------------------------------------------
# Shared helpers — the classical frame
# ---------------------------------------------------------------------------

def _sign(lon: float) -> int:
    return int(lon % 360.0 // 30)


def _house_from(reference_sign: int, target_sign: int) -> int:
    """Whole-sign house of *target_sign* counted from *reference_sign* (1-12)."""
    return (target_sign - reference_sign) % 12 + 1


def _planets_by_house(
    sidereal_longitudes: dict[str, float],
    reference_sign: int,
    include: tuple[str, ...] = _SEVEN_PLANETS,
) -> dict[int, list[str]]:
    """Whole-sign house occupancy (house -> planets) from a reference sign."""
    occupancy: dict[int, list[str]] = {}
    for planet in include:
        if planet not in sidereal_longitudes:
            continue
        house = _house_from(reference_sign, _sign(sidereal_longitudes[planet]))
        occupancy.setdefault(house, []).append(planet)
    return occupancy


def _sign_aspects(aspecting: str, from_sign: int, to_sign: int) -> bool:
    """Whether *aspecting* casts a full graha drishti from one sign to another."""
    dist = (to_sign - from_sign) % 12 + 1
    return dist in _FULL_ASPECT_DISTANCES.get(aspecting, frozenset())


def benefic_malefic_classification(
    sidereal_longitudes: dict[str, float],
    policy: YogaPolicy | None = None,
) -> dict[str, str]:
    """
    Classify the seven planets as ``'benefic'`` or ``'malefic'`` under the
    BPHS Ch. 3 conditional doctrine (policy-switchable).

    * Jupiter, Venus: benefic.  Sun, Mars, Saturn: malefic.
    * Moon: benefic when waxing (Moon at least 0° and less than 180° ahead
      of the Sun counts the bright fortnight from the conjunction), malefic
      when waning — under ``moon_benefic_mode='paksha'``.
    * Mercury: malefic when sharing a sign with a malefic (evaluated after
      the Moon's classification), else benefic — under
      ``mercury_benefic_mode='conditional'``.
    """
    policy = policy or YogaPolicy()
    result: dict[str, str] = {
        'Jupiter': 'benefic', 'Venus': 'benefic',
        'Sun': 'malefic', 'Mars': 'malefic', 'Saturn': 'malefic',
    }

    if policy.moon_benefic_mode == 'always_benefic':
        result['Moon'] = 'benefic'
    else:
        elongation = (
            sidereal_longitudes.get('Moon', 0.0)
            - sidereal_longitudes.get('Sun', 0.0)
        ) % 360.0
        result['Moon'] = 'benefic' if elongation < 180.0 else 'malefic'

    if policy.mercury_benefic_mode == 'always_benefic':
        result['Mercury'] = 'benefic'
    else:
        mercury_sign = _sign(sidereal_longitudes.get('Mercury', 0.0))
        with_malefic = any(
            _sign(sidereal_longitudes[p]) == mercury_sign
            for p in _SEVEN_PLANETS
            if p != 'Mercury'
            and p in sidereal_longitudes
            and result.get(p) == 'malefic'
        )
        result['Mercury'] = 'malefic' if with_malefic else 'benefic'

    return result


# ---------------------------------------------------------------------------
# Family 1 — Pancha Mahapurusha (BPHS Ch. 75 [Santhanam] 1-2)
#
# "When Mars, Mercury, Jupiter, Venus and Saturn being in their own sign or
#  in their sign of exaltation, be in kendra to the Ascendant, they give
#  rise to Ruchaka, Bhadra, Hamsa, Malavya and Sasa yogas respectively."
#
# Dignities: own sign or exaltation ONLY — no primary source (BPHS 75.1-2,
# Phaladeepika 6.1, Saravali 37.2) names moolatrikona.  (Moolatrikona is a
# subset of own sign for all five planets, so admitting it would change no
# result; it is omitted to stay source-faithful.)
#
# Cancellations: BPHS Ch. 75, Phaladeepika Ch. 6, and Saravali Ch. 37 state
# NONE.  Raman (#19-23) carries only a strength-attenuation doctrine
# ("balishta": a weak planet yields the yoga nominally, not effectively) —
# metadata, never a boolean cancel.  The popular combustion / navamsa-
# debilitation cancellation rules appear in NO consulted primary source and
# are intentionally not implemented.
#
# Reference point: kendra from the LAGNA (BPHS explicit).  Raman (Chart 19
# commentary) also admits kendras from the Moon — exposed as the
# ``mahapurusha_reference='lagna_or_moon'`` policy switch.
# ---------------------------------------------------------------------------

_MAHAPURUSHA_YOGAS: tuple[tuple[str, str], ...] = (
    ('Ruchaka', 'Mars'),
    ('Bhadra', 'Mercury'),
    ('Hamsa', 'Jupiter'),
    ('Malavya', 'Venus'),
    ('Sasa', 'Saturn'),
)

_MAHAPURUSHA_SOURCE = (
    "BPHS Ch. 75 (Santhanam) 1-2; Phaladeepika 6.1; Saravali 37.2; "
    "Raman, Three Hundred Important Combinations #19-23"
)


def pancha_mahapurusha_yogas(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: YogaPolicy | None = None,
) -> tuple[YogaResult, ...]:
    """
    Evaluate the five Mahapurusha yogas (Ruchaka, Bhadra, Hamsa, Malavya,
    Sasa) per BPHS Ch. 75.1-2.

    Formation: the yoga planet in its own or exaltation sign AND in a
    whole-sign kendra from the lagna (policy may also admit kendras from
    the Moon per Raman).  No classical cancellations exist; Raman's
    strength-attenuation is carried in the observed evidence, not as a
    cancel.
    """
    from .vedic_dignities import vedic_dignity

    policy = policy or YogaPolicy()
    lagna_sign = _sign(lagna_sidereal_lon)
    moon_sign = (
        _sign(sidereal_longitudes['Moon'])
        if 'Moon' in sidereal_longitudes else None
    )
    from .constants import SIGNS

    results: list[YogaResult] = []
    for name, planet in _MAHAPURUSHA_YOGAS:
        lon = sidereal_longitudes.get(planet)
        if lon is None:
            continue
        planet_sign = _sign(lon)
        dig = vedic_dignity(planet, lon)
        dignity_ok = dig.is_own_sign or dig.is_exalted
        dignity_observed = (
            f"{planet} in {SIGNS[planet_sign]} — "
            + ("exaltation" if dig.is_exalted
               else "own sign" if dig.is_own_sign
               else dig.dignity_rank)
        )

        house_lagna = _house_from(lagna_sign, planet_sign)
        kendra_lagna = house_lagna in _KENDRA_HOUSES
        if policy.mahapurusha_reference == 'lagna_or_moon' and moon_sign is not None:
            house_moon = _house_from(moon_sign, planet_sign)
            kendra_ok = kendra_lagna or (house_moon in _KENDRA_HOUSES)
            kendra_observed = (
                f"{planet} in H{house_lagna} from lagna"
                + f", H{house_moon} from Moon"
            )
            kendra_description = (
                "In a whole-sign kendra (1/4/7/10) from the lagna, or from "
                "the Moon (Raman variant admitted by policy)"
            )
        else:
            kendra_ok = kendra_lagna
            kendra_observed = f"{planet} in H{house_lagna} from lagna"
            kendra_description = (
                "In a whole-sign kendra (1/4/7/10) from the lagna (BPHS 75.1-2)"
            )

        conditions = (
            YogaCondition(
                description=(
                    f"{planet} in its own sign or sign of exaltation "
                    "(BPHS 75.1-2; moolatrikona named by no primary source)"
                ),
                satisfied=dignity_ok,
                observed=dignity_observed,
            ),
            YogaCondition(
                description=kendra_description,
                satisfied=kendra_ok,
                observed=kendra_observed,
            ),
        )

        formed = dignity_ok and kendra_ok
        results.append(YogaResult(
            name=name,
            family='pancha_mahapurusha',
            formed=formed,
            cancelled=False,
            present=formed,
            conditions=conditions,
            cancellations=(),
            participants=(planet,) if formed else (),
            houses_involved=(house_lagna,) if formed else (),
            source=_MAHAPURUSHA_SOURCE,
            notes=(
                "No classical cancellation exists (BPHS/Phaladeepika/"
                "Saravali state none); Raman's balishta doctrine is "
                "strength attenuation, not cancellation. Raman ranks the "
                "10th kendra strongest and exaltation above own sign."
            ),
        ))

    return tuple(results)


# ---------------------------------------------------------------------------
# Family 2 — Nabhasa (32) — BPHS Ch. 35 (Santhanam) 1-17; Brihat Jataka
# Ch. 12 (Sastri, with Bhattotpala's commentary); Phaladeepika 6.39-41
# (Sankhya group only).
#
# Participation: the seven classical planets only (PD 6.39 "from Sun to
# Saturn"); the lagna is the reference frame, never a participant.  Akriti
# patterns are whole-sign BHAVAS from the lagna; Sankhya counts distinct
# RASHIS (BJ 12.10 note).
#
# Occupancy semantics (declared doctrine): EXACT-SET — the set of occupied
# houses equals the named pattern.  BPHS 35.14's "seven continuous houses"
# clarifier and the akriti ("figure") concept support this reading; it
# renders all twenty Akriti patterns mutually exclusive.  The looser
# subset reading is recorded as rejected.
#
# Dala class doctrine (Bhattotpala on BJ 12.2, citing Garga/Badarayana):
# benefics = Mercury, Jupiter, Venus; malefics = Sun, Mars, Saturn; the
# Moon is left out of account entirely.  Vajra/Yava need all seven placed,
# so the Moon's class there follows the engine's paksha policy (a
# post-classical necessity the primaries leave open — noted on results).
#
# Precedence (BPHS 35.17; BJ 12.10, 12.12 with Bhattotpala):
#   Akriti > Dala > Ashraya > Sankhya, except Gola > Ashraya.
# Suppressed yogas remain visible with ``suppressed_by`` set.
# ---------------------------------------------------------------------------

_NABHASA_SOURCE_BPHS = "BPHS Ch. 35 (Santhanam)"
_NABHASA_SOURCE_BJ = "Brihat Jataka Ch. 12 (Sastri/Bhattotpala)"

# Dala-class planets (Moon excluded per Bhattotpala on BJ 12.2).
_DALA_BENEFICS: tuple[str, ...] = ('Mercury', 'Jupiter', 'Venus')
_DALA_MALEFICS: tuple[str, ...] = ('Sun', 'Mars', 'Saturn')

# Akriti patterns: name -> (exact occupied-house set variants, citation)
_AKRITI_PATTERNS: tuple[tuple[str, tuple[frozenset[int], ...], str], ...] = (
    ('Gada', (frozenset({1, 4}), frozenset({4, 7}),
              frozenset({7, 10}), frozenset({10, 1})),
     "BPHS 35.9; BJ 12.4"),
    ('Sakata', (frozenset({1, 7}),), "BPHS 35.9-11; BJ 12.4"),
    ('Vihaga', (frozenset({4, 10}),), "BPHS 35.9-11; BJ 12.4"),
    ('Sringataka', (frozenset({1, 5, 9}),), "BPHS 35.9-11; BJ 12.4"),
    ('Hala', (frozenset({2, 6, 10}), frozenset({3, 7, 11}),
              frozenset({4, 8, 12})),
     "BPHS 35.9-11; BJ 12.4"),
    ('Kamala', (frozenset({1, 4, 7, 10}),), "BPHS 35.12; BJ 12.5"),
    ('Vapi', (frozenset({2, 5, 8, 11}), frozenset({3, 6, 9, 12})),
     "BPHS 35.12; BJ 12.5"),
    ('Yupa', (frozenset({1, 2, 3, 4}),), "BPHS 35.13; BJ 12.7"),
    ('Ishu', (frozenset({4, 5, 6, 7}),), "BPHS 35.13; BJ 12.7"),
    ('Sakti', (frozenset({7, 8, 9, 10}),), "BPHS 35.13; BJ 12.7"),
    ('Danda', (frozenset({10, 11, 12, 1}),), "BPHS 35.13; BJ 12.7"),
    ('Nauka', (frozenset({1, 2, 3, 4, 5, 6, 7}),), "BPHS 35.14; BJ 12.8"),
    ('Koota', (frozenset({4, 5, 6, 7, 8, 9, 10}),), "BPHS 35.14; BJ 12.8"),
    ('Chatra', (frozenset({7, 8, 9, 10, 11, 12, 1}),), "BPHS 35.14; BJ 12.8"),
    ('Chapa', (frozenset({10, 11, 12, 1, 2, 3, 4}),), "BPHS 35.14; BJ 12.8"),
    # Ardha-Chandra: seven contiguous houses anchored at any NON-kendra
    # house (8 variants).  Formation authority is BJ 12.8 — the BPHS Ch. 35
    # text names the yoga and gives effects (35.40) but omits the
    # formation verse.
    ('Ardha-Chandra',
     tuple(
         frozenset(((anchor - 1 + k) % 12) + 1 for k in range(7))
         for anchor in (2, 3, 5, 6, 8, 9, 11, 12)
     ),
     "BJ 12.8 (formation; BPHS 35.40 effects only)"),
    ('Chakra', (frozenset({1, 3, 5, 7, 9, 11}),), "BPHS 35.15; BJ 12.9"),
    ('Samudra', (frozenset({2, 4, 6, 8, 10, 12}),), "BPHS 35.15; BJ 12.9"),
)

_SANKHYA_NAMES: dict[int, str] = {
    7: 'Vallaki', 6: 'Dama', 5: 'Pasa', 4: 'Kedara',
    3: 'Sula', 2: 'Yuga', 1: 'Gola',
}


def _describe_houses(occupied: frozenset[int]) -> str:
    return "{" + ", ".join(f"H{h}" for h in sorted(occupied)) + "}"


def nabhasa_yogas(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: YogaPolicy | None = None,
) -> tuple[YogaResult, ...]:
    """
    Evaluate all 32 Nabhasa yogas per BPHS Ch. 35 / Brihat Jataka Ch. 12.

    Every yoga is evaluated and returned; the source precedence doctrine
    (Akriti > Dala > Ashraya > Sankhya, except Gola > Ashraya) is applied
    via ``suppressed_by`` so exactly one Nabhasa yoga is ``present`` per
    chart while the full evaluation stays visible.
    """
    policy = policy or YogaPolicy()
    lagna_sign = _sign(lagna_sidereal_lon)

    planet_signs = {
        p: _sign(sidereal_longitudes[p])
        for p in _SEVEN_PLANETS if p in sidereal_longitudes
    }
    houses = {p: _house_from(lagna_sign, s) for p, s in planet_signs.items()}
    occupied = frozenset(houses.values())
    occupancy_observed = ", ".join(
        f"{p}=H{houses[p]}" for p in _SEVEN_PLANETS if p in houses
    )

    results: list[YogaResult] = []

    # --- Ashraya (sign modality; sign_idx % 3: 0 movable, 1 fixed, 2 dual) ---
    modalities = {p: s % 3 for p, s in planet_signs.items()}
    modality_observed = ", ".join(
        f"{p}={('movable', 'fixed', 'dual')[m]}" for p, m in modalities.items()
    )
    for name, modality_index, modality_name in (
        ('Rajju', 0, 'movable'), ('Musala', 1, 'fixed'), ('Nala', 2, 'dual'),
    ):
        formed = bool(modalities) and all(
            m == modality_index for m in modalities.values()
        )
        results.append(YogaResult(
            name=name,
            family='nabhasa',
            formed=formed,
            cancelled=False,
            present=formed,   # precedence applied below
            conditions=(YogaCondition(
                description=(
                    f"All seven planets in {modality_name} signs "
                    "(BPHS 35.7; BJ 12.2)"
                ),
                satisfied=formed,
                observed=modality_observed,
            ),),
            participants=tuple(p for p in _SEVEN_PLANETS if p in planet_signs)
            if formed else (),
            houses_involved=tuple(sorted(occupied)) if formed else (),
            source=f"{_NABHASA_SOURCE_BPHS} 35.7; {_NABHASA_SOURCE_BJ} 12.2",
            notes="Ashraya group; yields to Akriti/Dala and to Gola.",
        ))

    # --- Dala (benefics/malefics in kendras; Moon out of account) ---
    benefic_kendras = frozenset(
        houses[p] for p in _DALA_BENEFICS
        if p in houses and houses[p] in _KENDRA_HOUSES
    )
    malefic_kendras = frozenset(
        houses[p] for p in _DALA_MALEFICS
        if p in houses and houses[p] in _KENDRA_HOUSES
    )
    dala_observed = (
        f"benefic kendras {_describe_houses(benefic_kendras) if benefic_kendras else '{}'}"
        f"; malefic kendras {_describe_houses(malefic_kendras) if malefic_kendras else '{}'}"
        f"; Moon disregarded (H{houses.get('Moon', '?')})"
    )
    for name, own_class, own_kendras, other_kendras in (
        ('Mala', 'benefics (Me/Ju/Ve)', benefic_kendras, malefic_kendras),
        ('Sarpa', 'malefics (Su/Ma/Sa)', malefic_kendras, benefic_kendras),
    ):
        cond_three = YogaCondition(
            description=(
                f"The three {own_class} occupy three distinct kendras "
                "(Bhattotpala on BJ 12.2, citing Garga/Badarayana)"
            ),
            satisfied=len(own_kendras) == 3,
            observed=dala_observed,
        )
        cond_other = YogaCondition(
            description="The opposite class occupies no kendra",
            satisfied=len(other_kendras) == 0,
            observed=dala_observed,
        )
        formed = cond_three.satisfied and cond_other.satisfied
        results.append(YogaResult(
            name=name,
            family='nabhasa',
            formed=formed,
            cancelled=False,
            present=formed,
            conditions=(cond_three, cond_other),
            participants=(
                _DALA_BENEFICS if name == 'Mala' else _DALA_MALEFICS
            ) if formed else (),
            houses_involved=tuple(sorted(own_kendras)) if formed else (),
            source=f"{_NABHASA_SOURCE_BPHS} 35.8; {_NABHASA_SOURCE_BJ} 12.2",
            notes=(
                "Dala group; the Moon is left out of account entirely "
                "(Bhattotpala). Yields to Akriti; prevails over Sankhya."
            ),
        ))

    # --- Akriti (exact-set house patterns) ---
    classification = benefic_malefic_classification(sidereal_longitudes, policy)
    for name, variants, citation in _AKRITI_PATTERNS:
        matched = next((v for v in variants if occupied == v), None)
        if name in ('Vajra', 'Yava'):
            continue  # handled separately below (class-conditional)
        formed = matched is not None
        pattern_text = " or ".join(_describe_houses(v) for v in variants[:4])
        if len(variants) > 4:
            pattern_text += f" (any of {len(variants)} variants)"
        results.append(YogaResult(
            name=name,
            family='nabhasa',
            formed=formed,
            cancelled=False,
            present=formed,
            conditions=(YogaCondition(
                description=(
                    f"Occupied houses exactly equal {pattern_text} "
                    f"({citation}; exact-set doctrine)"
                ),
                satisfied=formed,
                observed=f"occupied {_describe_houses(occupied)}: {occupancy_observed}",
            ),),
            participants=tuple(p for p in _SEVEN_PLANETS if p in houses)
            if formed else (),
            houses_involved=tuple(sorted(matched)) if matched else (),
            source=citation,
            notes="Akriti group; prevails over Dala/Ashraya/Sankhya.",
        ))

    # Vajra / Yava — conjunctive class patterns (BJ 12.5).  All seven must
    # be placed, so the Moon takes its policy classification here.
    benefic_houses = frozenset(
        houses[p] for p in houses if classification[p] == 'benefic'
    )
    malefic_houses = frozenset(
        houses[p] for p in houses if classification[p] == 'malefic'
    )
    vajra_yava_observed = (
        f"benefics in {_describe_houses(benefic_houses) if benefic_houses else '{}'}"
        f", malefics in {_describe_houses(malefic_houses) if malefic_houses else '{}'}"
        f" (Moon classified {classification.get('Moon', '?')} by paksha policy)"
    )
    for name, ben_set, mal_set in (
        ('Vajra', frozenset({1, 7}), frozenset({4, 10})),
        ('Yava', frozenset({4, 10}), frozenset({1, 7})),
    ):
        cond_ben = YogaCondition(
            description=f"All benefics exclusively in {_describe_houses(ben_set)} (BJ 12.5)",
            satisfied=bool(benefic_houses) and benefic_houses == ben_set,
            observed=vajra_yava_observed,
        )
        cond_mal = YogaCondition(
            description=f"All malefics exclusively in {_describe_houses(mal_set)} (BJ 12.5)",
            satisfied=bool(malefic_houses) and malefic_houses == mal_set,
            observed=vajra_yava_observed,
        )
        formed = cond_ben.satisfied and cond_mal.satisfied
        results.append(YogaResult(
            name=name,
            family='nabhasa',
            formed=formed,
            cancelled=False,
            present=formed,
            conditions=(cond_ben, cond_mal),
            participants=tuple(p for p in _SEVEN_PLANETS if p in houses)
            if formed else (),
            houses_involved=tuple(sorted(ben_set | mal_set)) if formed else (),
            source=f"{_NABHASA_SOURCE_BPHS} 35.9-11; {_NABHASA_SOURCE_BJ} 12.5",
            notes=(
                "Conjunctive per BJ 12.5. The Moon's class here follows the "
                "engine's paksha policy — the primaries leave it open "
                "(Bhattotpala's Moon-exclusion is stated for Dala only). "
                "BJ 12.6 notes the rasi-chart formation is astronomically "
                "near-impossible (Mercury/Venus elongation)."
            ),
        ))

    # --- Sankhya (distinct rashis; residual class per BPHS 35.17) ---
    distinct_signs = len(frozenset(planet_signs.values()))
    signs_observed = (
        f"{distinct_signs} distinct rashi(s): "
        + ", ".join(f"{p}={s}" for p, s in planet_signs.items())
    )
    for count, name in _SANKHYA_NAMES.items():
        formed = distinct_signs == count
        results.append(YogaResult(
            name=name,
            family='nabhasa',
            formed=formed,
            cancelled=False,
            present=formed,
            conditions=(YogaCondition(
                description=(
                    f"The seven planets occupy exactly {count} distinct "
                    "rashis (BPHS 35.16-17; BJ 12.10; PD 6.39-41)"
                ),
                satisfied=formed,
                observed=signs_observed,
            ),),
            participants=tuple(p for p in _SEVEN_PLANETS if p in planet_signs)
            if formed else (),
            source="BPHS 35.16-17; BJ 12.10; Phaladeepika 6.39-41",
            notes=(
                "Sankhya group — residual: operable only when no other "
                "Nabhasa yoga forms (BPHS 35.17; BJ 12.10), except Gola, "
                "which prevails over Ashraya (Bhattotpala on BJ 12.12)."
            ),
        ))

    # --- Precedence doctrine (suppression pass) ---
    def _formed_names(family_names: tuple[str, ...]) -> list[str]:
        return [r.name for r in results if r.formed and r.name in family_names]

    akriti_names = tuple(n for n, _, _ in _AKRITI_PATTERNS)
    dala_names = ('Mala', 'Sarpa')
    ashraya_names = ('Rajju', 'Musala', 'Nala')
    sankhya_names = tuple(_SANKHYA_NAMES.values())

    formed_akriti = _formed_names(akriti_names)
    formed_dala = _formed_names(dala_names)
    formed_ashraya = _formed_names(ashraya_names)
    formed_gola = _formed_names(('Gola',))

    def _suppress(target_names: tuple[str, ...], by: str) -> None:
        for i, r in enumerate(results):
            if r.name in target_names and r.formed and r.present:
                results[i] = YogaResult(
                    name=r.name, family=r.family, formed=r.formed,
                    cancelled=r.cancelled, present=False,
                    conditions=r.conditions, cancellations=r.cancellations,
                    participants=r.participants,
                    houses_involved=r.houses_involved, source=r.source,
                    suppressed_by=by, notes=r.notes,
                )

    if formed_akriti:
        winner = formed_akriti[0]
        _suppress(dala_names, winner)
        _suppress(ashraya_names, winner)
        _suppress(sankhya_names, winner)
    elif formed_dala:
        winner = formed_dala[0]
        _suppress(ashraya_names, winner)
        _suppress(sankhya_names, winner)
    elif formed_ashraya:
        if formed_gola:
            # Gola prevails over Ashraya (Bhattotpala on BJ 12.12).
            _suppress(ashraya_names, 'Gola')
        else:
            _suppress(sankhya_names, formed_ashraya[0])
    # else: the Sankhya yoga (always exactly one forms) stands.

    return tuple(results)


# ---------------------------------------------------------------------------
# Family 3 — Chandra (lunar) yogas
#
# BPHS Ch. 36-37 (Santhanam); Brihat Jataka Ch. 13; Saravali Ch. 13;
# Phaladeepika 6.5-7, 6.42; Raman #1-7.
#
# Participation for the Sunapha class: "excepting the Sun" (BPHS 37.7-10;
# Saravali 13.1; BJ 13.3 "hitva arkam"), nodes never count — the five true
# planets Mars/Mercury/Jupiter/Venus/Saturn only.  Whole signs from the
# Moon; a planet conjunct the Moon does not create Sunapha/Anapha.
# ---------------------------------------------------------------------------

_SUNAPHA_PLANETS: tuple[str, ...] = (
    'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
)

# Classical combustion orb for Jupiter (Surya-Siddhanta lineage standard).
# BPHS 36.3-4 names combustion as a Gajakesari gate without stating an orb;
# the orb itself is therefore declared policy, not verse text.
_JUPITER_COMBUSTION_ORB_DEG = 11.0


def chandra_yogas(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: YogaPolicy | None = None,
) -> tuple[YogaResult, ...]:
    """
    Evaluate the lunar yoga family: Gajakesari, Sunapha, Anapha,
    Durudhara, Kemadruma (with its bhanga catalog), Adhi, Chandra-Mangala.
    """
    from .vedic_dignities import vedic_dignity
    from .constants import SIGNS

    policy = policy or YogaPolicy()
    lagna_sign = _sign(lagna_sidereal_lon)
    results: list[YogaResult] = []

    if 'Moon' not in sidereal_longitudes:
        return ()
    moon_sign = _sign(sidereal_longitudes['Moon'])

    # --- Gajakesari (BPHS 36.3-4) -----------------------------------------
    if 'Jupiter' in sidereal_longitudes:
        jup_lon = sidereal_longitudes['Jupiter']
        jup_sign = _sign(jup_lon)
        h_moon = _house_from(moon_sign, jup_sign)
        h_lagna = _house_from(lagna_sign, jup_sign)
        kendra_moon = h_moon in _KENDRA_HOUSES
        kendra_lagna = h_lagna in _KENDRA_HOUSES

        if policy.gajakesari_mode == 'common':
            conditions = [YogaCondition(
                description=(
                    "Jupiter in a kendra (1/4/7/10) from the Moon "
                    "(Phaladeepika 6.14; Raman #1 — common rule)"
                ),
                satisfied=kendra_moon,
                observed=f"Jupiter in H{h_moon} from the Moon",
            )]
            formed = kendra_moon
            gaja_notes = (
                "Common (PD/Raman) rule by policy; the BPHS 36.3-4 rule "
                "adds benefic association and freedom from debilitation, "
                "combustion, and inimical sign."
            )
        else:
            cond_kendra = YogaCondition(
                description=(
                    "Jupiter in a kendra from the lagna or from the Moon "
                    "(BPHS 36.3-4)"
                ),
                satisfied=kendra_lagna or kendra_moon,
                observed=(
                    f"Jupiter in H{h_lagna} from lagna, "
                    f"H{h_moon} from the Moon"
                ),
            )
            # Benefic association: conjunct or aspected by another benefic.
            classification = benefic_malefic_classification(
                sidereal_longitudes, policy,
            )
            associates = []
            for p in _SEVEN_PLANETS:
                if p in ('Jupiter',) or p not in sidereal_longitudes:
                    continue
                if classification[p] != 'benefic':
                    continue
                p_sign = _sign(sidereal_longitudes[p])
                if p_sign == jup_sign or _sign_aspects(p, p_sign, jup_sign):
                    associates.append(p)
            cond_benefic = YogaCondition(
                description=(
                    "Jupiter conjunct or aspected by another benefic "
                    "(BPHS 36.3-4)"
                ),
                satisfied=bool(associates),
                observed=(
                    "benefic association: " + ", ".join(associates)
                    if associates else "no benefic conjunct or aspecting"
                ),
            )
            dig = vedic_dignity('Jupiter', jup_lon)
            elong = abs(
                (jup_lon - sidereal_longitudes.get('Sun', 0.0) + 180.0)
                % 360.0 - 180.0
            )
            combust = elong < _JUPITER_COMBUSTION_ORB_DEG
            quality_ok = (
                not dig.is_debilitated
                and not combust
                and dig.dignity_rank not in ('enemy_sign',)
            )
            cond_quality = YogaCondition(
                description=(
                    "Jupiter avoids debilitation, combustion, and an "
                    "inimical sign (BPHS 36.3-4; combustion orb 11 deg is "
                    "declared policy — the verse names no orb)"
                ),
                satisfied=quality_ok,
                observed=(
                    f"Jupiter in {SIGNS[jup_sign]} ({dig.dignity_rank}); "
                    f"Sun elongation {elong:.1f} deg"
                ),
            )
            conditions = [cond_kendra, cond_benefic, cond_quality]
            formed = cond_kendra.satisfied and bool(associates) and quality_ok
            gaja_notes = (
                "Parashara-strict rule (BPHS 36.3-4). Policy "
                "gajakesari_mode='common' gives the plain PD/Raman rule."
            )

        results.append(YogaResult(
            name='Gajakesari',
            family='chandra',
            formed=formed,
            cancelled=False,
            present=formed,
            conditions=tuple(conditions),
            participants=('Jupiter', 'Moon') if formed else (),
            houses_involved=(h_moon,) if formed else (),
            source=(
                "BPHS Ch. 36 (Santhanam) 3-4; Phaladeepika 6.14, 6.16; "
                "Raman #1"
            ),
            notes=gaja_notes,
        ))

    # --- Sunapha / Anapha / Durudhara / Kemadruma (BPHS 37.7-13) ----------
    second_occupants = [
        p for p in _SUNAPHA_PLANETS
        if p in sidereal_longitudes
        and _house_from(moon_sign, _sign(sidereal_longitudes[p])) == 2
    ]
    twelfth_occupants = [
        p for p in _SUNAPHA_PLANETS
        if p in sidereal_longitudes
        and _house_from(moon_sign, _sign(sidereal_longitudes[p])) == 12
    ]
    conjunct_moon = [
        p for p in _SUNAPHA_PLANETS
        if p in sidereal_longitudes
        and _sign(sidereal_longitudes[p]) == moon_sign
    ]
    flanks_observed = (
        f"2nd from Moon: {', '.join(second_occupants) or 'empty'}; "
        f"12th: {', '.join(twelfth_occupants) or 'empty'}; "
        f"with Moon: {', '.join(conjunct_moon) or 'none'} "
        "(Sun and nodes never count)"
    )

    sunapha_formed = bool(second_occupants)
    anapha_formed = bool(twelfth_occupants)
    for name, formed_flag, house, occupants in (
        ('Sunapha', sunapha_formed and not anapha_formed, 2, second_occupants),
        ('Anapha', anapha_formed and not sunapha_formed, 12, twelfth_occupants),
        ('Durudhara', sunapha_formed and anapha_formed, 0,
         second_occupants + twelfth_occupants),
    ):
        if name == 'Durudhara':
            description = (
                "Planets other than the Sun in both the 2nd and 12th from "
                "the Moon (BPHS 37.7-10; Saravali 13.1; BJ 13.3; PD 6.5)"
            )
            houses_involved = (2, 12)
        else:
            description = (
                f"A planet other than the Sun in the {house}th from the "
                "Moon, the opposite flank empty (BPHS 37.7-10; Saravali "
                "13.1; BJ 13.3; PD 6.5)"
            )
            houses_involved = (house,)
        results.append(YogaResult(
            name=name,
            family='chandra',
            formed=formed_flag,
            cancelled=False,
            present=formed_flag,
            conditions=(YogaCondition(
                description=description,
                satisfied=formed_flag,
                observed=flanks_observed,
            ),),
            participants=tuple(occupants) if formed_flag else (),
            houses_involved=houses_involved if formed_flag else (),
            source="BPHS 37.7-10; Saravali 13.1; BJ 13.3; PD 6.5; Raman #2-4",
            notes=(
                "Only Mars/Mercury/Jupiter/Venus/Saturn participate; the "
                "Sun and the nodes never count."
            ),
        ))

    # Kemadruma: BPHS 37.11-13 folds three clauses into the formation —
    # no planet with the Moon, none in the 2nd/12th from the Moon, and
    # none in a kendra from the lagna.  The non-BPHS bhangas (kendra from
    # the Moon [Saravali 13.2 / PD 6.5], Moon itself in a kendra [BJ 13.3
    # variant], Moon aspected [Saravali]) are evaluated as first-class
    # cancellation clauses.
    kendra_from_lagna_occupants = [
        p for p in _SUNAPHA_PLANETS
        if p in sidereal_longitudes
        and _house_from(lagna_sign, _sign(sidereal_longitudes[p]))
        in _KENDRA_HOUSES
    ]
    kem_conditions = (
        YogaCondition(
            description="No planet (bar the Sun) with the Moon (BPHS 37.11-13)",
            satisfied=not conjunct_moon,
            observed=flanks_observed,
        ),
        YogaCondition(
            description=(
                "No planet in the 2nd or 12th from the Moon (BPHS 37.11-13)"
            ),
            satisfied=not second_occupants and not twelfth_occupants,
            observed=flanks_observed,
        ),
        YogaCondition(
            description=(
                "No planet in a kendra from the lagna (BPHS 37.11-13 — "
                "part of the formation rule in Parashara)"
            ),
            satisfied=not kendra_from_lagna_occupants,
            observed=(
                "kendras from lagna hold: "
                + (", ".join(kendra_from_lagna_occupants) or "no planet")
            ),
        ),
    )
    kem_formed = all(c.satisfied for c in kem_conditions)

    kendra_from_moon_occupants = [
        p for p in _SUNAPHA_PLANETS
        if p in sidereal_longitudes
        and _house_from(moon_sign, _sign(sidereal_longitudes[p]))
        in _KENDRA_HOUSES
    ]
    moon_house_from_lagna = _house_from(lagna_sign, moon_sign)
    moon_aspectors = [
        p for p in _SEVEN_PLANETS
        if p not in ('Moon',) and p in sidereal_longitudes
        and _sign_aspects(p, _sign(sidereal_longitudes[p]), moon_sign)
    ]
    kem_cancellations = (
        YogaCondition(
            description=(
                "A planet in a kendra from the Moon negates Kemadruma "
                "(Saravali 13.2; PD 6.5 'some'; Raman #5)"
            ),
            satisfied=bool(kendra_from_moon_occupants),
            observed=(
                "kendras from Moon hold: "
                + (", ".join(kendra_from_moon_occupants) or "no planet")
            ),
        ),
        YogaCondition(
            description=(
                "The Moon itself in a kendra from the lagna negates "
                "Kemadruma (BJ 13.3 variant reading — flagged "
                "non-authoritative in BJ itself)"
            ),
            satisfied=moon_house_from_lagna in _KENDRA_HOUSES,
            observed=f"Moon in H{moon_house_from_lagna} from lagna",
        ),
        YogaCondition(
            description=(
                "The Moon aspected by any planet negates Kemadruma "
                "(Saravali 13.2)"
            ),
            satisfied=bool(moon_aspectors),
            observed=(
                "Moon aspected by: " + (", ".join(moon_aspectors) or "none")
            ),
        ),
    )
    kem_cancelled = kem_formed and any(c.satisfied for c in kem_cancellations)
    results.append(YogaResult(
        name='Kemadruma',
        family='chandra',
        formed=kem_formed,
        cancelled=kem_cancelled,
        present=kem_formed and not kem_cancelled,
        conditions=kem_conditions,
        cancellations=kem_cancellations,
        participants=('Moon',) if kem_formed else (),
        source="BPHS 37.11-13; Saravali 13.2; BJ 13.3; PD 6.5; Raman #5",
        notes=(
            "BPHS folds the kendra-from-lagna clause into the formation; "
            "the evaluated cancellations are the classical non-BPHS "
            "bhangas. The popular 'Jupiter aspects the Moon' bhanga alone "
            "appears in no consulted primary source (Saravali's clause "
            "covers any planet's aspect)."
        ),
    ))

    # --- Adhi yoga (BPHS 37.5; BJ 13.2; PD 6.42; Raman #7) ----------------
    adhi_placements = {
        p: _house_from(moon_sign, _sign(sidereal_longitudes[p]))
        for p in ('Mercury', 'Jupiter', 'Venus')
        if p in sidereal_longitudes
    }
    adhi_in = {p: h for p, h in adhi_placements.items() if h in (6, 7, 8)}
    malefics_in = [
        p for p in ('Sun', 'Mars', 'Saturn')
        if p in sidereal_longitudes
        and _house_from(moon_sign, _sign(sidereal_longitudes[p])) in (6, 7, 8)
    ]
    adhi_observed = (
        "benefics 6/7/8 from Moon: "
        + (", ".join(f"{p}=H{h}" for p, h in adhi_in.items()) or "none")
        + "; malefics there: " + (", ".join(malefics_in) or "none")
    )
    adhi_formed = bool(adhi_in)
    adhi_cancel = YogaCondition(
        description=(
            "A malefic occupying the 6th/7th/8th from the Moon voids the "
            "yoga (Santhanam commentary / PD Subha-prefix logic — "
            "commentarial, not mula)"
        ),
        satisfied=bool(malefics_in),
        observed=adhi_observed,
    )
    results.append(YogaResult(
        name='Adhi',
        family='chandra',
        formed=adhi_formed,
        cancelled=adhi_formed and adhi_cancel.satisfied,
        present=adhi_formed and not adhi_cancel.satisfied,
        conditions=(YogaCondition(
            description=(
                "Benefics (Mercury/Jupiter/Venus) in the 6th, 7th, or 8th "
                "from the Moon, in any distribution (BPHS 37.5; BJ 13.2; "
                "PD 6.42; Raman #7). Grade by count: 1 leader, 2 minister, "
                "3 ruler."
            ),
            satisfied=adhi_formed,
            observed=adhi_observed,
        ),),
        cancellations=(adhi_cancel,),
        participants=tuple(adhi_in) if adhi_formed else (),
        houses_involved=tuple(sorted(set(adhi_in.values())))
        if adhi_formed else (),
        source="BPHS 37.5; Brihat Jataka 13.2; PD 6.42; Raman #7",
        notes=(
            f"Benefic count = {len(adhi_in)} "
            "(1 leader / 2 minister / 3 ruler — grading is commentarial). "
            "No source requires all three houses filled."
        ),
    ))

    # --- Chandra-Mangala (Raman #6; Saravali Ch. 15 effects) --------------
    if 'Mars' in sidereal_longitudes:
        mars_sign = _sign(sidereal_longitudes['Mars'])
        cm_formed = mars_sign == moon_sign
        results.append(YogaResult(
            name='Chandra-Mangala',
            family='chandra',
            formed=cm_formed,
            cancelled=False,
            present=cm_formed,
            conditions=(YogaCondition(
                description=(
                    "The Moon and Mars conjunct in one sign (Raman #6; "
                    "Saravali 15.8 conjunction effects)"
                ),
                satisfied=cm_formed,
                observed=(
                    f"Moon in sign {moon_sign}, Mars in sign {mars_sign}"
                ),
            ),),
            participants=('Moon', 'Mars') if cm_formed else (),
            source="Raman #6; Saravali Ch. 15 (conjunction effects)",
            notes=(
                "Not defined in BPHS/BJ/PD — Raman is the naming "
                "authority. Raman's mutual-aspect extension is his own "
                "opinion and is not implemented."
            ),
        ))

    return tuple(results)


# ---------------------------------------------------------------------------
# Family 4 — Surya (solar) yogas
#
# BPHS Ch. 38 (Santhanam) 1-4; Saravali Ch. 14; PD 6.8-10; Raman #16-18,
# #24.  Participation: "barring the Moon", nodes excluded — the five true
# planets only.  Whole signs from the Sun; conjunction with the Sun does
# not form these.
# ---------------------------------------------------------------------------

def surya_yogas(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: YogaPolicy | None = None,
) -> tuple[YogaResult, ...]:
    """
    Evaluate the solar yoga family: Vesi, Vosi, Ubhayachari, Budhaditya.
    """
    policy = policy or YogaPolicy()
    results: list[YogaResult] = []
    if 'Sun' not in sidereal_longitudes:
        return ()
    sun_sign = _sign(sidereal_longitudes['Sun'])
    classification = benefic_malefic_classification(sidereal_longitudes, policy)

    second = [
        p for p in _SUNAPHA_PLANETS
        if p in sidereal_longitudes
        and _house_from(sun_sign, _sign(sidereal_longitudes[p])) == 2
    ]
    twelfth = [
        p for p in _SUNAPHA_PLANETS
        if p in sidereal_longitudes
        and _house_from(sun_sign, _sign(sidereal_longitudes[p])) == 12
    ]

    def _subha_papa(occupants: list[str]) -> str:
        if not occupants:
            return ""
        kinds = {classification[p] for p in occupants}
        if kinds == {'benefic'}:
            return "subha (all benefic occupants)"
        if kinds == {'malefic'}:
            return "papa (all malefic occupants)"
        return "mixed benefic/malefic occupants"

    flanks_observed = (
        f"2nd from Sun: {', '.join(second) or 'empty'}; "
        f"12th: {', '.join(twelfth) or 'empty'} "
        "(Moon and nodes never count)"
    )
    for name, formed_flag, house, occupants in (
        ('Vesi', bool(second) and not twelfth, 2, second),
        ('Vosi', bool(twelfth) and not second, 12, twelfth),
        ('Ubhayachari', bool(second) and bool(twelfth), 0, second + twelfth),
    ):
        if name == 'Ubhayachari':
            description = (
                "Planets other than the Moon in both the 2nd and 12th "
                "from the Sun (BPHS 38.1; Saravali 14.1; PD 6.8)"
            )
            houses_involved = (2, 12)
        else:
            description = (
                f"A planet other than the Moon in the {house}th from the "
                "Sun, the opposite flank empty (BPHS 38.1; Saravali 14.1; "
                "PD 6.8)"
            )
            houses_involved = (house,)
        quality = _subha_papa(occupants)
        results.append(YogaResult(
            name=name,
            family='surya',
            formed=formed_flag,
            cancelled=False,
            present=formed_flag,
            conditions=(YogaCondition(
                description=description,
                satisfied=formed_flag,
                observed=flanks_observed
                + (f"; {quality}" if formed_flag and quality else ""),
            ),),
            participants=tuple(occupants) if formed_flag else (),
            houses_involved=houses_involved if formed_flag else (),
            source="BPHS 38.1-4; Saravali 14.1; PD 6.8-10; Raman #16-18",
            notes=(
                "BPHS 38.4: benefic occupants give the stated effects, "
                "malefics the contrary (PD names them Subha-/Papa- "
                "variants). BPHS calls the 12th-house yoga 'Vosi'; "
                "Saravali/PD/Raman use 'Vasi'."
            ),
        ))

    # Budhaditya (Raman #24; Saravali 15.4 conjunction effects).
    if 'Mercury' in sidereal_longitudes:
        mercury_lon = sidereal_longitudes['Mercury']
        same_sign = _sign(mercury_lon) == sun_sign
        elong = abs(
            (mercury_lon - sidereal_longitudes['Sun'] + 180.0) % 360.0 - 180.0
        )
        combust_close = elong < 10.0
        cancel = YogaCondition(
            description=(
                "Mercury within 10 deg of the Sun (Raman #24 caveat — "
                "modern, not mula; enabled by policy "
                "budhaditya_combustion_cancel)"
            ),
            satisfied=combust_close if policy.budhaditya_combustion_cancel
            else False,
            observed=f"Sun-Mercury elongation {elong:.2f} deg",
        )
        bud_cancelled = same_sign and cancel.satisfied
        results.append(YogaResult(
            name='Budhaditya',
            family='surya',
            formed=same_sign,
            cancelled=bud_cancelled,
            present=same_sign and not bud_cancelled,
            conditions=(YogaCondition(
                description=(
                    "The Sun and Mercury conjunct in one sign (Raman #24; "
                    "Saravali 15.4 conjunction effects; no house "
                    "restriction in any mula text examined)"
                ),
                satisfied=same_sign,
                observed=(
                    f"Sun sign {sun_sign}, Mercury sign "
                    f"{_sign(mercury_lon)}; elongation {elong:.2f} deg"
                ),
            ),),
            cancellations=(cancel,),
            participants=('Sun', 'Mercury') if same_sign else (),
            source="Raman #24; Saravali Ch. 15 (conjunction effects)",
            notes=(
                "Jataka Martanda restricts efficacy to Aries/Leo/Virgo "
                "lagnas (via Santhanam's Saravali notes) — recorded, not "
                "implemented. Raman's 10-deg elongation caveat is a "
                "policy switch, default off."
            ),
        ))

    return tuple(results)


# ---------------------------------------------------------------------------
# Family 5 — Raja yogas
#
# BPHS Ch. 34 (Santhanam) 11-15 (kendra-trikona foundation + 34.15
# dilution); BPHS Ch. 39 (royal associations); Phaladeepika 6.37
# (Dharma-Karmadhipati named as THE Raja Yoga), 6.57 (Harsha/Sarala/Vimala
# naming), 7.26-30 (Neecha Bhanga Raja); Uttara Kalamrita IV.3, IV.22;
# Raman #109-111.
#
# Viparita formulations conflict across the primaries and are exposed as
# policy: Phaladeepika (each dusthana lord in ANY of 6/8/12 — naming
# source, default), Uttara Kalamrita (each lord in the OTHER two
# dusthanas, with the unassociation clause), Raman (each lord in its OWN
# dusthana).  UK's clash with PD's Dainya classification is recorded on
# the result, never silently resolved.
# ---------------------------------------------------------------------------

def _lords_of_houses(lagna_sign: int) -> dict[int, str]:
    """House number (1-12) -> classical lord, whole signs from the lagna."""
    return {
        house: _RASI_LORDS[(lagna_sign + house - 1) % 12]
        for house in range(1, 13)
    }


def _houses_owned(lagna_sign: int, planet: str) -> frozenset[int]:
    return frozenset(
        h for h, lord in _lords_of_houses(lagna_sign).items() if lord == planet
    )


def _sambandha(
    a: str,
    b: str,
    sidereal_longitudes: dict[str, float],
    lagna_sign: int,
) -> str | None:
    """
    Classical relation between two planets: 'conjunction', 'exchange', or
    'mutual_aspect' (the three sambandhas of UK IV.4), else None.
    """
    if a not in sidereal_longitudes or b not in sidereal_longitudes:
        return None
    sa, sb = _sign(sidereal_longitudes[a]), _sign(sidereal_longitudes[b])
    if sa == sb:
        return 'conjunction'
    if _RASI_LORDS[sa] == b and _RASI_LORDS[sb] == a:
        return 'exchange'
    if _sign_aspects(a, sa, sb) and _sign_aspects(b, sb, sa):
        return 'mutual_aspect'
    return None


def raja_yogas(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: YogaPolicy | None = None,
    planet_speeds: dict[str, float] | None = None,
) -> tuple[YogaResult, ...]:
    """
    Evaluate the Raja family: Kendra-Trikona Raja (BPHS 34.11-12 with the
    34.15 dilution), Yogakaraka (BPHS 34.13), Dharma-Karmadhipati
    (PD 6.37; UK IV.3), Viparita Harsha/Sarala/Vimala (policy-selected
    formulation), and Neecha Bhanga Raja (PD 7.26-30) per debilitated
    planet.  ``planet_speeds`` (deg/day, signed) enables the PD 7.3 / UK
    II.6 retrograde clause; omitted, that clause reads unevaluated-false.
    """
    from .vedic_dignities import vedic_dignity
    from .constants import SIGNS

    policy = policy or YogaPolicy()
    lagna_sign = _sign(lagna_sidereal_lon)
    lords = _lords_of_houses(lagna_sign)
    results: list[YogaResult] = []

    kendra_lords = {lords[h] for h in (1, 4, 7, 10)}
    trikona_lords = {lords[h] for h in (1, 5, 9)}
    evil_lords = {lords[h] for h in (3, 6, 11)}   # BPHS 34.15

    # --- Yogakaraka (BPHS 34.13) ------------------------------------------
    yogakarakas = sorted(
        p for p in kendra_lords & trikona_lords
        if _houses_owned(lagna_sign, p) & {4, 7, 10}
        and _houses_owned(lagna_sign, p) & {5, 9}
    )
    results.append(YogaResult(
        name='Yogakaraka',
        family='raja',
        formed=bool(yogakarakas),
        cancelled=False,
        present=bool(yogakarakas),
        conditions=(YogaCondition(
            description=(
                "One planet simultaneously lords a kendra (4/7/10) and a "
                "trikona (5/9) (BPHS 34.13)"
            ),
            satisfied=bool(yogakarakas),
            observed=(
                "yogakaraka(s): " + (", ".join(yogakarakas) or "none")
            ),
        ),),
        participants=tuple(yogakarakas),
        source="BPHS Ch. 34 (Santhanam) 13",
        notes=(
            "The lagna lord's dual kendra+trikona status (BPHS 34.2-7) is "
            "not counted here — 34.13 concerns the 4/7/10 + 5/9 dual lord."
        ),
    ))

    # --- Kendra-Trikona Raja (BPHS 34.11-12, diluted per 34.15) -----------
    pair_evidence: list[str] = []
    qualifying: list[tuple[str, str, str]] = []
    diluted: list[str] = []
    seen_pairs: set[frozenset[str]] = set()
    for kl in sorted(kendra_lords):
        for tl in sorted(trikona_lords):
            if kl == tl:
                continue
            key = frozenset({kl, tl})
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            relation = _sambandha(kl, tl, sidereal_longitudes, lagna_sign)
            placement = None
            if relation is None:
                # BPHS 34.11-12 also admits placements: trikona lord in a
                # kendra house or kendra lord in a trikona house.
                if kl in sidereal_longitudes and tl in sidereal_longitudes:
                    tl_house = _house_from(
                        lagna_sign, _sign(sidereal_longitudes[tl]))
                    kl_house = _house_from(
                        lagna_sign, _sign(sidereal_longitudes[kl]))
                    if tl_house in _KENDRA_HOUSES or kl_house in _TRIKONA_HOUSES:
                        placement = (
                            f"{tl} in H{tl_house} / {kl} in H{kl_house}"
                        )
            if relation is None and placement is None:
                continue
            how = relation or f"placement ({placement})"
            if kl in evil_lords or tl in evil_lords:
                diluted.append(
                    f"{kl}-{tl} ({how}) — diluted: "
                    f"{'/'.join(p for p in (kl, tl) if p in evil_lords)} "
                    "also lords 3/6/11 (BPHS 34.15)"
                )
                continue
            qualifying.append((kl, tl, how))
            pair_evidence.append(f"{kl}-{tl} via {how}")

    kt_formed = bool(qualifying)
    results.append(YogaResult(
        name='Kendra-Trikona Raja',
        family='raja',
        formed=kt_formed,
        cancelled=False,
        present=kt_formed,
        conditions=(
            YogaCondition(
                description=(
                    "A kendra lord and a trikona lord related by exchange, "
                    "conjunction, mutual full aspect, or kendra/trikona "
                    "placement (BPHS 34.11-12)"
                ),
                satisfied=kt_formed,
                observed=(
                    "qualifying pairs: " + ("; ".join(pair_evidence) or "none")
                ),
            ),
            YogaCondition(
                description=(
                    "Neither lord simultaneously owns an evil house 3/6/11 "
                    "(BPHS 34.15 — such relations do not cause Raja yoga)"
                ),
                satisfied=kt_formed,
                observed=(
                    "diluted pairs: " + ("; ".join(diluted) or "none")
                ),
            ),
        ),
        participants=tuple(sorted({p for kl, tl, _ in qualifying
                                   for p in (kl, tl)})),
        source="BPHS Ch. 34 (Santhanam) 11-12, 15; Ch. 41.28",
        notes=(
            "Santhanam's commentary ranks exchange, mutual aspect, and "
            "conjunction above pure placements. Nodes (BPHS 34.16-17) are "
            "outside this engine's participant set."
        ),
    ))

    # --- Dharma-Karmadhipati (PD 6.37; UK IV.3) ----------------------------
    lord9, lord10 = lords[9], lords[10]
    if lord9 == lord10:
        dk_relation = 'single lord of both (yogakaraka, BPHS 34.13)'
    else:
        dk_relation = _sambandha(lord9, lord10, sidereal_longitudes, lagna_sign)
    dk_formed = dk_relation is not None
    uk_caveat_holds = bool(
        (_houses_owned(lagna_sign, lord9) | _houses_owned(lagna_sign, lord10))
        & {8, 11}
    )
    dk_cancel = YogaCondition(
        description=(
            "Either lord also owns the 8th or 11th (UK IV.3 proviso: the "
            "yoga holds 'provided the said two lords do not own the 8th "
            "or the 11th house as well')"
        ),
        satisfied=uk_caveat_holds,
        observed=(
            f"{lord9} owns {sorted(_houses_owned(lagna_sign, lord9))}; "
            f"{lord10} owns {sorted(_houses_owned(lagna_sign, lord10))}"
        ),
    )
    results.append(YogaResult(
        name='Dharma-Karmadhipati',
        family='raja',
        formed=dk_formed,
        cancelled=dk_formed and uk_caveat_holds,
        present=dk_formed and not uk_caveat_holds,
        conditions=(YogaCondition(
            description=(
                "The 9th and 10th lords in sambandha — conjunction, "
                "exchange, or mutual aspect (PD 6.37 names this THE Raja "
                "Yoga; UK IV.3 admits the same three relations)"
            ),
            satisfied=dk_formed,
            observed=(
                f"9L={lord9}, 10L={lord10}; relation: "
                + (dk_relation or "none")
            ),
        ),),
        cancellations=(dk_cancel,),
        participants=(lord9, lord10) if dk_formed else (),
        source="Phaladeepika 6.37; Uttara Kalamrita IV.3-4; BPHS 39.37",
        notes=(
            "'Supreme raja yoga' status is commentarial (PD names it, UK "
            "elaborates it; no captured mula verse says 'supreme')."
        ),
    ))

    # --- Viparita: Harsha / Sarala / Vimala (policy formulation) -----------
    for name, dusthana in (('Harsha', 6), ('Sarala', 8), ('Vimala', 12)):
        lord = lords[dusthana]
        if lord not in sidereal_longitudes:
            continue
        lord_house = _house_from(lagna_sign, _sign(sidereal_longitudes[lord]))
        if policy.viparita_mode == 'uttara_kalamrita':
            allowed = _DUSTHANA_HOUSES - {dusthana}
            rule_text = (
                f"The {dusthana}th lord in one of the OTHER two dusthanas "
                f"{sorted(allowed)} (UK IV.22)"
            )
        elif policy.viparita_mode == 'raman':
            allowed = frozenset({dusthana})
            rule_text = (
                f"The {dusthana}th lord in its OWN house H{dusthana} "
                "(Raman #109-111, read distributively)"
            )
        else:
            allowed = _DUSTHANA_HOUSES
            rule_text = (
                f"The {dusthana}th lord in any of 6/8/12 "
                "(Phaladeepika 6.57 — the naming source)"
            )
        formed = lord_house in allowed

        # UK's unassociation clause, evaluated always, cancelling only in
        # UK mode (PD states no guard; BPHS guards differently).
        other_assoc = sorted(
            p for p in _SEVEN_PLANETS
            if p != lord and p in sidereal_longitudes
            and p not in (lords[6], lords[8], lords[12])
            and _sambandha(lord, p, sidereal_longitudes, lagna_sign)
            is not None
        )
        uk_cancel = YogaCondition(
            description=(
                "The dusthana lord in sambandha with a planet outside the "
                "6/8/12 lords voids the Viparita effect (UK IV.22 "
                "unassociation clause — UK-only; PD states no guard)"
            ),
            satisfied=bool(other_assoc)
            if policy.viparita_mode == 'uttara_kalamrita' else False,
            observed=(
                "outside associations: " + (", ".join(other_assoc) or "none")
            ),
        )
        cancelled = formed and uk_cancel.satisfied
        results.append(YogaResult(
            name=name,
            family='raja',
            formed=formed,
            cancelled=cancelled,
            present=formed and not cancelled,
            conditions=(YogaCondition(
                description=rule_text,
                satisfied=formed,
                observed=f"{dusthana}L={lord} in H{lord_house}",
            ),),
            cancellations=(uk_cancel,),
            participants=(lord,) if formed else (),
            houses_involved=(lord_house,) if formed else (),
            source=(
                "Phaladeepika 6.57 (naming); Uttara Kalamrita IV.22; "
                "Raman #109-111; BPHS Ch. 39.19-31 (different guard)"
            ),
            notes=(
                f"viparita_mode='{policy.viparita_mode}'. The three "
                "primaries define incompatible house-sets (PD any-of-6/8/12; "
                "UK other-two; Raman own-house). UK IV.22(d) treats mutual "
                "dusthana-lord exchange as Viparita Raja while PD 6.32 "
                "classes the same exchange as Dainya — an unresolved "
                "source conflict, reported, not hidden."
            ),
        ))

    # --- Neecha Bhanga Raja (PD 7.26-30) ------------------------------------
    from .vedic_dignities import EXALTATION_SIGN, DEBILITATION_SIGN

    moon_sign = (
        _sign(sidereal_longitudes['Moon'])
        if 'Moon' in sidereal_longitudes else None
    )
    for planet in _SEVEN_PLANETS:
        if planet not in sidereal_longitudes:
            continue
        lon = sidereal_longitudes[planet]
        dig = vedic_dignity(planet, lon)
        if not dig.is_debilitated:
            continue
        deb_sign = _sign(lon)
        deb_lord = _RASI_LORDS[deb_sign]
        exalt_lord = _RASI_LORDS[EXALTATION_SIGN[planet]]

        def _in_kendra_from_lagna_or_moon(p: str) -> tuple[bool, str]:
            if p not in sidereal_longitudes:
                return False, f"{p} absent"
            ps = _sign(sidereal_longitudes[p])
            hl = _house_from(lagna_sign, ps)
            hm = _house_from(moon_sign, ps) if moon_sign is not None else None
            ok = hl in _KENDRA_HOUSES or (
                hm is not None and hm in _KENDRA_HOUSES
            )
            return ok, f"{p}: H{hl} from lagna" + (
                f", H{hm} from Moon" if hm is not None else ""
            )

        ok_a, obs_a = _in_kendra_from_lagna_or_moon(deb_lord)
        ok_b, obs_b = _in_kendra_from_lagna_or_moon(exalt_lord)
        dispositor_aspects = (
            deb_lord in sidereal_longitudes
            and _sign_aspects(
                deb_lord, _sign(sidereal_longitudes[deb_lord]), deb_sign,
            )
        )
        mutual_kendra = (
            deb_lord in sidereal_longitudes
            and exalt_lord in sidereal_longitudes
            and _house_from(
                _sign(sidereal_longitudes[deb_lord]),
                _sign(sidereal_longitudes[exalt_lord]),
            ) in _KENDRA_HOUSES
        )
        retrograde = (
            planet_speeds is not None
            and planet_speeds.get(planet, 0.0) < 0.0
        )

        rules = (
            YogaCondition(
                description=(
                    f"The lord of the debilitation sign ({deb_lord}) in a "
                    "kendra from the lagna or the Moon (PD 7.26, 7.29)"
                ),
                satisfied=ok_a,
                observed=obs_a,
            ),
            YogaCondition(
                description=(
                    f"The lord of {planet}'s exaltation sign ({exalt_lord}) "
                    "in a kendra from the lagna or the Moon (PD 7.26; the "
                    "'planet exalted in the debilitation sign' alternative "
                    "reading is noted by the translator, not implemented)"
                ),
                satisfied=ok_b,
                observed=obs_b,
            ),
            YogaCondition(
                description=(
                    f"{planet} aspected by its dispositor {deb_lord} "
                    "(PD 7.28)"
                ),
                satisfied=bool(dispositor_aspects),
                observed=(
                    f"{deb_lord} aspects {planet}: {bool(dispositor_aspects)}"
                ),
            ),
            YogaCondition(
                description=(
                    "The debilitation lord and the exaltation lord in "
                    "mutual kendras (PD 7.27)"
                ),
                satisfied=bool(mutual_kendra),
                observed=f"{deb_lord} and {exalt_lord} mutual kendra: "
                f"{bool(mutual_kendra)}",
            ),
            YogaCondition(
                description=(
                    f"{planet} retrograde while debilitated (PD 7.3; UK "
                    "II.6: strength as if exalted). Requires speeds; "
                    "unevaluated without them."
                ),
                satisfied=bool(retrograde),
                observed=(
                    f"speed: {planet_speeds.get(planet):+.4f} deg/day"
                    if planet_speeds is not None
                    and planet in planet_speeds
                    else "speeds not supplied"
                ),
            ),
        )
        formed = any(r.satisfied for r in rules)
        results.append(YogaResult(
            name=f'Neecha Bhanga ({planet})',
            family='raja',
            formed=formed,
            cancelled=False,
            present=formed,
            conditions=rules,
            participants=(planet,) if formed else (),
            source="Phaladeepika 7.26-30, 7.3; Uttara Kalamrita II.6; "
                   "Jataka Parijata 7.14 (navamsa rule, not implemented)",
            notes=(
                "Any single satisfied rule grants the yoga (PD treats "
                "7.26-30 directly as raja yogas). PD names kendra only — "
                "the popular trikona widening and the exchange/"
                "aspected-by-another-debilitated rules are compilation-"
                "tier, unverified in the captured primaries, and are not "
                "implemented."
            ),
        ))

    return tuple(results)


# ---------------------------------------------------------------------------
# Family 6 — Dhana (wealth) core
#
# BPHS Ch. 13 (2nd-house doctrine); Uttara Kalamrita IV.5, IV.28 (the
# 2/5/9/11 network with its dusthana-contamination dilution);
# Phaladeepika 6.21 (Lakshmi), 6.32-34 (Parivartana classification).
# ---------------------------------------------------------------------------

def dhana_yogas(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: YogaPolicy | None = None,
) -> tuple[YogaResult, ...]:
    """
    Evaluate the Dhana core: the 2L-11L association (BPHS 13.4-5), the
    2/5/9/11 sambandha network with UK IV.28's dusthana dilution, Lakshmi
    (PD 6.21 primary form), and the Parivartana exchange classification
    (Maha/Khala/Dainya per PD 6.32).
    """
    from .vedic_dignities import vedic_dignity
    from .constants import SIGNS

    policy = policy or YogaPolicy()
    lagna_sign = _sign(lagna_sidereal_lon)
    lords = _lords_of_houses(lagna_sign)
    results: list[YogaResult] = []

    # --- 2L-11L association (BPHS 13.4) ------------------------------------
    lord2, lord11 = lords[2], lords[11]
    if lord2 == lord11:
        rel_2_11 = 'single lord of both'
    else:
        rel_2_11 = _sambandha(lord2, lord11, sidereal_longitudes, lagna_sign)
        if rel_2_11 == 'mutual_aspect':
            # BPHS 13.4 admits exchange or conjunction in kendra/trikona;
            # mutual aspect is not named there.
            rel_2_11 = None
        if rel_2_11 == 'conjunction':
            joint_house = _house_from(
                lagna_sign, _sign(sidereal_longitudes[lord2]))
            if joint_house not in (_KENDRA_HOUSES | _TRIKONA_HOUSES):
                rel_2_11 = None
    dhana_2_11_formed = rel_2_11 is not None
    results.append(YogaResult(
        name='Dhana (2-11)',
        family='dhana',
        formed=dhana_2_11_formed,
        cancelled=False,
        present=dhana_2_11_formed,
        conditions=(YogaCondition(
            description=(
                "The 2nd and 11th lords exchange houses, or join in a "
                "kendra or trikona (BPHS 13.4)"
            ),
            satisfied=dhana_2_11_formed,
            observed=f"2L={lord2}, 11L={lord11}; relation: "
            + (rel_2_11 or "none admitted by 13.4"),
        ),),
        participants=(lord2, lord11) if dhana_2_11_formed else (),
        source="BPHS Ch. 13 (Santhanam) 4-5",
        notes="BPHS 13.6-8 poverty caveats concern dusthana placement "
              "and combustion — carried by the network dilution below.",
    ))

    # --- 2/5/9/11 network (UK IV.28) ----------------------------------------
    network_lords = {h: lords[h] for h in (2, 5, 9, 11)}
    related_pairs: list[str] = []
    participants: set[str] = set()
    houses_involved: set[int] = set()
    items = sorted(set(network_lords.values()))
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            rel = _sambandha(a, b, sidereal_longitudes, lagna_sign)
            if rel is not None:
                related_pairs.append(f"{a}-{b} ({rel})")
                participants.update((a, b))
    for h, lord in network_lords.items():
        if lord in participants:
            houses_involved.add(h)
    dusthana_lords = {lords[6], lords[8], lords[12]}
    contaminators = sorted(
        d for d in dusthana_lords
        for p in participants
        if d != p and _sambandha(d, p, sidereal_longitudes, lagna_sign)
        is not None
    )
    contamination = YogaCondition(
        description=(
            "A dusthana (6/8/12) lord partnering the sambandha destroys "
            "the wealth (UK IV.28: 'destruction of the whole wealth')"
        ),
        satisfied=bool(contaminators),
        observed="dusthana partners: " + (", ".join(contaminators) or "none"),
    )
    net_formed = bool(related_pairs)
    results.append(YogaResult(
        name='Dhana Network (2-5-9-11)',
        family='dhana',
        formed=net_formed,
        cancelled=net_formed and contamination.satisfied,
        present=net_formed and not contamination.satisfied,
        conditions=(YogaCondition(
            description=(
                "Two or more of the 2nd/5th/9th/11th lords mutually "
                "related by conjunction, exchange, or mutual aspect "
                "(UK IV.28)"
            ),
            satisfied=net_formed,
            observed="related: " + ("; ".join(related_pairs) or "none"),
        ),),
        cancellations=(contamination,),
        participants=tuple(sorted(participants)),
        houses_involved=tuple(sorted(houses_involved)),
        source="Uttara Kalamrita IV.5, IV.28; BPHS 41.16",
        notes="UK grades by strength; strength grading is Shadbala's "
              "domain, joined at the API layer.",
    ))

    # --- Lakshmi (PD 6.21 primary) ------------------------------------------
    lord9 = lords[9]
    def _own_or_exalt_in_kendra_trikona(p: str) -> tuple[bool, str]:
        if p not in sidereal_longitudes:
            return False, f"{p} absent"
        lon = sidereal_longitudes[p]
        d = vedic_dignity(p, lon)
        house = _house_from(lagna_sign, _sign(lon))
        ok = (d.is_own_sign or d.is_exalted) and (
            house in (_KENDRA_HOUSES | _TRIKONA_HOUSES)
        )
        return ok, (
            f"{p} in {SIGNS[_sign(lon)]} ({d.dignity_rank}) H{house}"
        )

    ok9, obs9 = _own_or_exalt_in_kendra_trikona(lord9)
    okv, obsv = _own_or_exalt_in_kendra_trikona('Venus')
    lakshmi_formed = ok9 and okv
    results.append(YogaResult(
        name='Lakshmi',
        family='dhana',
        formed=lakshmi_formed,
        cancelled=False,
        present=lakshmi_formed,
        conditions=(
            YogaCondition(
                description=(
                    f"The 9th lord ({lord9}) in own or exaltation sign "
                    "identical with a kendra or trikona (PD 6.21)"
                ),
                satisfied=ok9,
                observed=obs9,
            ),
            YogaCondition(
                description=(
                    "Venus likewise in own or exaltation sign in a kendra "
                    "or trikona (PD 6.21 — the primary form requires BOTH)"
                ),
                satisfied=okv,
                observed=obsv,
            ),
        ),
        participants=(lord9, 'Venus') if lakshmi_formed else (),
        source="Phaladeepika 6.21, 6.24; Raman #72 (variant definitions)",
        notes=(
            "PD's primary form requires the 9th lord AND Venus. Raman's "
            "headline form (strong lagna lord + 9L only) is a recorded "
            "variant, not implemented; Raman himself calls the PD form "
            "'the most powerful type'."
        ),
    ))

    # --- Parivartana classification (PD 6.32) -------------------------------
    exchanges: list[tuple[str, str, str]] = []
    seen: set[frozenset[str]] = set()
    for a in sorted(set(lords.values())):
        for b in sorted(set(lords.values())):
            if a >= b:
                continue
            key = frozenset({a, b})
            if key in seen:
                continue
            seen.add(key)
            if a not in sidereal_longitudes or b not in sidereal_longitudes:
                continue
            sa, sb = (_sign(sidereal_longitudes[a]),
                      _sign(sidereal_longitudes[b]))
            if _RASI_LORDS[sa] == b and _RASI_LORDS[sb] == a and sa != sb:
                houses_a = _houses_owned(lagna_sign, a)
                houses_b = _houses_owned(lagna_sign, b)
                combined = houses_a | houses_b
                if combined & {6, 8, 12}:
                    kind = 'Dainya'
                elif 3 in combined:
                    kind = 'Khala'
                else:
                    kind = 'Maha'
                exchanges.append((a, b, kind))

    for kind in ('Maha', 'Khala', 'Dainya'):
        matching = [(a, b) for a, b, k in exchanges if k == kind]
        formed = bool(matching)
        results.append(YogaResult(
            name=f'{kind} Parivartana',
            family='dhana',
            formed=formed,
            cancelled=False,
            present=formed,
            conditions=(YogaCondition(
                description=(
                    "Two house lords in mutual exchange; classified "
                    "Dainya when a 6/8/12 lord participates, Khala when "
                    "the 3rd lord participates (and no dusthana), Maha "
                    "otherwise (PD 6.32: 30 Dainya, 8 Khala, 28 Maha)"
                ),
                satisfied=formed,
                observed=(
                    "exchanges: "
                    + ("; ".join(f"{a}<->{b}" for a, b in matching) or "none")
                ),
            ),),
            participants=tuple(sorted({p for pair in matching for p in pair})),
            source="Phaladeepika 6.32-34",
            notes=(
                "UK IV.22(d) treats mutual dusthana-lord exchange as "
                "Viparita Raja while PD 6.32 classes it Dainya — both "
                "evaluations are reported (see the Viparita results)."
            ) if kind == 'Dainya' else "",
        ))

    return tuple(results)


# ---------------------------------------------------------------------------
# Top-level evaluator
# ---------------------------------------------------------------------------

def evaluate_yogas(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: YogaPolicy | None = None,
    planet_speeds: dict[str, float] | None = None,
) -> YogaChartResult:
    """
    Evaluate every yoga family for one chart.

    Parameters
    ----------
    sidereal_longitudes : dict[str, float]
        Sidereal longitudes of the seven classical planets.
    lagna_sidereal_lon : float
        Sidereal lagna longitude (whole-sign house frame).
    policy : YogaPolicy, optional
        Doctrine switches; defaults are BPHS-primary.
    planet_speeds : dict[str, float], optional
        Signed daily motions; enables the retrograde Neecha Bhanga clause.

    Returns
    -------
    YogaChartResult
        Every evaluated yoga — present, formed-but-cancelled,
        formed-but-suppressed, and unformed alike — the full proof set.
    """
    policy = policy or YogaPolicy()
    yogas = (
        pancha_mahapurusha_yogas(sidereal_longitudes, lagna_sidereal_lon, policy)
        + chandra_yogas(sidereal_longitudes, lagna_sidereal_lon, policy)
        + surya_yogas(sidereal_longitudes, lagna_sidereal_lon, policy)
        + nabhasa_yogas(sidereal_longitudes, lagna_sidereal_lon, policy)
        + raja_yogas(sidereal_longitudes, lagna_sidereal_lon, policy,
                     planet_speeds)
        + dhana_yogas(sidereal_longitudes, lagna_sidereal_lon, policy)
    )
    return YogaChartResult(
        lagna_sign_index=_sign(lagna_sidereal_lon),
        policy=policy,
        yogas=yogas,
        present_names=tuple(y.name for y in yogas if y.present),
    )
