"""
Moira — Avastha Engine (planetary states)
==========================================

Archetype: Engine

Purpose
-------
Computes the classical planetary-state (avastha) systems of BPHS Ch. 45
(Santhanam), with the Deeptadi system source-parameterized because the four
primary texts genuinely disagree (differing counts, and name collisions
such as Deena = neutral in BPHS but Dina = enemy in Jataka Parijata).
States are reported with the evidence that produced them.

Systems
-------
1. **Baladi** (5 age states, BPHS 45.3-4): 6-degree bands, ascending in odd
   signs, reversed in even signs.  Effect grades per 45.4: Bala 1/4,
   Kumara 1/2, Yuva full, Vriddha "negligible" (no classical number —
   any numeric value is declared policy), Mrita nil.
2. **Jagradadi** (3 awareness states, BPHS 45.5-6): Jagrat (own/exaltation),
   Swapna (friend's or neutral's sign), Sushupti (enemy's sign or
   debilitation).  Exaltation/debilitation clauses override the lordship
   clauses (declared interpretive doctrine — the verse does not resolve
   the overlap).
3. **Deeptadi** (source-parameterized): BPHS 45.7-10 nine states (default);
   Saravali 5.2-4 nine (different set); Jataka Parijata 2.16-18 ten;
   Phaladeepika 3.18-19 eleven named conditions.  Never merged.
4. **Lajjitadi** (6 conditional states, BPHS 45.11-18): independent,
   non-exclusive booleans — BPHS gives no dominance ordering; the
   45.18-23 modulation rules are carried as notes.

**Sayanadi** (BPHS 45.30-155) is intentionally deferred: it requires birth
ghatis and the first syllable of the native's name (inputs beyond the
chart), and Santhanam's printed sub-state example carries an arithmetic
inconsistency needing a second-edition recheck.

Ambiguity policy (declared)
---------------------------
* Relationship scheme: compound (Panchadha Maitri) by default — BPHS
  45.8-10 uses adhimitra/adhishatru, categories that exist only in the
  compound scheme; switchable to natural.
* Benefic/malefic classification: the engine-wide conditional doctrine
  (paksha Moon, conditional Mercury) from ``moira.yogas``.
* Combustion: longitude proximity to the Sun within classical per-planet
  orbs (declared table below; BPHS says only "eclipsed by the Sun").
* "Benefic/malefic varga" (Saravali/JP/PD): the planet's NAVAMSA sign
  lord's nature — declared policy, the texts do not name the varga.
* Watery signs (Trushita): Cancer, Scorpio, Pisces.
* Nodes: not avastha subjects by default; Rahu/Ketu participate only as
  Lajjita afflictors when their longitudes are supplied.

Sources
-------
BPHS Ch. 45 (Santhanam, verified against the archive.org scan with the
sanskritdocuments e-text resolving one printed lacuna in 45.7-10);
Saravali Ch. 5 (Santhanam); Jataka Parijata Adhyaya 2 (Sastri lineage,
secondary-verified); Phaladeepika Ch. 3 (Sastri/wisdomlib).
"""

from dataclasses import dataclass

__all__ = [
    "AvasthaPolicy",
    "BaladiAvastha",
    "JagradadiAvastha",
    "DeeptadiAvastha",
    "LajjitadiState",
    "LajjitadiAvasthas",
    "PlanetAvasthas",
    "AvasthaChartResult",
    "baladi_avastha",
    "jagradadi_avastha",
    "deeptadi_avastha",
    "lajjitadi_avasthas",
    "evaluate_avasthas",
]

_SEVEN_PLANETS: tuple[str, ...] = (
    'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
)

_RASI_LORDS: tuple[str, ...] = (
    'Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury',
    'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter',
)

# Classical combustion orbs (degrees of Sun elongation), direct motion.
# BPHS Ch. 45 says only "eclipsed by the Sun"; the orb table is the
# standard classical set and is declared policy, not verse text.
_COMBUSTION_ORB_DEG: dict[str, float] = {
    'Moon': 12.0, 'Mars': 17.0, 'Mercury': 14.0,
    'Jupiter': 11.0, 'Venus': 10.0, 'Saturn': 15.0,
}

# Graha drishti (full sign aspects) — same doctrine as moira.yogas.
_FULL_ASPECT_DISTANCES: dict[str, frozenset[int]] = {
    'Sun':     frozenset({7}),
    'Moon':    frozenset({7}),
    'Mars':    frozenset({4, 7, 8}),
    'Mercury': frozenset({7}),
    'Jupiter': frozenset({5, 7, 9}),
    'Venus':   frozenset({7}),
    'Saturn':  frozenset({3, 7, 10}),
}

_WATERY_SIGNS: frozenset[int] = frozenset({3, 7, 11})   # Cancer, Scorpio, Pisces

_BALADI_STATES: tuple[str, ...] = ('Bala', 'Kumara', 'Yuva', 'Vriddha', 'Mrita')
_BALADI_FRACTIONS: dict[str, float | None] = {
    'Bala': 0.25, 'Kumara': 0.5, 'Yuva': 1.0,
    'Vriddha': None,   # "negligible" — no classical number (BPHS 45.4)
    'Mrita': 0.0,
}


@dataclass(frozen=True, slots=True)
class AvasthaPolicy:
    """
    Explicit doctrine switches for avastha evaluation.

    relationship_scheme : str
        ``'compound'`` (Panchadha Maitri — default; BPHS 45.8-10 requires
        it) or ``'natural'``.
    deeptadi_source : str
        ``'bphs_9'`` (default) | ``'saravali_9'`` | ``'jataka_parijata_10'``
        | ``'phaladeepika_11'`` — the four texts genuinely disagree and are
        never merged.
    vriddha_fraction : float or None
        Numeric stand-in for BPHS 45.4's "negligible"; None (default)
        reports the classical wording without inventing a number.
    """

    relationship_scheme: str = 'compound'
    deeptadi_source: str = 'bphs_9'
    vriddha_fraction: float | None = None

    def __post_init__(self) -> None:
        if self.relationship_scheme not in ('compound', 'natural'):
            raise ValueError(
                f"relationship_scheme must be 'compound' or 'natural', "
                f"got {self.relationship_scheme!r}"
            )
        if self.deeptadi_source not in (
            'bphs_9', 'saravali_9', 'jataka_parijata_10', 'phaladeepika_11',
        ):
            raise ValueError(
                f"deeptadi_source must be one of 'bphs_9', 'saravali_9', "
                f"'jataka_parijata_10', 'phaladeepika_11', "
                f"got {self.deeptadi_source!r}"
            )


# ---------------------------------------------------------------------------
# Vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BaladiAvastha:
    """Baladi (age) state per BPHS 45.3-4."""

    planet: str
    state: str
    segment_index: int          # 0-4 band within the sign
    degree_in_sign: float
    sign_is_odd: bool
    effect_fraction: float | None
    effect_label: str           # 'quarter' | 'half' | 'full' | 'negligible' | 'nil'

    def __post_init__(self) -> None:
        if self.state not in _BALADI_STATES:
            raise ValueError(f"unknown Baladi state {self.state!r}")
        if not (0 <= self.segment_index <= 4):
            raise ValueError(
                f"segment_index must be 0-4, got {self.segment_index}"
            )


@dataclass(frozen=True, slots=True)
class JagradadiAvastha:
    """Jagradadi (awareness) state per BPHS 45.5-6."""

    planet: str
    state: str                  # 'Jagrat' | 'Swapna' | 'Sushupti'
    reason: str
    effect_fraction: float      # 1.0 | 0.5 | 0.0 (BPHS 45.6 full/medium/nil)

    def __post_init__(self) -> None:
        if self.state not in ('Jagrat', 'Swapna', 'Sushupti'):
            raise ValueError(f"unknown Jagradadi state {self.state!r}")


@dataclass(frozen=True, slots=True)
class DeeptadiAvastha:
    """Deeptadi state under one named source's rule table (never merged)."""

    planet: str
    state: str
    source: str                 # 'bphs_9' | 'saravali_9' | ...
    reason: str
    citation: str


@dataclass(frozen=True, slots=True)
class LajjitadiState:
    """One evaluated Lajjitadi condition (BPHS 45.11-18)."""

    state: str
    applies: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class LajjitadiAvasthas:
    """
    All six Lajjitadi flags for one planet — independent and non-exclusive
    (BPHS gives no dominance ordering; 45.19-23's modulation is strength-
    scaling plus three house-specific compound rules, carried in notes).
    """

    planet: str
    states: tuple[LajjitadiState, ...]
    active: tuple[str, ...]
    notes: str

    def __post_init__(self) -> None:
        expected = tuple(s.state for s in self.states if s.applies)
        if tuple(self.active) != expected:
            raise ValueError("LajjitadiAvasthas.active must match the flags")


@dataclass(frozen=True, slots=True)
class PlanetAvasthas:
    """All avastha systems for one planet."""

    planet: str
    baladi: BaladiAvastha
    jagradadi: JagradadiAvastha
    deeptadi: DeeptadiAvastha
    lajjitadi: LajjitadiAvasthas


@dataclass(frozen=True, slots=True)
class AvasthaChartResult:
    """Avasthas for every classical planet in one chart."""

    policy: AvasthaPolicy
    planets: dict[str, PlanetAvasthas]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _sign(lon: float) -> int:
    return int(lon % 360.0 // 30)


def _sign_aspects(aspecting: str, from_sign: int, to_sign: int) -> bool:
    dist = (to_sign - from_sign) % 12 + 1
    return dist in _FULL_ASPECT_DISTANCES.get(aspecting, frozenset())


def _relationship(
    planet: str,
    other: str,
    sidereal_longitudes: dict[str, float],
    policy: AvasthaPolicy,
) -> str:
    """Relationship of *planet* toward *other*: friend/neutral/enemy tiers."""
    from .vedic_dignities import (
        NATURAL_FRIENDS, NATURAL_NEUTRALS, NATURAL_ENEMIES,
        planetary_relationships,
    )

    if policy.relationship_scheme == 'natural':
        if other in NATURAL_FRIENDS.get(planet, set()):
            return 'friend'
        if other in NATURAL_NEUTRALS.get(planet, set()):
            return 'neutral'
        return 'enemy'
    for rel in planetary_relationships(sidereal_longitudes):
        if rel.from_planet == planet and rel.to_planet == other:
            compound = rel.compound
            if compound in ('adhi_mitra', 'mitra'):
                return 'friend'
            if compound == 'sama':
                return 'neutral'
            return 'enemy'
    return 'neutral'


def _compound_tier(
    planet: str,
    other: str,
    sidereal_longitudes: dict[str, float],
) -> str:
    """Full compound tier (adhi_mitra..adhi_shatru) for Deeptadi ladders."""
    from .vedic_dignities import planetary_relationships

    for rel in planetary_relationships(sidereal_longitudes):
        if rel.from_planet == planet and rel.to_planet == other:
            return rel.compound
    return 'sama'


def _is_combust(planet: str, sidereal_longitudes: dict[str, float]) -> bool:
    if planet == 'Sun' or planet not in sidereal_longitudes:
        return False
    if 'Sun' not in sidereal_longitudes:
        return False
    elong = abs(
        (sidereal_longitudes[planet] - sidereal_longitudes['Sun'] + 180.0)
        % 360.0 - 180.0
    )
    return elong < _COMBUSTION_ORB_DEG.get(planet, 10.0)


def _navamsa_sign(lon: float) -> int:
    return int(lon % 360.0 // (30.0 / 9)) % 12


def _sign_dignity(planet: str, lon: float) -> tuple[bool, bool, bool]:
    """Sign-level dignity flags: (exaltation sign, own sign, debilitation).

    The avastha texts speak of SIGNS ("own sign or exaltation" — BPHS
    45.5), so these checks are sign-level, not dignity-rank-level: a
    planet at its moolatrikona degrees still occupies its own or
    exaltation SIGN and must satisfy the sign clauses.
    """
    from .vedic_dignities import EXALTATION_SIGN, OWN_SIGNS, DEBILITATION_SIGN

    sign = _sign(lon)
    return (
        sign == EXALTATION_SIGN.get(planet),
        sign in OWN_SIGNS.get(planet, ()),
        sign == DEBILITATION_SIGN.get(planet),
    )


# ---------------------------------------------------------------------------
# 1. Baladi (BPHS 45.3-4)
# ---------------------------------------------------------------------------

def baladi_avastha(
    planet: str,
    sidereal_lon: float,
    policy: AvasthaPolicy | None = None,
) -> BaladiAvastha:
    """
    Baladi age state: 6-degree bands ascending in odd signs, reversed in
    even signs (BPHS 45.3); effect grades per 45.4.  Band boundaries are
    half-open, lower-inclusive (declared convention).
    """
    policy = policy or AvasthaPolicy()
    lon = sidereal_lon % 360.0
    sign = _sign(lon)
    deg = lon % 30.0
    segment = min(int(deg // 6.0), 4)
    sign_is_odd = (sign % 2 == 0)   # 0-based: Aries=0 is the 1st (odd) sign
    state = (
        _BALADI_STATES[segment] if sign_is_odd
        else _BALADI_STATES[4 - segment]
    )
    fraction = _BALADI_FRACTIONS[state]
    if state == 'Vriddha' and policy.vriddha_fraction is not None:
        fraction = policy.vriddha_fraction
    label = {
        'Bala': 'quarter', 'Kumara': 'half', 'Yuva': 'full',
        'Vriddha': 'negligible', 'Mrita': 'nil',
    }[state]
    return BaladiAvastha(
        planet=planet,
        state=state,
        segment_index=segment,
        degree_in_sign=deg,
        sign_is_odd=sign_is_odd,
        effect_fraction=fraction,
        effect_label=label,
    )


# ---------------------------------------------------------------------------
# 2. Jagradadi (BPHS 45.5-6)
# ---------------------------------------------------------------------------

def jagradadi_avastha(
    planet: str,
    sidereal_longitudes: dict[str, float],
    policy: AvasthaPolicy | None = None,
) -> JagradadiAvastha:
    """
    Jagradadi awareness state (BPHS 45.5-6).  The exaltation/debilitation
    clauses override the lordship-relationship clauses when both apply
    (declared doctrine — the verse leaves the overlap unresolved).
    """
    from .vedic_dignities import vedic_dignity

    policy = policy or AvasthaPolicy()
    lon = sidereal_longitudes[planet]
    dig = vedic_dignity(planet, lon)
    in_exalt, in_own, in_debil = _sign_dignity(planet, lon)

    if in_own or in_exalt:
        return JagradadiAvastha(
            planet=planet, state='Jagrat',
            reason='own sign' if in_own else 'exaltation sign',
            effect_fraction=1.0,
        )
    if in_debil:
        return JagradadiAvastha(
            planet=planet, state='Sushupti',
            reason='debilitation (overrides lordship clause)',
            effect_fraction=0.0,
        )
    lord = _RASI_LORDS[_sign(lon)]
    tier = _relationship(planet, lord, sidereal_longitudes, policy)
    if tier in ('friend', 'neutral'):
        return JagradadiAvastha(
            planet=planet, state='Swapna',
            reason=f"sign lord {lord} is a {tier}",
            effect_fraction=0.5,
        )
    return JagradadiAvastha(
        planet=planet, state='Sushupti',
        reason=f"sign lord {lord} is an enemy",
        effect_fraction=0.0,
    )


# ---------------------------------------------------------------------------
# 3. Deeptadi (source-parameterized; the four texts disagree — never merged)
# ---------------------------------------------------------------------------

def deeptadi_avastha(
    planet: str,
    sidereal_longitudes: dict[str, float],
    policy: AvasthaPolicy | None = None,
) -> DeeptadiAvastha:
    """
    Deeptadi state under the policy-selected source's rule table.

    ``bphs_9`` (default, BPHS 45.7-10 e-text nine): exaltation Deepta; own
    Swastha; adhimitra Pramudita; mitra Shanta; sama Deena; conjunct
    malefic Vikala; shatru Dukhita; adhishatru Khala; combust Kopa.
    The other sources' ladders (Saravali 5.2-4; JP 2.16-18; PD 3.18-19)
    use graha-yuddha, varga, and brightness conditions; "benefic/malefic
    varga" is materialized as the navamsa sign lord's nature (declared
    policy — the texts do not name the varga).
    """
    from .vedic_dignities import vedic_dignity
    from .yogas import benefic_malefic_classification

    policy = policy or AvasthaPolicy()
    lon = sidereal_longitudes[planet]
    sign = _sign(lon)
    dig = vedic_dignity(planet, lon)
    in_exalt, in_own, in_debil = _sign_dignity(planet, lon)
    lord = _RASI_LORDS[sign]
    combust = _is_combust(planet, sidereal_longitudes)
    classification = benefic_malefic_classification(sidereal_longitudes)

    if policy.deeptadi_source == 'bphs_9':
        citation = "BPHS 45.7-10 (Santhanam; e-text resolves the printed lacuna)"
        if combust:
            return DeeptadiAvastha(planet, 'Kopa', 'bphs_9',
                                   'eclipsed by the Sun (combust)', citation)
        if in_exalt:
            return DeeptadiAvastha(planet, 'Deepta', 'bphs_9',
                                   'exaltation sign', citation)
        if in_own:
            return DeeptadiAvastha(planet, 'Swastha', 'bphs_9',
                                   'own sign', citation)
        conjunct_malefic = any(
            _sign(sidereal_longitudes[p]) == sign
            for p in _SEVEN_PLANETS
            if p != planet and p in sidereal_longitudes
            and classification.get(p) == 'malefic'
        )
        if conjunct_malefic:
            return DeeptadiAvastha(planet, 'Vikala', 'bphs_9',
                                   'conjunct a malefic', citation)
        tier = _compound_tier(planet, lord, sidereal_longitudes)
        state = {
            'adhi_mitra': 'Pramudita', 'mitra': 'Shanta', 'sama': 'Deena',
            'shatru': 'Dukhita', 'adhi_shatru': 'Khala',
        }.get(tier, 'Deena')
        return DeeptadiAvastha(
            planet, state, 'bphs_9',
            f"sign lord {lord} is {tier} (compound)", citation,
        )

    # Non-BPHS ladders share machinery: dignity, war, varga, brightness.
    from .shadbala import graha_yuddha_pairs
    wars = graha_yuddha_pairs(sidereal_longitudes)
    lost_war = any(w.loser == planet for w in wars)
    nav_lord = _RASI_LORDS[_navamsa_sign(lon)]
    nav_lord_nature = classification.get(nav_lord, 'benefic')
    tier = _relationship(planet, lord, sidereal_longitudes, policy)

    if policy.deeptadi_source == 'saravali_9':
        citation = "Saravali 5.2-4 (Santhanam)"
        if in_exalt:
            return DeeptadiAvastha(planet, 'Dipta', 'saravali_9',
                                   'exaltation', citation)
        if in_own:
            return DeeptadiAvastha(planet, 'Svastha', 'saravali_9',
                                   'own sign', citation)
        if in_debil:
            return DeeptadiAvastha(planet, 'Bhita', 'saravali_9',
                                   'debilitation', citation)
        if lost_war:
            return DeeptadiAvastha(planet, 'Nipidita', 'saravali_9',
                                   'defeated in graha yuddha', citation)
        if combust:
            return DeeptadiAvastha(planet, 'Vikala', 'saravali_9',
                                   'combust', citation)
        if tier == 'friend':
            return DeeptadiAvastha(planet, 'Mudita', 'saravali_9',
                                   "friend's sign", citation)
        if nav_lord_nature == 'benefic':
            return DeeptadiAvastha(
                planet, 'Santa', 'saravali_9',
                f'benefic varga (navamsa lord {nav_lord} — declared policy)',
                citation)
        if nav_lord_nature == 'malefic':
            return DeeptadiAvastha(
                planet, 'Khala', 'saravali_9',
                f'malefic varga (navamsa lord {nav_lord} — declared policy)',
                citation)
        return DeeptadiAvastha(planet, 'Sakta', 'saravali_9',
                               'bright rays (not combust)', citation)

    if policy.deeptadi_source == 'jataka_parijata_10':
        citation = "Jataka Parijata 2.16-18 (Sastri lineage, secondary-verified)"
        if in_exalt or dig.is_mulatrikona:
            return DeeptadiAvastha(planet, 'Dipta', 'jataka_parijata_10',
                                   'exaltation or moolatrikona', citation)
        if in_own:
            return DeeptadiAvastha(planet, 'Svastha', 'jataka_parijata_10',
                                   'own sign', citation)
        if in_debil:
            return DeeptadiAvastha(planet, 'Bhita', 'jataka_parijata_10',
                                   'debilitation', citation)
        if lost_war:
            return DeeptadiAvastha(planet, 'Prapidita', 'jataka_parijata_10',
                                   'defeated in graha yuddha', citation)
        if combust:
            return DeeptadiAvastha(planet, 'Vikala', 'jataka_parijata_10',
                                   'eclipsed by the Sun', citation)
        if tier == 'enemy':
            return DeeptadiAvastha(planet, 'Dina', 'jataka_parijata_10',
                                   'enemy rasi (JP: Dina = enemy — name '
                                   'collides with BPHS Deena = neutral)',
                                   citation)
        if tier == 'friend':
            return DeeptadiAvastha(planet, 'Pramudita', 'jataka_parijata_10',
                                   'friendly sign', citation)
        if nav_lord_nature == 'benefic':
            return DeeptadiAvastha(
                planet, 'Shanta', 'jataka_parijata_10',
                f'benefic varga (navamsa lord {nav_lord} — declared policy)',
                citation)
        if nav_lord_nature == 'malefic':
            return DeeptadiAvastha(
                planet, 'Khala', 'jataka_parijata_10',
                f'malefic varga (navamsa lord {nav_lord} — declared policy)',
                citation)
        return DeeptadiAvastha(planet, 'Sakta', 'jataka_parijata_10',
                               'away from the Sun (not combust)', citation)

    # phaladeepika_11
    citation = "Phaladeepika 3.18-19 (Sastri/wisdomlib)"
    if in_exalt and not dig.is_mulatrikona:
        return DeeptadiAvastha(planet, 'Pradipta', 'phaladeepika_11',
                               'exaltation', citation)
    if dig.is_mulatrikona:
        return DeeptadiAvastha(planet, 'Sukhita', 'phaladeepika_11',
                               'moolatrikona', citation)
    if in_own:
        return DeeptadiAvastha(planet, 'Svastha', 'phaladeepika_11',
                               'own house', citation)
    if in_debil:
        return DeeptadiAvastha(planet, 'Atibhita', 'phaladeepika_11',
                               'depression', citation)
    if lost_war:
        return DeeptadiAvastha(planet, 'Nipidita', 'phaladeepika_11',
                               'overcome in graha yuddha', citation)
    if combust:
        return DeeptadiAvastha(planet, 'Vikala', 'phaladeepika_11',
                               'set/disappeared (combust)', citation)
    if tier == 'enemy':
        return DeeptadiAvastha(planet, 'Suduhkhita', 'phaladeepika_11',
                               "enemy's house", citation)
    if tier == 'friend':
        return DeeptadiAvastha(planet, 'Mudita', 'phaladeepika_11',
                               "friend's house", citation)
    if nav_lord_nature == 'benefic':
        return DeeptadiAvastha(
            planet, 'Shanta', 'phaladeepika_11',
            f'benefic varga (navamsa lord {nav_lord} — declared policy)',
            citation)
    if nav_lord_nature == 'malefic':
        return DeeptadiAvastha(
            planet, 'Khala', 'phaladeepika_11',
            f'malefic varga (navamsa lord {nav_lord} — declared policy)',
            citation)
    return DeeptadiAvastha(planet, 'Shakta', 'phaladeepika_11',
                           'unclouded splendour (not combust)', citation)


# ---------------------------------------------------------------------------
# 4. Lajjitadi (BPHS 45.11-18) — six independent flags
# ---------------------------------------------------------------------------

def lajjitadi_avasthas(
    planet: str,
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: AvasthaPolicy | None = None,
    node_longitudes: dict[str, float] | None = None,
) -> LajjitadiAvasthas:
    """
    The six Lajjitadi conditions (BPHS 45.11-18), each an independent,
    non-exclusive flag with its evidence.  ``node_longitudes`` supplies
    Rahu/Ketu (as Lajjita afflictors only); without them the node clause
    reads unevaluated-false.
    """
    from .yogas import benefic_malefic_classification

    policy = policy or AvasthaPolicy()
    lon = sidereal_longitudes[planet]
    sign = _sign(lon)
    lagna_sign = _sign(lagna_sidereal_lon)
    house = (sign - lagna_sign) % 12 + 1
    classification = benefic_malefic_classification(sidereal_longitudes)
    from .vedic_dignities import vedic_dignity
    dig = vedic_dignity(planet, lon)

    def conjunct(names: tuple[str, ...]) -> list[str]:
        found = [
            p for p in names
            if p != planet and p in sidereal_longitudes
            and _sign(sidereal_longitudes[p]) == sign
        ]
        if node_longitudes:
            found += [
                n for n in ('Rahu', 'Ketu')
                if n in names and n in node_longitudes
                and _sign(node_longitudes[n]) == sign
            ]
        return found

    def aspected_by(predicate) -> list[str]:
        return [
            p for p in _SEVEN_PLANETS
            if p != planet and p in sidereal_longitudes
            and predicate(p)
            and _sign_aspects(p, _sign(sidereal_longitudes[p]), sign)
        ]

    enemies = [
        p for p in _SEVEN_PLANETS
        if p != planet and p in sidereal_longitudes
        and _relationship(planet, p, sidereal_longitudes, policy) == 'enemy'
    ]

    # Lajjita: in the 5th house AND with a node, Sun, Saturn, or Mars.
    lajjita_afflictors = conjunct(('Rahu', 'Ketu', 'Sun', 'Saturn', 'Mars'))
    lajjita = LajjitadiState(
        state='Lajjita',
        applies=house == 5 and bool(lajjita_afflictors),
        evidence=(
            f"house {house}; afflictors with it: "
            + (", ".join(lajjita_afflictors) or "none")
            + ("" if node_longitudes else " (nodes not supplied)")
        ),
    )
    # Garvita: exaltation or moolatrikona.
    garvita = LajjitadiState(
        state='Garvita',
        applies=dig.is_exalted or dig.is_mulatrikona,
        evidence=f"dignity: {dig.dignity_rank}",
    )
    # Kshudhita: enemy's sign OR conjunct an enemy OR aspected by an enemy
    # OR conjunct Saturn.
    sign_lord = _RASI_LORDS[sign]
    in_exalt, in_own, _in_debil = _sign_dignity(planet, lon)
    in_enemy_sign = (
        not in_own and not in_exalt
        and _relationship(planet, sign_lord, sidereal_longitudes, policy)
        == 'enemy'
    )
    conj_enemy = [e for e in enemies
                  if _sign(sidereal_longitudes[e]) == sign]
    asp_enemy = aspected_by(lambda p: p in enemies)
    conj_saturn = planet != 'Saturn' and 'Saturn' in sidereal_longitudes \
        and _sign(sidereal_longitudes['Saturn']) == sign
    kshudhita = LajjitadiState(
        state='Kshudhita',
        applies=bool(in_enemy_sign or conj_enemy or asp_enemy or conj_saturn),
        evidence=(
            f"enemy sign: {in_enemy_sign}; conjunct enemy: "
            f"{', '.join(conj_enemy) or 'none'}; aspected by enemy: "
            f"{', '.join(asp_enemy) or 'none'}; with Saturn: {conj_saturn}"
        ),
    )
    # Trushita: watery sign AND aspected by a malefic AND NOT by a benefic.
    asp_malefic = aspected_by(lambda p: classification.get(p) == 'malefic')
    asp_benefic = aspected_by(lambda p: classification.get(p) == 'benefic')
    trushita = LajjitadiState(
        state='Trushita',
        applies=(sign in _WATERY_SIGNS and bool(asp_malefic)
                 and not asp_benefic),
        evidence=(
            f"watery sign: {sign in _WATERY_SIGNS}; malefic aspects: "
            f"{', '.join(asp_malefic) or 'none'}; benefic aspects: "
            f"{', '.join(asp_benefic) or 'none'}"
        ),
    )
    # Mudita: friendly sign OR conjunct/aspected by a friend? (BPHS: with a
    # benefic or aspected by a benefic) OR conjunct Jupiter.
    in_friend_sign = (
        not in_own and not in_exalt
        and _relationship(planet, sign_lord, sidereal_longitudes, policy)
        == 'friend'
    )
    conj_benefic = [
        p for p in _SEVEN_PLANETS
        if p != planet and p in sidereal_longitudes
        and classification.get(p) == 'benefic'
        and _sign(sidereal_longitudes[p]) == sign
    ]
    conj_jupiter = planet != 'Jupiter' and 'Jupiter' in sidereal_longitudes \
        and _sign(sidereal_longitudes['Jupiter']) == sign
    mudita = LajjitadiState(
        state='Mudita',
        applies=bool(in_friend_sign or conj_benefic or asp_benefic
                     or conj_jupiter),
        evidence=(
            f"friend's sign: {in_friend_sign}; with benefic: "
            f"{', '.join(conj_benefic) or 'none'}; aspected by benefic: "
            f"{', '.join(asp_benefic) or 'none'}; with Jupiter: {conj_jupiter}"
        ),
    )
    # Kshobhita: conjunct the Sun AND (aspected-by/with a malefic OR
    # aspected by an enemy).
    with_sun = planet != 'Sun' and 'Sun' in sidereal_longitudes \
        and _sign(sidereal_longitudes['Sun']) == sign
    other_malefic_with = [
        p for p in _SEVEN_PLANETS
        if p not in (planet, 'Sun') and p in sidereal_longitudes
        and classification.get(p) == 'malefic'
        and _sign(sidereal_longitudes[p]) == sign
    ]
    kshobhita = LajjitadiState(
        state='Kshobhita',
        applies=bool(with_sun and (asp_malefic or other_malefic_with
                                   or asp_enemy)),
        evidence=(
            f"with Sun: {with_sun}; malefic with/aspecting: "
            f"{', '.join(other_malefic_with + asp_malefic) or 'none'}; "
            f"enemy aspecting: {', '.join(asp_enemy) or 'none'}"
        ),
    )

    states = (lajjita, garvita, kshudhita, trushita, mudita, kshobhita)
    return LajjitadiAvasthas(
        planet=planet,
        states=states,
        active=tuple(s.state for s in states if s.applies),
        notes=(
            "Non-exclusive flags (BPHS gives no dominance ordering). "
            "Modulation per 45.18-23: houses held by a Kshudhita or "
            "Kshobhita planet are destroyed; 10th-house "
            "Lajjita/Kshudhita/Kshobhita, 5th-house Lajjita, and "
            "7th-house Kshobhita/Trushita carry specific compound "
            "effects; strength scaling is Shadbala's domain."
        ),
    )


# ---------------------------------------------------------------------------
# Top-level evaluator
# ---------------------------------------------------------------------------

def evaluate_avasthas(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: AvasthaPolicy | None = None,
    node_longitudes: dict[str, float] | None = None,
) -> AvasthaChartResult:
    """
    All four implemented avastha systems for every supplied classical
    planet.  Sayanadi (BPHS 45.30-155) is deferred: it needs birth ghatis
    and the native's name-syllable — inputs beyond the chart.
    """
    policy = policy or AvasthaPolicy()
    planets: dict[str, PlanetAvasthas] = {}
    for planet in _SEVEN_PLANETS:
        if planet not in sidereal_longitudes:
            continue
        planets[planet] = PlanetAvasthas(
            planet=planet,
            baladi=baladi_avastha(planet, sidereal_longitudes[planet], policy),
            jagradadi=jagradadi_avastha(planet, sidereal_longitudes, policy),
            deeptadi=deeptadi_avastha(planet, sidereal_longitudes, policy),
            lajjitadi=lajjitadi_avasthas(
                planet, sidereal_longitudes, lagna_sidereal_lon,
                policy, node_longitudes,
            ),
        )
    return AvasthaChartResult(policy=policy, planets=planets)
