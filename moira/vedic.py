"""
moira.vedic — Vedic astrology surface.

Builds on ``moira.essentials`` and collects every Vedic-domain subsystem
into a single, coherent import surface: panchanga, sidereal/ayanamsa,
nakshatra, varga (divisional charts), Vedic dignities, Vimshottari and
alternate dasha systems, Jaimini karakas, Ashtakavarga, and Shadbala.

This module does not include the full Western classical surface
(Arabic lots, Firdaria, Zodiacal Releasing, Huber, etc.). For that,
use ``moira.classical``. For the complete surface, use ``moira.facade``.

Usage
-----
    from moira.vedic import *

    m = Moira()
    chart = m.chart(datetime(1985, 3, 21, 6, 0, tzinfo=timezone.utc))

    # Ayanamsa and sidereal positions
    ayan = ayanamsa(chart.jd, Ayanamsa.LAHIRI)
    naks = all_nakshatras_at(chart.jd, chart.longitudes())

    # Panchanga for the moment
    pg = panchanga_at(chart.jd, latitude=28.6, longitude=77.2)

    # Vedic dignities
    dignities = {b: vedic_dignity(lon) for b, lon in chart.longitudes().items()}

    # Vimshottari dasha
    periods = vimshottari(moon_lon=chart.longitudes()['Moon'], birth_jd=chart.jd)

    # Shadbala
    strength = shadbala(chart.jd, latitude=28.6, longitude=77.2)

Next step
---------
For transits, progressions, synastry, eclipses, and returns, use
``moira.predictive``.

For the complete surface, use ``moira.facade``.
"""

# ── Everything from essentials ───────────────────────────────────────────
from .essentials import *  # noqa: F401,F403
from .essentials import __all__ as _essentials_all

# ── Sidereal / Ayanamsa (full) ───────────────────────────────────────────
from .sidereal import (
    UserDefinedAyanamsa,
    NakshatraPosition,
    nakshatra_of,
    all_nakshatras_at,
)

# ── Panchanga ────────────────────────────────────────────────────────────
from .panchanga import (
    TithiPaksha,
    YogaClass,
    KaranaType,
    VaraLordType,
    PanchangaPolicy,
    TITHI_NAMES,
    YOGA_NAMES,
    KARANA_NAMES,
    VARA_LORDS,
    VARA_NAMES,
    PanchangaElement,
    PanchangaResult,
    TithiConditionProfile,
    PanchangaProfile,
    panchanga_at,
    tithi_condition_profile,
    panchanga_profile,
    validate_panchanga_output,
)

# ── Vedic Dignities ──────────────────────────────────────────────────────
from .vedic_dignities import (
    VedicDignityRank,
    CompoundRelationship,
    DignityTier,
    EXALTATION_SIGN,
    EXALTATION_DEGREE,
    DEBILITATION_SIGN,
    MULATRIKONA_SIGN,
    MULATRIKONA_START,
    MULATRIKONA_END,
    OWN_SIGNS,
    NATURAL_FRIENDS,
    NATURAL_NEUTRALS,
    NATURAL_ENEMIES,
    VedicDignityResult,
    PlanetaryRelationship,
    VedicDignityPolicy,
    DignityConditionProfile,
    ChartDignityProfile,
    vedic_dignity,
    planetary_relationships,
    dignity_condition_profile,
    chart_dignity_profile,
    validate_dignity_output,
)

# ── Varga (divisional charts) ────────────────────────────────────────────
from .varga import (
    VargaPoint,
    calculate_varga,
    navamsa,
    saptamsa,
    dashamansa,
    dwadashamsa,
    trimshamsa,
    hora,
    chaturthamsha,
    shashthamsha,
    ashtamsha,
    shodashamsha,
    vimshamsha,
    chaturvimshamsha,
    saptavimshamsha,
    khavedamsha,
    akshavedamsha,
    shashtiamsha,
)

# ── Vimshottari Dasha ────────────────────────────────────────────────────
from .dasha import (
    VIMSHOTTARI_YEARS,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_TOTAL,
    VIMSHOTTARI_YEAR_BASIS,
    VIMSHOTTARI_LEVEL_NAMES,
    DashaLordType,
    VimshottariYearPolicy,
    VimshottariAyanamsaPolicy,
    VimshottariComputationPolicy,
    DEFAULT_VIMSHOTTARI_POLICY,
    DashaPeriod,
    DashaActiveLine,
    DashaConditionProfile,
    DashaSequenceProfile,
    DashaLordPair,
    vimshottari,
    current_dasha,
    dasha_balance,
    dasha_active_line,
    dasha_condition_profile,
    dasha_sequence_profile,
    dasha_lord_pair,
    validate_vimshottari_output,
)

# ── Alternate Dasha Systems (Ashtottari, Yogini) ─────────────────────────
from .dasha_systems import (
    AlternateDashaSystem,
    ASHTOTTARI_YEARS,
    ASHTOTTARI_SEQUENCE,
    ASHTOTTARI_NAKSHATRA_LORD,
    ASHTOTTARI_TOTAL,
    YOGINI_YEARS,
    YOGINI_SEQUENCE,
    YOGINI_PLANETS,
    YOGINI_TOTAL,
    AlternateDashaPeriod,
    AshtottariPolicy,
    YoginiPolicy,
    AlternatePeriodProfile,
    AlternateDashaSequenceProfile,
    ashtottari,
    yogini_dasha,
    alternate_period_profile,
    alternate_sequence_profile,
    validate_alternate_dasha_output,
)

# ── Jaimini Karakas ──────────────────────────────────────────────────────
from .jaimini import (
    KarakaRole,
    KarakaPlanetType,
    JaiminiPolicy,
    KARAKA_NAMES_7,
    KARAKA_NAMES_8,
    KarakaAssignment,
    JaiminiKarakaResult,
    KarakaConditionProfile,
    JaiminiChartProfile,
    KarakaPair,
    jaimini_karakas,
    atmakaraka,
    karaka_condition_profile,
    jaimini_chart_profile,
    karaka_pair,
    validate_jaimini_output,
)

# ── Ashtakavarga ─────────────────────────────────────────────────────────
from .ashtakavarga import (
    RekhaTier,
    AshtakavargaPolicy,
    REKHA_TABLES,
    BhinnashtakavargaResult,
    AshtakavargaResult,
    SignStrengthProfile,
    AshtakavargaChartProfile,
    bhinnashtakavarga,
    ashtakavarga,
    transit_strength,
    sign_strength_profile,
    ashtakavarga_chart_profile,
    validate_ashtakavarga_output,
)

# ── Shadbala ─────────────────────────────────────────────────────────────
from .shadbala import (
    NAISARGIKA_BALA,
    REQUIRED_RUPAS,
    MEAN_DAILY_MOTION,
    ShadbalaTier,
    SthanaBala,
    KalaBala,
    PlanetShadbala,
    ShadbalaResult,
    ShadbalaPolicy,
    ShadbalaConditionProfile,
    ShadbalaChartProfile,
    sthana_bala,
    dig_bala,
    kala_bala,
    chesta_bala,
    drig_bala,
    shadbala,
    hora_lord_at,
    shadbala_condition_profile,
    shadbala_chart_profile,
    validate_shadbala_output,
)


# ── Build __all__ ────────────────────────────────────────────────────────

_VEDIC_OWN: list[str] = [
    # Sidereal (extended)
    "UserDefinedAyanamsa",
    "NakshatraPosition",
    "nakshatra_of",
    "all_nakshatras_at",
    # Panchanga
    "TithiPaksha",
    "YogaClass",
    "KaranaType",
    "VaraLordType",
    "PanchangaPolicy",
    "TITHI_NAMES",
    "YOGA_NAMES",
    "KARANA_NAMES",
    "VARA_LORDS",
    "VARA_NAMES",
    "PanchangaElement",
    "PanchangaResult",
    "TithiConditionProfile",
    "PanchangaProfile",
    "panchanga_at",
    "tithi_condition_profile",
    "panchanga_profile",
    "validate_panchanga_output",
    # Vedic dignities
    "VedicDignityRank",
    "CompoundRelationship",
    "DignityTier",
    "EXALTATION_SIGN",
    "EXALTATION_DEGREE",
    "DEBILITATION_SIGN",
    "MULATRIKONA_SIGN",
    "MULATRIKONA_START",
    "MULATRIKONA_END",
    "OWN_SIGNS",
    "NATURAL_FRIENDS",
    "NATURAL_NEUTRALS",
    "NATURAL_ENEMIES",
    "VedicDignityResult",
    "PlanetaryRelationship",
    "VedicDignityPolicy",
    "DignityConditionProfile",
    "ChartDignityProfile",
    "vedic_dignity",
    "planetary_relationships",
    "dignity_condition_profile",
    "chart_dignity_profile",
    "validate_dignity_output",
    # Varga
    "VargaPoint",
    "calculate_varga",
    "navamsa",
    "saptamsa",
    "dashamansa",
    "dwadashamsa",
    "trimshamsa",
    "hora",
    "chaturthamsha",
    "shashthamsha",
    "ashtamsha",
    "shodashamsha",
    "vimshamsha",
    "chaturvimshamsha",
    "saptavimshamsha",
    "khavedamsha",
    "akshavedamsha",
    "shashtiamsha",
    # Vimshottari Dasha
    "VIMSHOTTARI_YEARS",
    "VIMSHOTTARI_SEQUENCE",
    "VIMSHOTTARI_TOTAL",
    "VIMSHOTTARI_YEAR_BASIS",
    "VIMSHOTTARI_LEVEL_NAMES",
    "DashaLordType",
    "VimshottariYearPolicy",
    "VimshottariAyanamsaPolicy",
    "VimshottariComputationPolicy",
    "DEFAULT_VIMSHOTTARI_POLICY",
    "DashaPeriod",
    "DashaActiveLine",
    "DashaConditionProfile",
    "DashaSequenceProfile",
    "DashaLordPair",
    "vimshottari",
    "current_dasha",
    "dasha_balance",
    "dasha_active_line",
    "dasha_condition_profile",
    "dasha_sequence_profile",
    "dasha_lord_pair",
    "validate_vimshottari_output",
    # Alternate dasha systems
    "AlternateDashaSystem",
    "ASHTOTTARI_YEARS",
    "ASHTOTTARI_SEQUENCE",
    "ASHTOTTARI_NAKSHATRA_LORD",
    "ASHTOTTARI_TOTAL",
    "YOGINI_YEARS",
    "YOGINI_SEQUENCE",
    "YOGINI_PLANETS",
    "YOGINI_TOTAL",
    "AlternateDashaPeriod",
    "AshtottariPolicy",
    "YoginiPolicy",
    "AlternatePeriodProfile",
    "AlternateDashaSequenceProfile",
    "ashtottari",
    "yogini_dasha",
    "alternate_period_profile",
    "alternate_sequence_profile",
    "validate_alternate_dasha_output",
    # Jaimini
    "KarakaRole",
    "KarakaPlanetType",
    "JaiminiPolicy",
    "KARAKA_NAMES_7",
    "KARAKA_NAMES_8",
    "KarakaAssignment",
    "JaiminiKarakaResult",
    "KarakaConditionProfile",
    "JaiminiChartProfile",
    "KarakaPair",
    "jaimini_karakas",
    "atmakaraka",
    "karaka_condition_profile",
    "jaimini_chart_profile",
    "karaka_pair",
    "validate_jaimini_output",
    # Ashtakavarga
    "RekhaTier",
    "AshtakavargaPolicy",
    "REKHA_TABLES",
    "BhinnashtakavargaResult",
    "AshtakavargaResult",
    "SignStrengthProfile",
    "AshtakavargaChartProfile",
    "bhinnashtakavarga",
    "ashtakavarga",
    "transit_strength",
    "sign_strength_profile",
    "ashtakavarga_chart_profile",
    "validate_ashtakavarga_output",
    # Shadbala
    "NAISARGIKA_BALA",
    "REQUIRED_RUPAS",
    "MEAN_DAILY_MOTION",
    "ShadbalaTier",
    "SthanaBala",
    "KalaBala",
    "PlanetShadbala",
    "ShadbalaResult",
    "ShadbalaPolicy",
    "ShadbalaConditionProfile",
    "ShadbalaChartProfile",
    "sthana_bala",
    "dig_bala",
    "kala_bala",
    "chesta_bala",
    "drig_bala",
    "shadbala",
    "hora_lord_at",
    "shadbala_condition_profile",
    "shadbala_chart_profile",
    "validate_shadbala_output",
]

__all__ = list(_essentials_all) + _VEDIC_OWN
