"""
Moira — muhurta.py

Purpose
-------
Vedic Muhurta (electional astrology) doctrine and scoring layer.

This module provides traditional Muhurta classification and basic scoring
built on top of Panchanga + planetary conditions. It is the primary
remaining "practitioner workflow" gap identified in the competitive analysis
for Vedic completeness (Tier 2).

It is intentionally separated from the general `electional.py` scanner:
- `electional.py` = flexible search engine (any predicate, tropical or sidereal)
- `muhurta.py`     = traditional Vedic rules and scoring for auspiciousness

Current Scope
-------------------------------------
- Basic Muhurta classification using Panchanga elements (Tithi, Vara, Nakshatra, Yoga, Karana)
- Traditional auspicious/inauspicious categorizations for the five Panchanga limbs
- Simple scoring surface that practitioners can extend
- Policy for weighting different factors
- Natal Tara/Chandra overlays and repaired bounded sampled-search adapters
- Abhijit/Brahma compatibility predicates; typed source-owned intervals live in named_muhurta

Future increments (per competitive analysis):
- Sunrise-owned and exact-transition search, separate from sampled JD weekday
- Additional named Muhurta intervals and purpose-specific profiles
- Support for additional classical rules (e.g., from BPHS Muhurta chapters, Brihat Samhita)

References (researched source material only)
---------------------------------------------
- Parashara, Brihat Parashara Hora Shastra (BPHS), English translation by R. Santhanam, Chapter 85 "Inauspicious Births" (primary source for Dagdha Yogas, Vishti/Bhadra Karana, Gandanta, etc.).
- Varahamihira, Brihat Samhita, Chapters 98–104 (Muhurta context).
- Daivajna Rama, Muhurta Chintamani, Avasthi commentary (2004), Vivaha 52/54:
  eighth daylight division and Wednesday exclusion; named_muhurta owns the new policy.
- Arunadatta on Ashtanga Hridaya Sutrasthana 2.1 supports the fixed-ghati
  Brahma profile in named_muhurta. The proportional-night predicate here is
  separately identified compatibility behavior.
- These historical source leads are not an edition-collated proof of every
  scoring rule. VED-004/006 retain the existing profile and repair composition;
  source-specific additions and variants require their own admission evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal
from .electional import ElectionalPolicy, ElectionalWindow

from .panchanga import (
    PanchangaResult,
    _ASHUBHA_YOGA_INDICES,
)

# Import Nakshatra names for robust name<->index mapping (used for Tara Bala etc.)
from .sidereal import NAKSHATRA_NAMES

__all__ = [
    "MuhurtaPolicy",
    "MuhurtaClassification",
    "MuhurtaScore",
    "classify_muhurta",
    "score_muhurta",
    # Natal-personalized layer
    "TARA_NAMES",
    "TaraBala",
    "tara_bala",
    "ChandraBala",
    "chandra_bala",
    "PersonalMuhurtaScore",
    "personal_muhurta_score",
]


@dataclass(frozen=True, slots=True)
class MuhurtaPolicy:
    """
    Policy controlling how Muhurta classification and scoring is performed.

    Weights apply to the existing Moira classification/Tara/Chandra profile.
    They do not select another school's rules, cancellations or activity doctrine.
    """
    weight_tithi: float = 1.0
    weight_vara: float = 1.0
    weight_nakshatra: float = 1.0
    weight_yoga: float = 1.5     # Traditionally very important for Muhurta
    weight_karana: float = 0.8
    # Natal-personalized overlays (personal_muhurta_score); Tara and Chandra
    # Bala are the classical benchmark pair for individual muhurta.
    weight_tara: float = 1.0
    weight_chandra: float = 1.0

    # Future: allow disabling certain classical rules
    use_classical_ashubha_yoga: bool = True

    def __post_init__(self) -> None:
        # This reserved field never selected an alternate rule set. Fail closed
        # rather than acknowledging a choice the evaluator does not implement.
        if self.use_classical_ashubha_yoga is not True:
            raise ValueError("use_classical_ashubha_yoga is reserved and must remain True")
        weights = (
            "weight_tithi", "weight_vara", "weight_nakshatra", "weight_yoga",
            "weight_karana", "weight_tara", "weight_chandra",
        )
        for name in weights:
            value = _finite_number(name, getattr(self, name))
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
            object.__setattr__(self, name, value)
        # Bound the worst possible component magnitudes, including the 1.5x
        # Yoga and 2x Chandrashtama penalties, so aggregation cannot overflow.
        try:
            bound = math.fsum(getattr(self, name) * (
                1.5 if name == "weight_yoga" else 2 if name == "weight_chandra" else 1
            ) for name in weights)
        except OverflowError as exc:
            raise ValueError("Muhurta weights would overflow score aggregation") from exc
        if not math.isfinite(bound):
            raise ValueError("Muhurta weights would overflow score aggregation")

    @property
    def rule_profile(self) -> str:
        """Identity of the existing rule set, separate from configurable weights."""
        return "moira.muhurta.existing_weighted_profile.v1"


def _finite_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number, without coercion")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class MuhurtaClassification:
    """
    Structured classification of a moment for Muhurta purposes.
    """
    overall: Literal["auspicious", "neutral", "inauspicious"]
    tithi: Literal["auspicious", "neutral", "inauspicious"]
    vara: Literal["auspicious", "neutral", "inauspicious"]
    nakshatra: Literal["auspicious", "neutral", "inauspicious"]
    yoga: Literal["auspicious", "neutral", "inauspicious"]
    karana: Literal["auspicious", "neutral", "inauspicious"]

    # Human-readable reasons (for UI / reports)
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MuhurtaScore:
    """
    Quantitative score for a moment from a Muhurta perspective.
    Range is intentionally not normalized yet — callers can rescale.
    """
    total: float
    breakdown: dict[str, float]  # e.g. {"yoga": 1.5, "tithi": 0.8, ...}
    classification: MuhurtaClassification


# ------------------------------------------------------------------
# Doctrine tables derived strictly from researched classical sources
# (BPHS Ch. 85 via Santhanam translation, Muhurta Chintamani, etc.)
# ------------------------------------------------------------------

# Dagdha (Burnt) Yogas from BPHS Ch. 85 — highly inauspicious Tithi + Vara combinations
# Format: (tithi_index 0-based, vara_index 0-based Sunday=0)
_DAGDHA_YOGAS: frozenset[tuple[int, int]] = frozenset({
    (11, 0),   # Sunday + 12th Tithi
    (10, 1),   # Monday + 11th Tithi
    (4, 2),    # Tuesday + 5th Tithi
    (2, 3), (3, 3),   # Wednesday + 3rd or 4th Tithi (some editions vary)
    (5, 4),    # Thursday + 6th Tithi
    (7, 5),    # Friday + 8th Tithi
    (8, 6),    # Saturday + 9th Tithi
})

# Vishti / Bhadra Karana is classically highly inauspicious (ruled by Saturn)
# Movable Karanas cycle: indices 1-56 (0-based in our 0-59 Karana range)
# Vishti is the 7th in the 7-Karana cycle (typically indices congruent to 6 mod 7 in the movable range)
def _is_vishti_karana(karana_index: int) -> bool:
    """Returns True for Vishti/Bhadra Karana (highly inauspicious per BPHS)."""
    if karana_index in (0, 57, 58, 59):  # Fixed Karanas
        return False
    # Movable Karanas 1-56 (0-based). Vishti is every 7th starting appropriately.
    # Standard: positions where (karana_index - 1) % 7 == 6 in the movable cycle
    movable_pos = karana_index - 1
    return (movable_pos % 7) == 6


def _classify_tithi(index: int) -> Literal["auspicious", "neutral", "inauspicious"]:
    """
    Classification using the classical Nanda-Bhadra-Jaya-Rikta-Poorna framework
    (widely used in Muhurta Chintamani and related texts).

    Sources: Muhurta Chintamani; cross-referenced in discussions of BPHS principles.
    """
    if index == 29:  # Amavasya
        return "inauspicious"
    if index in (3, 8, 13):  # Rikta (4,9,14) — generally avoided for major positive works
        return "inauspicious"

    # Nanda (1,6,11) — joyful
    if index in (0, 5, 10):
        return "auspicious"
    # Bhadra (2,7,12)
    if index in (1, 6, 11):
        return "auspicious"
    # Jaya/Vijaya (3,8,13)
    if index in (2, 7, 12):
        return "auspicious"
    # Poorna (5,10,15) — full/complete, highly auspicious
    if index in (4, 9, 14):
        return "auspicious"

    return "neutral"


def _classify_vara(index: int, tithi_index: int) -> Literal["auspicious", "neutral", "inauspicious"]:
    """Checks Dagdha combinations from BPHS Ch. 85."""
    if (tithi_index, index) in _DAGDHA_YOGAS:
        return "inauspicious"
    # Benefic weekdays (traditional preference when not in Dagdha)
    if index in (1, 3, 4, 5):  # Monday, Wednesday, Thursday, Friday
        return "neutral"
    return "neutral"


# ------------------------------------------------------------------
# Tara Bala — the nine-tara cycle from the janma nakshatra
#
# Governing object: Navatara Chakra (Muhurta Chintamani; standard
# Panchanga Shuddhi doctrine).  Count from the janma nakshatra to the
# target nakshatra inclusive; reduce modulo 9:
#
#   1 Janma (caution)      2 Sampat (fav)    3 Vipat (unfav)
#   4 Kshema (fav)         5 Pratyari (unfav) 6 Sadhaka (fav)
#   7 Vadha (unfav)        8 Mitra (fav)     9 Parama Mitra (fav)
#
# Janma is classified 'caution' — classically avoided for major
# undertakings but not malefic like Vipat/Pratyari/Vadha; the polarity
# is exposed so callers can apply activity-specific doctrine.
# ------------------------------------------------------------------

TARA_NAMES: tuple[str, ...] = (
    "Janma", "Sampat", "Vipat", "Kshema", "Pratyari",
    "Sadhaka", "Vadha", "Mitra", "Parama Mitra",
)

_TARA_POLARITY: tuple[str, ...] = (
    "caution",      # 1 Janma
    "favorable",    # 2 Sampat
    "unfavorable",  # 3 Vipat
    "favorable",    # 4 Kshema
    "unfavorable",  # 5 Pratyari
    "favorable",    # 6 Sadhaka
    "unfavorable",  # 7 Vadha
    "favorable",    # 8 Mitra
    "favorable",    # 9 Parama Mitra
)


@dataclass(frozen=True, slots=True)
class TaraBala:
    """
    Tara Bala of a target nakshatra relative to the janma nakshatra.

    Attributes
    ----------
    janma_nakshatra_index : int
        0-based janma (birth Moon) nakshatra index (0 = Ashwini).
    target_nakshatra_index : int
        0-based nakshatra index of the moment being judged.
    count : int
        Inclusive count from janma to target (1-27).
    tara_number : int
        Position in the nine-tara cycle (1-9).
    tara_name : str
        Name from ``TARA_NAMES``.
    polarity : str
        ``'favorable'`` | ``'unfavorable'`` | ``'caution'`` (Janma tara).
    favorable : bool
        Convenience: ``polarity == 'favorable'``.
    """

    janma_nakshatra_index:  int
    target_nakshatra_index: int
    count:       int
    tara_number: int
    tara_name:   str
    polarity:    str
    favorable:   bool

    def __post_init__(self) -> None:
        if not (0 <= self.janma_nakshatra_index <= 26):
            raise ValueError(
                f"TaraBala.janma_nakshatra_index must be in [0, 26], "
                f"got {self.janma_nakshatra_index}"
            )
        if not (0 <= self.target_nakshatra_index <= 26):
            raise ValueError(
                f"TaraBala.target_nakshatra_index must be in [0, 26], "
                f"got {self.target_nakshatra_index}"
            )
        if not (1 <= self.tara_number <= 9):
            raise ValueError(
                f"TaraBala.tara_number must be in [1, 9], got {self.tara_number}"
            )


def tara_bala(
    janma_nakshatra_index: int,
    target_nakshatra_index: int,
) -> TaraBala:
    """
    Compute Tara Bala for a target nakshatra relative to the janma nakshatra.

    The count runs from janma to target inclusive (janma itself = 1),
    reduced through the nine-tara cycle.

    Source: Navatara Chakra doctrine (Muhurta Chintamani; standard
    Panchanga Shuddhi practice).
    """
    for name, value in (("janma_nakshatra_index", janma_nakshatra_index),
                        ("target_nakshatra_index", target_nakshatra_index)):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 26:
            raise ValueError(f"{name} must be an integer in [0, 26]")
    count = (target_nakshatra_index - janma_nakshatra_index) % 27 + 1
    tara_number = (count - 1) % 9 + 1
    polarity = _TARA_POLARITY[tara_number - 1]
    return TaraBala(
        janma_nakshatra_index=janma_nakshatra_index,
        target_nakshatra_index=target_nakshatra_index,
        count=count,
        tara_number=tara_number,
        tara_name=TARA_NAMES[tara_number - 1],
        polarity=polarity,
        favorable=(polarity == "favorable"),
    )


# ------------------------------------------------------------------
# Chandra Bala — transit Moon's house from the natal Moon (janma rashi)
#
# Governing object: standard Muhurta doctrine (Chandra Shuddhi).
# Favorable: 1, 3, 6, 7, 10, 11.  Neutral: 2, 5.
# Unfavorable: 4, 8, 9, 12 — the 8th (Chandrashtama) is the strongest
# affliction and is flagged separately.
# ------------------------------------------------------------------

_CHANDRA_FAVORABLE:   frozenset[int] = frozenset({1, 3, 6, 7, 10, 11})
_CHANDRA_NEUTRAL:     frozenset[int] = frozenset({2, 5})
_CHANDRA_UNFAVORABLE: frozenset[int] = frozenset({4, 8, 9, 12})


@dataclass(frozen=True, slots=True)
class ChandraBala:
    """
    Chandra Bala of the transit Moon relative to the natal Moon sign.

    Attributes
    ----------
    janma_rashi_index : int
        Natal Moon's sidereal sign index (0 = Aries).
    transit_rashi_index : int
        Transit Moon's sidereal sign index.
    house_from_moon : int
        Whole-sign house of the transit Moon counted from the janma
        rashi (1-12).
    polarity : str
        ``'favorable'`` | ``'neutral'`` | ``'unfavorable'``.
    favorable : bool
        Convenience: ``polarity == 'favorable'``.
    is_chandrashtama : bool
        True when the transit Moon is in the 8th from the natal Moon —
        the strongest Chandra affliction.
    """

    janma_rashi_index:   int
    transit_rashi_index: int
    house_from_moon:     int
    polarity:            str
    favorable:           bool
    is_chandrashtama:    bool

    def __post_init__(self) -> None:
        if not (1 <= self.house_from_moon <= 12):
            raise ValueError(
                f"ChandraBala.house_from_moon must be in [1, 12], "
                f"got {self.house_from_moon}"
            )


def chandra_bala(
    janma_moon_sidereal_lon: float,
    transit_moon_sidereal_lon: float,
) -> ChandraBala:
    """
    Compute Chandra Bala from natal and transit Moon sidereal longitudes.

    Whole-sign count from the janma rashi.  Source: standard Muhurta
    Chandra Shuddhi doctrine (favorable 1/3/6/7/10/11, neutral 2/5,
    unfavorable 4/8/9/12 with the 8th as Chandrashtama).
    """
    janma_moon_sidereal_lon = _finite_number("janma_moon_sidereal_lon", janma_moon_sidereal_lon)
    transit_moon_sidereal_lon = _finite_number("transit_moon_sidereal_lon", transit_moon_sidereal_lon)
    janma_rashi = int(janma_moon_sidereal_lon % 360.0 // 30)
    transit_rashi = int(transit_moon_sidereal_lon % 360.0 // 30)
    house = (transit_rashi - janma_rashi) % 12 + 1
    if house in _CHANDRA_FAVORABLE:
        polarity = "favorable"
    elif house in _CHANDRA_NEUTRAL:
        polarity = "neutral"
    else:
        polarity = "unfavorable"
    return ChandraBala(
        janma_rashi_index=janma_rashi,
        transit_rashi_index=transit_rashi,
        house_from_moon=house,
        polarity=polarity,
        favorable=(polarity == "favorable"),
        is_chandrashtama=(house == 8),
    )


@dataclass(frozen=True, slots=True)
class PersonalMuhurtaScore:
    """
    Natal-personalized Muhurta score: the generic Panchanga score plus
    Tara Bala and Chandra Bala relative to the native's Moon.

    ``total`` = generic total + weighted tara + weighted chandra;
    ``breakdown`` carries every component (transparency doctrine).
    """

    total:          float
    breakdown:      dict[str, float]
    classification: MuhurtaClassification
    tara:           TaraBala
    chandra:        ChandraBala


def personal_muhurta_score(
    panchanga: PanchangaResult,
    janma_moon_sidereal_lon: float,
    transit_moon_sidereal_lon: float,
    policy: "MuhurtaPolicy | None" = None,
) -> PersonalMuhurtaScore:
    """
    Score a moment for a specific native: generic Muhurta score overlaid
    with Tara Bala (nakshatra cycle from the janma nakshatra) and Chandra
    Bala (transit Moon's house from the natal Moon).

    Parameters
    ----------
    panchanga : PanchangaResult
        The moment's Panchanga (for the generic score).
    janma_moon_sidereal_lon : float
        Natal Moon sidereal longitude (defines janma nakshatra and rashi).
    transit_moon_sidereal_lon : float
        Transit Moon sidereal longitude at the judged moment.
    policy : MuhurtaPolicy, optional
        Weights; ``weight_tara`` / ``weight_chandra`` govern the overlay.

    Scoring: favorable tara/chandra add the full weight; unfavorable
    subtract it; Janma tara (caution) and neutral chandra add nothing.
    Chandrashtama doubles the chandra penalty (strongest affliction).
    """
    policy = MuhurtaPolicy() if policy is None else policy
    if not isinstance(policy, MuhurtaPolicy):
        raise ValueError("policy must be MuhurtaPolicy")
    janma_moon_sidereal_lon = _finite_number("janma_moon_sidereal_lon", janma_moon_sidereal_lon)
    transit_moon_sidereal_lon = _finite_number("transit_moon_sidereal_lon", transit_moon_sidereal_lon)
    base = score_muhurta(panchanga, policy)

    from .sidereal import _nakshatra_sector

    _, janma_nak, _ = _nakshatra_sector(janma_moon_sidereal_lon)
    _, target_nak, _ = _nakshatra_sector(transit_moon_sidereal_lon)
    tara = tara_bala(janma_nak, target_nak)
    chandra = chandra_bala(janma_moon_sidereal_lon, transit_moon_sidereal_lon)

    tara_score = policy.weight_tara * (
        1.0 if tara.polarity == "favorable"
        else -1.0 if tara.polarity == "unfavorable"
        else 0.0
    )
    if chandra.is_chandrashtama:
        chandra_score = policy.weight_chandra * -2.0
    else:
        chandra_score = policy.weight_chandra * (
            1.0 if chandra.polarity == "favorable"
            else -1.0 if chandra.polarity == "unfavorable"
            else 0.0
        )

    breakdown = dict(base.breakdown)
    breakdown["tara"] = tara_score
    breakdown["chandra"] = chandra_score

    return PersonalMuhurtaScore(
        total=base.total + tara_score + chandra_score,
        breakdown=breakdown,
        classification=base.classification,
        tara=tara,
        chandra=chandra,
    )


def _classify_nakshatra(
    nakshatra_name: str | None,
    janma_nakshatra: str | None = None,
) -> Literal["auspicious", "neutral", "inauspicious"]:
    """
    Classification using Tara Bala (relative to Janma Nakshatra) + Uttama list
    from classical Muhurta sources.

    Sources:
    - Tara Bala: Standard in Muhurta Chintamani and Panchanga Shuddhi.
    - Uttama Nakshatras: Muhurta Chintamani (as referenced in traditional lists).
    """
    if not nakshatra_name:
        return "neutral"

    # Gandanta junctions (problematic per multiple sources including BPHS context)
    gandanta = {"Revati", "Ashlesha", "Jyeshta", "Ashwini", "Magha", "Mula"}
    if nakshatra_name in gandanta:
        return "inauspicious"

    # Uttama (best) Nakshatras per Muhurta Chintamani tradition
    uttama = {
        "Ashwini", "Rohini", "Mrigashira", "Pushya", "Uttara Phalguni",
        "Hasta", "Chitra", "Uttara Ashadha", "Shravana", "Uttara Bhadrapada"
    }
    if nakshatra_name in uttama:
        return "auspicious"

    # Tara Bala (if Janma Nakshatra provided): count from janma to target,
    # 9-tara cycle.  Favorable: Sampat/Kshema/Sadhaka/Mitra/Parama Mitra.
    # Unfavorable: Vipat/Pratyari/Vadha.  Janma itself is cautionary and
    # classified neutral here (activity-dependent per Muhurta Chintamani).
    if janma_nakshatra and (
        janma_nakshatra in NAKSHATRA_NAMES and nakshatra_name in NAKSHATRA_NAMES
    ):
        bala = tara_bala(
            NAKSHATRA_NAMES.index(janma_nakshatra),
            NAKSHATRA_NAMES.index(nakshatra_name),
        )
        if bala.polarity == "favorable":
            return "auspicious"
        if bala.polarity == "unfavorable":
            return "inauspicious"

    return "neutral"


def _nakshatra_name_from_panchanga(panchanga: PanchangaResult) -> str | None:
    """Return the live Nakshatra vessel name without assuming one field spelling."""

    nakshatra = getattr(panchanga, "nakshatra", None)
    if nakshatra is None:
        return None
    return getattr(nakshatra, "nakshatra", None) or getattr(nakshatra, "name", None)


def _classify_karana(index: int) -> Literal["auspicious", "neutral", "inauspicious"]:
    if _is_vishti_karana(index):
        return "inauspicious"
    return "neutral"


def classify_muhurta(
    panchanga: PanchangaResult,
    policy: MuhurtaPolicy | None = None,
) -> MuhurtaClassification:
    """
    Classify a Panchanga moment according to Muhurta considerations.

    Doctrine drawn from:
    - BPHS Ch. 85 (Santhanam translation): Dagdha Yogas, Vishti Karana, Gandanta, etc.
    - Classical Muhurta tradition for Panchanga limb evaluation.
    """
    policy = MuhurtaPolicy() if policy is None else policy
    if not isinstance(policy, MuhurtaPolicy):
        raise ValueError("policy must be MuhurtaPolicy")

    is_ashubha_yoga = panchanga.yoga.index in _ASHUBHA_YOGA_INDICES

    tithi_class = _classify_tithi(panchanga.tithi.index)
    vara_class = _classify_vara(panchanga.vara.index, panchanga.tithi.index)
    nak_class = _classify_nakshatra(_nakshatra_name_from_panchanga(panchanga))
    yoga_class = "inauspicious" if is_ashubha_yoga else "auspicious"
    karana_class = _classify_karana(panchanga.karana.index)

    # Overall judgment (conservative — multiple inauspicious factors compound)
    bad_count = sum(
        1 for c in (tithi_class, vara_class, nak_class, yoga_class, karana_class)
        if c == "inauspicious"
    )

    if bad_count >= 2 or (is_ashubha_yoga and bad_count >= 1):
        overall = "inauspicious"
    elif bad_count == 1:
        overall = "neutral"
    else:
        overall = "auspicious"

    reasons: list[str] = []
    if is_ashubha_yoga:
        reasons.append(f"Ashubha Yoga: {panchanga.yoga.name}")
    if (panchanga.tithi.index, panchanga.vara.index) in _DAGDHA_YOGAS:
        reasons.append("Dagdha Yoga (BPHS Ch. 85)")
    if _is_vishti_karana(panchanga.karana.index):
        reasons.append("Vishti / Bhadra Karana (highly inauspicious)")

    return MuhurtaClassification(
        overall=overall,
        tithi=tithi_class,
        vara=vara_class,
        nakshatra=nak_class,
        yoga=yoga_class,
        karana=karana_class,
        reasons=tuple(reasons),
    )


def score_muhurta(
    panchanga: PanchangaResult,
    policy: MuhurtaPolicy | None = None,
) -> MuhurtaScore:
    """
    Produce a numeric Muhurta score for the given moment.
    Higher is better. Uses researched classical factors from BPHS etc.
    """
    policy = MuhurtaPolicy() if policy is None else policy
    if not isinstance(policy, MuhurtaPolicy):
        raise ValueError("policy must be MuhurtaPolicy")
    classification = classify_muhurta(panchanga, policy)

    breakdown: dict[str, float] = {}

    # Scoring based on researched avoidances (BPHS Ch. 85 emphasis)
    breakdown["tithi"] = policy.weight_tithi * (1.0 if classification.tithi == "auspicious" else -0.5 if classification.tithi == "inauspicious" else 0.0)
    breakdown["vara"] = policy.weight_vara * (1.0 if classification.vara == "auspicious" else -0.5 if classification.vara == "inauspicious" else 0.0)
    breakdown["nakshatra"] = policy.weight_nakshatra * (1.0 if classification.nakshatra == "auspicious" else -0.5 if classification.nakshatra == "inauspicious" else 0.0)
    breakdown["yoga"] = policy.weight_yoga * (1.0 if classification.yoga == "auspicious" else -1.5 if classification.yoga == "inauspicious" else 0.0)
    breakdown["karana"] = policy.weight_karana * (1.0 if classification.karana == "auspicious" else -1.0 if classification.karana == "inauspicious" else 0.0)

    total = sum(breakdown.values())

    return MuhurtaScore(
        total=total,
        breakdown=breakdown,
        classification=classification,
    )


# ------------------------------------------------------------------
# Named Classical Muhurtas (researched from classical sources)
# ------------------------------------------------------------------

def is_abhijit_muhurta(
    sunrise_jd: float,
    sunset_jd: float,
    query_jd: float,
) -> bool:
    """
    Returns True if the query time falls within Abhijit Muhurta.

    Geometry from Muhurta Chintamani, Avasthi 2004, Vivaha v.52:
    the eighth of fifteen equal daylight parts, centered on the sunrise/
    sunset midpoint (not an independently solved meridian transit).
    This legacy predicate does not evaluate the v.54 Wednesday exclusion.
    See named_muhurta for attributed intervals and explicit rule application.
    """
    if sunset_jd <= sunrise_jd:
        return False

    daylight = sunset_jd - sunrise_jd
    muhurta_length = daylight / 15.0

    abhijit_start = sunrise_jd + (7 * muhurta_length)
    abhijit_end = abhijit_start + muhurta_length

    return abhijit_start <= query_jd < abhijit_end


def is_brahma_muhurta(
    sunrise_jd: float,
    sunset_jd: float,
    query_jd: float,
) -> bool:
    """
    Returns True if the query time falls within Brahma Muhurta.

    Legacy proportional-night convention: the fourteenth of fifteen parts
    of the preceding sunset-to-sunrise interval. Only a twelve-hour night
    gives 96 to 48 minutes before sunrise. This is not Arunadatta's fixed
    ghati reading of Ashtanga Hridaya 2.1. See named_muhurta for separately
    attributed fixed-time and compatibility profiles. Valid arithmetic here
    is retained for existing callers.
    """
    if sunrise_jd <= sunset_jd:
        return False

    night_length = sunrise_jd - sunset_jd
    muhurta_length = night_length / 15.0

    # 14th Muhurta of night: starts after 13 Muhurtas from sunset
    brahma_start = sunset_jd + (13 * muhurta_length)
    brahma_end = brahma_start + muhurta_length

    return brahma_start <= query_jd < brahma_end


__all__.extend(["is_abhijit_muhurta", "is_brahma_muhurta"])


# ------------------------------------------------------------------
# Activity-Specific Muhurta Guidance (researched from classical sources)
# Sources: Muhurta Chintamani (Daivajña Rāmācārya), cross-referenced with
# BPHS principles and traditional summaries.
# ------------------------------------------------------------------

ACTIVITY_MUHURTA_GUIDANCE: dict[str, dict] = {
    "marriage": {  # Vivaha Muhurta
        "good_tithis": [1, 2, 3, 4, 6, 7, 9, 10, 11, 12, 13],  # Shukla emphasis; avoid Rikta 4,9,14 + Amavasya
        "preferred_tithis": [2, 3, 5, 7, 10, 11, 13],  # From Muhurta Chintamani
        "avoid_tithis": [0, 3, 8, 13, 29],  # Rikta + Amavasya (0-based: 3=4th, etc.)
        "good_nakshatras": [
            "Rohini", "Mrigashira", "Pushya", "Uttara Phalguni", "Hasta",
            "Swati", "Anuradha", "Uttara Ashadha", "Shravana", "Uttara Bhadrapada", "Revati"
        ],
        "avoid_nakshatras": [
            "Bharani", "Krittika", "Ardra", "Ashlesha", "Jyeshtha",
            "Purva Phalguni", "Purva Ashadha", "Purva Bhadrapada", "Mula", "Vishakha"
        ],
        "good_yogas": ["Sarvarthasiddhi", "Siddhi", "Brahma", "Harshana", "Ravi"],
        "avoid_yogas": ["Vishkumbha", "Vajra", "Ganda", "Atiganda", "Vyaghata", "Parigha", "Vaidhriti", "Vyatipata", "Shula"],
        "preferred_varas": [1, 3, 4, 5],  # Mon, Wed, Thu, Fri
        "karana": "Avoid Vishti/Bhadra",
        "notes": "Strong Jupiter and benefic influences on Lagna/Moon highly recommended. Many doshas have pariharas in the text."
    },
    "house_construction": {  # Griharambha / Foundation
        "good_tithis": [1, 2, 3, 4, 6, 7, 9, 10, 12, 13],  # Similar to marriage, Shukla preferred
        "preferred_tithis": [2, 3, 5, 7, 10, 13],
        "avoid_tithis": [3, 8, 13, 29],  # Rikta + Amavasya
        "good_nakshatras": [
            "Ashwini", "Rohini", "Mrigashira", "Pushya", "Uttara Phalguni",
            "Hasta", "Chitra", "Uttara Ashadha", "Shravana", "Uttara Bhadrapada"
        ],
        "avoid_nakshatras": [
            "Bharani", "Krittika", "Ardra", "Ashlesha", "Jyeshtha",
            "Purva Phalguni", "Purva Ashadha", "Purva Bhadrapada", "Mula"
        ],
        "preferred_varas": [1, 3, 4, 5],  # Monday, Wednesday, Thursday, Friday
        "critical": "4th and 8th bhava shuddhi from Muhurta Lagna is mandatory (no malefics, especially Saturn/Mars in 8th).",
        "notes": "Uttarayana strongly preferred. Strong emphasis on Vastu alignment and specific Lagna (Taurus, Leo, Aquarius best)."
    },
    "house_entry": {  # Grihapravesh
        "good_tithis": [1, 2, 3, 4, 6, 7, 9, 10, 12, 13],  # Shukla Paksha emphasis
        "preferred_tithis": [2, 3, 5, 7, 10, 13],
        "avoid_tithis": [3, 8, 13, 29],
        "good_nakshatras": [  # Overlap with construction, often fixed signs favored
            "Rohini", "Mrigashira", "Pushya", "Uttara Phalguni", "Hasta",
            "Chitra", "Shravana", "Uttara Bhadrapada"
        ],
        "avoid_nakshatras": [
            "Bharani", "Krittika", "Ashlesha", "Jyeshtha", "Purva trio", "Mula"
        ],
        "preferred_varas": [1, 3, 4, 5],
        "critical": "Strong 10th bhava shuddhi from Muhurta Lagna.",
        "notes": "Often done with family and sacred fire. Moon should be strong."
    },
    "travel": {  # Yatra Muhurta
        "good_tithis": [2, 3, 5, 7, 10, 11, 13],  # Generally lighter than marriage
        "avoid_tithis": [3, 8, 13, 29],  # Rikta + Amavasya
        "good_nakshatras": [
            "Ashwini", "Rohini", "Mrigashira", "Pushya", "Hasta",
            "Chitra", "Swati", "Anuradha", "Shravana"
        ],
        "avoid_nakshatras": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Jyeshtha", "Mula"],
        "preferred_varas": [1, 3, 4, 5],  # Avoid Tuesday/Saturday in many texts
        "notes": "Direction and purpose matter greatly. Specific tyajya vara-nakshatra combinations exist in Muhurta Chintamani for travel."
    },
}

def get_muhurta_guidance_for_activity(activity: str) -> dict | None:
    """Returns the researched guidance dict for a given activity, or None."""
    return ACTIVITY_MUHURTA_GUIDANCE.get(activity.lower())


# ------------------------------------------------------------------
# Scorer and Improved Integration Helper
# ------------------------------------------------------------------

def muhurta_scorer(
    chart: object,
    janma_nakshatra: str | None = None,
    policy: MuhurtaPolicy | None = None,
    *,
    janma_moon_sidereal_lon: float | None = None,
    ayanamsa_system: str = "Lahiri",
    reader=None,
) -> float:
    """Scalar adapter over the inspectable chart scorer.

    Natal Moon longitude is required for personalization. A legacy Nakshatra
    name may corroborate it, but cannot supply a natal sign or Chandra Bala.
    Missing chart inputs raise instead of returning a fabricated score.
    """
    from .muhurta_search import _natal_moon, muhurta_score_for_chart
    natal = _natal_moon(janma_moon_sidereal_lon, janma_nakshatra)
    return muhurta_score_for_chart(
        chart, janma_moon_sidereal_lon=natal, ayanamsa_system=ayanamsa_system,
        policy=policy, reader=reader,
    ).score.total


def find_best_muhurta_windows(
    start_jd: float,
    end_jd: float,
    latitude: float,
    longitude: float,
    janma_nakshatra: str | None = None,
    muhurta_policy: MuhurtaPolicy | None = None,
    electional_policy: ElectionalPolicy | None = None,
    min_score: float = 0.0,
    *,
    reader=None,
    janma_moon_sidereal_lon: float | None = None,
    ayanamsa_system: str = "Lahiri",
) -> list[tuple[ElectionalWindow, float]]:
    """Compatibility tuple view of ``find_muhurta_windows``.

    Coordinates remain validated for signature compatibility, but this admitted
    geocentric/JD-weekday product evaluates no location, houses or Lagna factor.
    ElectionalPolicy supplies cadence and an optional result cap only. Reject
    incompatible frame, body, refinement and gap choices explicitly. The typed
    search retains threshold brackets, peak receipts and truncation evidence.
    """
    from .muhurta_search import _natal_moon, MuhurtaSearchPolicy, find_muhurta_windows
    lat = _finite_number("latitude", latitude)
    lon = _finite_number("longitude", longitude)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude/longitude are outside geographic bounds")
    natal = _natal_moon(janma_moon_sidereal_lon, janma_nakshatra)
    scan = ElectionalPolicy() if electional_policy is None else electional_policy
    if not isinstance(scan, ElectionalPolicy):
        raise ValueError("electional_policy must be ElectionalPolicy")
    step = _finite_number("step_days", scan.step_days)
    gap = _finite_number("merge_gap_days", scan.effective_merge_gap)
    if not step <= gap < 2 * step:
        raise ValueError("Muhurta requires consecutive samples; merge gap must be >= step and < 2 steps")
    if scan.boundary_refine_steps != 0:
        raise ValueError("Muhurta sampled search does not admit boundary refinement")
    if scan.bodies is not None and (len(scan.bodies) != 2 or set(scan.bodies) != {"Sun", "Moon"}):
        raise ValueError("Muhurta sampled search requires exactly Sun and Moon")
    if scan.zodiac_frame == "sidereal" and (
        scan.ayanamsa_system != ayanamsa_system or scan.ayanamsa_mode != "true"
    ):
        raise ValueError("ElectionalPolicy sidereal frame conflicts with Muhurta ayanamsa")
    search = find_muhurta_windows(start_jd, end_jd,
        janma_moon_sidereal_lon=natal, reader=reader,
        policy=MuhurtaSearchPolicy(
            ayanamsa_system=ayanamsa_system,
            muhurta_policy=MuhurtaPolicy() if muhurta_policy is None else muhurta_policy,
            step_days=step, min_score=min_score,
            max_results=128 if scan.max_windows is None else scan.max_windows,
        ),
    )
    return [(ElectionalWindow(
        jd_start=w.jd_start, jd_end=w.jd_end,
        duration_hours=(w.jd_end - w.jd_start) * 24,
        qualifying_jds=w.qualifying_jds,
    ), w.peak.score.total) for w in search.windows]
