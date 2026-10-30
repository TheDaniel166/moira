"""
Moira — Ayanamsa Doctrine
=========================

Archetype: Doctrine registry and textual ayanamsa families

Purpose
-------
States what kind of claim every ayanamsa makes, and computes the three
families the original texts support: the Grahalāghava formula, the
siddhantic polar star, and the trepidation reconstructions.

Governing record: ``wiki/02_standards/AYANAMSA_DOCTRINE_STANDARD.md``.
Research basis: ``wiki/05_research/fixed_stars/AYANAMSA_ANCHORS_IN_ORIGINAL_TEXTS.md``.

Boundary declaration
--------------------
Owns: the provenance records (``AyanamsaDoctrine``), the doctrinal system
      values (``GrahalaghavaAyanamsa``, ``PolarStarAyanamsa``,
      ``SuryaSiddhantaLibrationAyanamsa``, ``SuryadevaTrepidationAyanamsa``),
      their arithmetic, and the polar-longitude construction.
Delegates: nutation and obliquity to ``moira.obliquity``; star positions to
           ``moira.stars``; truth assembly to ``moira.sidereal``.

Import-time side effects: None
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Union

from .obliquity import mean_obliquity, nutation, true_obliquity

__all__ = [
    "TextualAttestation",
    "AyanamsaDoctrine",
    "GrahalaghavaAyanamsa",
    "PolarStarAyanamsa",
    "SuryaSiddhantaLibrationAyanamsa",
    "SuryadevaTrepidationAyanamsa",
    "DoctrinalAyanamsa",
    "POLAR_STAR_CATALOGUE",
    "ayanamsa_doctrine",
    "grahalaghava_ayanamsa_for_saka_year",
    "polar_longitude",
    "siddhantic_polar_to_ecliptic",
]

# Families and layers (AYANAMSA_DOCTRINE_STANDARD.md, Section 2.1).
FAMILY_EPOCH_POLYNOMIAL = "epoch_polynomial"
FAMILY_STAR_ANCHORED_ECLIPTIC = "star_anchored_ecliptic"
FAMILY_TEXTUAL_FORMULA = "textual_formula"
FAMILY_POLAR_STAR = "polar_star"
FAMILY_TREPIDATION = "trepidation_reconstruction"
FAMILY_USER_DEFINED = "user_defined"

LAYER_MODERN_CONVENTION = "modern_convention"
LAYER_VERSE = "verse"
LAYER_COMMENTARY = "commentary"
LAYER_RECONSTRUCTION = "reconstruction"
LAYER_USER_SUPPLIED = "user_supplied"

_J2000 = 2451545.0
# Midnight 17/18 February 3102 BCE (proleptic Julian): the start of the Kali age.
_KALI_EPOCH_JD = 588465.5
# Civil days per Mahāyuga (4,320,000 years): Sūrya Siddhānta and Āryabhaṭa.
_SURYA_SIDDHANTA_MAHAYUGA_DAYS = 1_577_917_828
_ARYABHATA_MAHAYUGA_DAYS = 1_577_917_500
_MAHAYUGA_YEARS = 4_320_000
# Geometric mean longitude of the Sun, mean equinox of date (Meeus,
# Astronomical Algorithms, 2nd ed., eq. 25.2); also used by moira.coordinates.
_MEAN_SUN_L0_DEG = 280.46646
_MEAN_SUN_RATE_DEG_PER_DAY = 36000.76983 / 36525.0
_TROPICAL_YEAR_DAYS = 365.2422
# Approximate March equinox 2000 (JD), only to seed the year-boundary search.
_EQUINOX_2000_JD = 2451623.8


def _finite(name: str, value: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric and finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


def _dms(value_deg: float) -> str:
    sign = "-" if value_deg < 0 else ""
    minutes = round(abs(value_deg) * 60.0)
    return f"{sign}{minutes // 60}°{minutes % 60:02d}′" if minutes % 60 else f"{sign}{minutes // 60}°"


# ---------------------------------------------------------------------------
# Provenance records
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TextualAttestation:
    """One source's value for an anchor star, in that source's own coordinate."""

    source: str
    date: str
    value_deg: float
    coordinate: str
    latitude_deg: float | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class AyanamsaDoctrine:
    """What one ayanamsa holds fixed, which layer of the tradition it belongs
    to, and which texts support its anchor value."""

    system: str
    family: str
    layer: str
    definition: str
    anchor_star: str | None = None
    anchor_identification: str | None = None
    anchor_target_deg: float | None = None
    anchor_coordinate: str | None = None
    anchor_product: str | None = None
    identification_certainty: str | None = None
    attestations: tuple[TextualAttestation, ...] = ()
    zero_epoch: str | None = None
    sources: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()


_PM_1989 = (
    "Pingree & Morrissey, 'On the identification of the yogatārās of the "
    "Indian nakṣatras', JHA 20 (1989) 99–119"
)
_SS = "Sūrya Siddhānta viii.1–9 (Burgess 1860; Yano e-text; RSS ed. with Raṅganātha)"
_GL = "Gaṇeśa, Grahalāghava (1520) 11.2–3 (Jośī ed.; Rao & Uma)"
_TABLE_21 = "via Pingree & Morrissey 1989, Table 21"


def _att(source: str, date: str, value: float, coordinate: str = "polar",
         latitude: float | None = None, note: str | None = None) -> TextualAttestation:
    return TextualAttestation(source, date, value, coordinate, latitude, note)


_ATTESTATIONS: dict[str, tuple[TextualAttestation, ...]] = {
    "chitra": (
        _att("Paitāmaha Siddhānta", "c. 425", 183.0, note=_TABLE_21),
        _att("Varāhamihira, Pañcasiddhāntikā XIV.37", "c. 505", 181.0 + 50.0 / 60.0,
             "tropical_ecliptic", -(2.0 + 42.0 / 60.0),
             "Neugebauer & Pingree's reading; Thibaut reads 180°50′"),
        _att("Brahmagupta, Brāhmasphuṭasiddhānta", "628", 183.0, note=_TABLE_21),
        _att("Sūrya Siddhānta", "c. 800", 180.0, latitude=-2.0,
             note="ecliptic 180°49′ with the text's 24° obliquity"),
        _att("Vaṭeśvara", "904", 183.0, note=_TABLE_21),
        _att("Gaṇeśa, Grahalāghava", "1520", 183.0, latitude=-2.0),
    ),
    "revati": (
        _att("Paitāmaha Siddhānta", "c. 425", 0.0, note=_TABLE_21),
        _att("Brahmagupta, Brāhmasphuṭasiddhānta", "628", 0.0, note=_TABLE_21),
        _att("Sūrya Siddhānta", "c. 800", 359.0 + 50.0 / 60.0, latitude=0.0,
             note="10′ before the zero point, the end of the Revatī segment"),
        _att("Vaṭeśvara", "904", 0.0, note=_TABLE_21),
        _att("Gaṇeśa, Grahalāghava", "1520", 0.0, latitude=0.0),
    ),
    "pushya": (
        _att("Paitāmaha Siddhānta", "c. 425", 106.0, latitude=0.0, note=_TABLE_21),
        _att("Brahmagupta, Brāhmasphuṭasiddhānta", "628", 106.0, latitude=0.0, note=_TABLE_21),
        _att("Sūrya Siddhānta", "c. 800", 106.0, latitude=0.0),
        _att("Vaṭeśvara", "904", 106.0, latitude=0.0, note=_TABLE_21),
        _att("Gaṇeśa, Grahalāghava", "1520", 106.0, latitude=0.0),
    ),
    "mula": (
        _att("Paitāmaha Siddhānta", "c. 425", 240.0 + 4.0 / 60.0,
             note=_TABLE_21 + "; fits 45 Oph better than λ Sco"),
        _att("Brahmagupta, Brāhmasphuṭasiddhānta", "628", 241.0, note=_TABLE_21),
        _att("Sūrya Siddhānta", "c. 800", 241.0, latitude=-9.0,
             note="ecliptic 242°55′ with the text's 24° obliquity"),
        _att("Vaṭeśvara", "904", 241.0, note=_TABLE_21),
        _att("Gaṇeśa, Grahalāghava", "1520", 242.0, latitude=-8.0),
    ),
    "ashvini": (
        _att("Sūrya Siddhānta", "c. 800", 8.0, latitude=10.0),
        _att("Gaṇeśa, Grahalāghava", "1520", 8.0, latitude=10.0),
    ),
}

# Catalog name, identification, certainty (Pingree & Morrissey 1989, Tables 5, 7–8).
_YOGATARA: dict[str, tuple[str, str, str]] = {
    "ashvini": ("Sheratan", "β Arietis", "beyond_doubt"),
    "pushya": ("Asellus Australis", "δ Cancri", "beyond_doubt"),
    "chitra": ("Spica", "α Virginis", "in_doubt"),
    "mula": ("Shaula", "λ Scorpii", "in_doubt"),
    "revati": ("Revati", "ζ Piscium", "beyond_doubt"),
}

_POLYNOMIAL_SOURCES: dict[str, tuple[str, str]] = {
    "Lahiri": (
        "Calendar Reform Committee report, Government of India (1955)",
        "The national ayanamsa adopted from N. C. Lahiri's Spica-based "
        "(Chitrapaksha) value; Moira propagates its J2000 mean value by "
        "IAU 2006 general precession.",
    ),
    "Fagan-Bradley": (
        "Fagan & Bradley, Primer of Sidereal Astrology (1967)",
        "The Western sidereal zodiac of Fagan and Bradley, defined by an epoch value.",
    ),
    "Krishnamurti": (
        "K. S. Krishnamurti, KP ayanamsa tables",
        "The Krishnamurti Paddhati ayanamsa, defined by an epoch value.",
    ),
    "Raman": (
        "B. V. Raman, sidereal ephemeris tables",
        "B. V. Raman's ayanamsa, defined by an epoch value.",
    ),
    "Yukteshwar": (
        "Sri Yukteswar, The Holy Science (1894)",
        "Sri Yukteswar's ayanamsa lineage, defined by an epoch value.",
    ),
    "Djwhal Khul": (
        "Alice A. Bailey / Djwhal Khul theosophical tradition",
        "The theosophical sidereal value, defined by an epoch value.",
    ),
    "De Luce": (
        "Cyril Fagan, Zodiacs Old and New (1951), De Luce variant",
        "Robert De Luce's ayanamsa, defined by an epoch value.",
    ),
}

_STAR_CONVENTIONS: dict[str, tuple[str, float, str, tuple[str, ...], tuple[str, ...]]] = {
    "True Chitrapaksha": (
        "chitra", 180.0, "Spica held at ecliptic longitude 180° of date.",
        (_PM_1989, _SS, _GL),
        (
            "A modern ecliptic convention. 180° is the Sūrya Siddhānta's polar "
            "value, which is ecliptic 180°49′; the other catalogues give 183°.",
            "Pingree & Morrissey hold Citrā = α Vir in doubt (76 Vir is the "
            "alternative); it fits within 1° only for a base year of 500.",
        ),
    ),
    "True Revati": (
        "revati", 359.0 + 50.0 / 60.0, "ζ Piscium held at ecliptic longitude 359°50′ of date.",
        (_PM_1989, _SS, _GL),
        (
            "359°50′ is the Sūrya Siddhānta's value alone; the other "
            "catalogues put the star at 0°. The texts' zero is the end of the "
            "Revatī segment, not the star.",
            "ζ Psc is dim (V 5.2); Pingree & Morrissey accept it but call its "
            "faintness and its nearly 2° offset disturbing.",
        ),
    ),
    "True Pushya": (
        "pushya", 106.0, "δ Cancri held at ecliptic longitude 106° of date.",
        (_PM_1989, _SS, _GL),
        (
            "The only anchor value every sidereal catalogue agrees on; at "
            "latitude 0 its polar and ecliptic longitudes coincide.",
            "The Pañcasiddhāntikā's Puṣya near 97° is μ Cnc in a tropical list "
            "and does not bear on this anchor.",
        ),
    ),
    "True Mula": (
        "mula", 240.0, "λ Scorpii held at ecliptic longitude 240° of date (Chandra Hari's Mula-paksha).",
        ("Chandra Hari, Mula-paksha ayanamsa", _PM_1989, _SS, _GL),
        (
            "240° matches no catalogue exactly: the Paitāmaha gives 240°04′, "
            "Brahmagupta and the Sūrya Siddhānta 241°, the Grahalāghava 242°.",
            "Pingree & Morrissey hold Mūla = λ Sco in doubt (45 Oph is the "
            "alternative).",
        ),
    ),
}


def _named_doctrine(system: str) -> AyanamsaDoctrine:
    from .sidereal import _APPARENT_VARIANTS, _AYANAMSA_AT_J2000, _STAR_ANCHORED

    if system not in _AYANAMSA_AT_J2000:
        raise ValueError(f"Unknown ayanamsa system {system!r}")
    base = _APPARENT_VARIANTS.get(system, system)
    product = "apparent" if system in _APPARENT_VARIANTS else "astrometric"
    if base in _POLYNOMIAL_SOURCES:
        source, definition = _POLYNOMIAL_SOURCES[base]
        return AyanamsaDoctrine(
            system=system,
            family=FAMILY_EPOCH_POLYNOMIAL,
            layer=LAYER_MODERN_CONVENTION,
            definition=definition,
            sources=(source,),
            caveats=("Defined by an epoch value carried by precession; no star "
                     "is held fixed.",),
        )
    star_name, target = _STAR_ANCHORED[base]
    suffix = (" The anchor is the apparent star, computed like the planets."
              if product == "apparent" else
              " The anchor is the astrometric star: a smooth frame without the "
              "yearly aberration swing.")
    if base == "Aldebaran (15 Tau)":
        return AyanamsaDoctrine(
            system=system,
            family=FAMILY_STAR_ANCHORED_ECLIPTIC,
            layer=LAYER_MODERN_CONVENTION,
            definition="Aldebaran held at ecliptic longitude 45° (15° Taurus) of date." + suffix,
            anchor_star=star_name,
            anchor_identification="α Tauri",
            anchor_target_deg=target,
            anchor_coordinate="ecliptic",
            anchor_product=product,
            identification_certainty="conventional",
            sources=("Western sidereal convention",),
            caveats=("Not studied against the Indian texts.",),
        )
    nakshatra, _, definition, sources, caveats = _STAR_CONVENTIONS[base]
    catalog, identification, certainty = _YOGATARA[nakshatra]
    return AyanamsaDoctrine(
        system=system,
        family=FAMILY_STAR_ANCHORED_ECLIPTIC,
        layer=LAYER_MODERN_CONVENTION,
        definition=definition + suffix,
        anchor_star=star_name,
        anchor_identification=identification,
        anchor_target_deg=target,
        anchor_coordinate="ecliptic",
        anchor_product=product,
        identification_certainty=certainty,
        attestations=_ATTESTATIONS[nakshatra],
        sources=sources,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Doctrinal system values
# ---------------------------------------------------------------------------

_YEAR_CONVENTIONS = ("current", "elapsed")
_STEPPINGS = ("annual", "continuous")


@dataclass(frozen=True, slots=True)
class GrahalaghavaAyanamsa:
    """Gaṇeśa's formula, Grahalāghava 2.7: ayanamsa = (Śaka − 444) / 60°.

    ``year_convention``: ``"current"`` (default; Mallāri's *vartamāna*) numbers
    the year beginning in the spring of CE year Y as Y − 77; ``"elapsed"`` as
    Y − 78. ``stepping``: ``"annual"`` (default) holds one value per year, as
    the text does; ``"continuous"`` interpolates between year boundaries.
    """

    year_convention: str = "current"
    stepping: str = "annual"

    def __post_init__(self) -> None:
        if self.year_convention not in _YEAR_CONVENTIONS:
            raise ValueError(f"year_convention must be one of {_YEAR_CONVENTIONS}, got {self.year_convention!r}")
        if self.stepping not in _STEPPINGS:
            raise ValueError(f"stepping must be one of {_STEPPINGS}, got {self.stepping!r}")

    @property
    def name(self) -> str:
        return f"Grahalaghava ({self.year_convention} year, {self.stepping})"


_POLAR_SOURCES = ("surya_siddhanta", "grahalaghava")
_STAR_PRODUCTS = ("astrometric", "apparent")

# Polar longitude (dhruvaka) and polar latitude (vikṣepa), degrees, as read in
# the original texts (AYANAMSA_ANCHORS_IN_ORIGINAL_TEXTS.md).
POLAR_STAR_CATALOGUE: dict[str, dict[str, tuple[float, float]]] = {
    "surya_siddhanta": {
        "ashvini": (8.0, 10.0),
        "pushya": (106.0, 0.0),
        "chitra": (180.0, -2.0),
        "mula": (241.0, -9.0),
        "revati": (359.0 + 50.0 / 60.0, 0.0),
    },
    "grahalaghava": {
        "ashvini": (8.0, 10.0),
        "pushya": (106.0, 0.0),
        "chitra": (183.0, -2.0),
        "mula": (242.0, -8.0),
        "revati": (0.0, 0.0),
    },
}

_SOURCE_TITLES = {"surya_siddhanta": "Surya Siddhanta", "grahalaghava": "Grahalaghava"}


@dataclass(frozen=True, slots=True)
class PolarStarAyanamsa:
    """A junction star held at its textual polar longitude of date.

    ``source`` is ``"surya_siddhanta"`` or ``"grahalaghava"``; ``nakshatra``
    one of ``ashvini``, ``pushya``, ``chitra``, ``mula``, ``revati``.
    ``star_product`` is ``"astrometric"`` (default) or ``"apparent"``.
    """

    source: str
    nakshatra: str
    star_product: str = "astrometric"

    def __post_init__(self) -> None:
        if self.source not in _POLAR_SOURCES:
            raise ValueError(f"source must be one of {_POLAR_SOURCES}, got {self.source!r}")
        if self.nakshatra not in POLAR_STAR_CATALOGUE[self.source]:
            raise ValueError(
                f"nakshatra must be one of {tuple(POLAR_STAR_CATALOGUE[self.source])}, got {self.nakshatra!r}"
            )
        if self.star_product not in _STAR_PRODUCTS:
            raise ValueError(f"star_product must be one of {_STAR_PRODUCTS}, got {self.star_product!r}")

    @property
    def target_deg(self) -> float:
        return POLAR_STAR_CATALOGUE[self.source][self.nakshatra][0]

    @property
    def star(self) -> str:
        return _YOGATARA[self.nakshatra][0]

    @property
    def name(self) -> str:
        product = ", apparent" if self.star_product == "apparent" else ""
        return (f"{_SOURCE_TITLES[self.source]} polar "
                f"({self.nakshatra.capitalize()} {_dms(self.target_deg)}{product})")


_LIBRATION_READINGS = (600, 30)


@dataclass(frozen=True, slots=True)
class SuryaSiddhantaLibrationAyanamsa:
    """The Sūrya Siddhānta iii.9–10 libration, a reconstruction.

    ``cycles_per_mahayuga`` is 600 (Raṅganātha's reading; default) or 30 (the
    reading Bhāskara II reports). The doḥ of the phase times 3/10 gives at most
    27°; negative in the first half-cycle, positive in the second.
    """

    cycles_per_mahayuga: int = 600

    def __post_init__(self) -> None:
        if self.cycles_per_mahayuga not in _LIBRATION_READINGS:
            raise ValueError(
                f"cycles_per_mahayuga must be one of {_LIBRATION_READINGS}, got {self.cycles_per_mahayuga!r}"
            )

    @property
    def name(self) -> str:
        return f"Surya Siddhanta libration ({self.cycles_per_mahayuga} per mahayuga)"


@dataclass(frozen=True, slots=True)
class SuryadevaTrepidationAyanamsa:
    """The ±24° rule quoted by Sūryadeva Yajvan (born 1191) from unnamed
    authors: a 5,808-year oscillation, zero at Kali 3600 (499 CE). Not in the
    Āryabhaṭīya; never attributed to Āryabhaṭa."""

    @property
    def name(self) -> str:
        return "Suryadeva trepidation (±24°)"


DoctrinalAyanamsa = Union[
    GrahalaghavaAyanamsa,
    PolarStarAyanamsa,
    SuryaSiddhantaLibrationAyanamsa,
    SuryadevaTrepidationAyanamsa,
]
DOCTRINAL_TYPES = (
    GrahalaghavaAyanamsa,
    PolarStarAyanamsa,
    SuryaSiddhantaLibrationAyanamsa,
    SuryadevaTrepidationAyanamsa,
)


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

def grahalaghava_ayanamsa_for_saka_year(saka_year: int) -> float:
    """Return Grahalāghava 2.7 for one Śaka year number: (Śaka − 444) / 60°."""
    if isinstance(saka_year, bool) or not isinstance(saka_year, int):
        raise ValueError(f"saka_year must be an integer, got {saka_year!r}")
    return (saka_year - 444) / 60.0


def _grahalaghava_saka_number(ce_year: int, year_convention: str) -> int:
    return ce_year - 77 if year_convention == "current" else ce_year - 78


def _grahalaghava_year_boundary(ce_year: int, year_convention: str) -> float:
    """JD (TT) when the mean tropical Sun reaches the year's own ayanamsa."""
    value = grahalaghava_ayanamsa_for_saka_year(_grahalaghava_saka_number(ce_year, year_convention))
    seed = _EQUINOX_2000_JD + (ce_year - 2000) * _TROPICAL_YEAR_DAYS
    seed_longitude = _MEAN_SUN_L0_DEG + _MEAN_SUN_RATE_DEG_PER_DAY * (seed - _J2000)
    turns = round((seed_longitude - value) / 360.0)
    target = value + 360.0 * turns
    return _J2000 + (target - _MEAN_SUN_L0_DEG) / _MEAN_SUN_RATE_DEG_PER_DAY


def _grahalaghava(jd_tt: float, system: GrahalaghavaAyanamsa) -> tuple[float, tuple]:
    year = int(math.floor((jd_tt - _EQUINOX_2000_JD) / _TROPICAL_YEAR_DAYS)) + 2000
    while _grahalaghava_year_boundary(year, system.year_convention) > jd_tt:
        year -= 1
    while _grahalaghava_year_boundary(year + 1, system.year_convention) <= jd_tt:
        year += 1
    start = _grahalaghava_year_boundary(year, system.year_convention)
    end = _grahalaghava_year_boundary(year + 1, system.year_convention)
    saka = _grahalaghava_saka_number(year, system.year_convention)
    value = grahalaghava_ayanamsa_for_saka_year(saka)
    if system.stepping == "continuous":
        value += (jd_tt - start) / (end - start) / 60.0
    terms = (
        ("year_convention", system.year_convention),
        ("stepping", system.stepping),
        ("saka_year", saka),
        ("year_start_jd_tt", start),
        ("next_year_start_jd_tt", end),
        ("year_boundary", "mean_sun_reaches_year_ayanamsa"),
    )
    return value, terms


def polar_longitude(ecliptic_longitude_deg: float, ecliptic_latitude_deg: float,
                    obliquity_deg: float) -> float:
    """Return the polar longitude (dhruvaka) of a point, degrees in [0, 360).

    The polar longitude is the ecliptic longitude of the point where the
    star's hour circle meets the ecliptic. Equating the right ascension of
    that ecliptic point, ``tan α = tan λp cos ε``, with the star's,
    ``tan α = (sin λ cos ε − tan β sin ε) / cos λ``, gives
    ``λp = atan2(sin λ cos ε − tan β sin ε, cos λ cos ε)``.
    """
    lam = math.radians(_finite("ecliptic_longitude_deg", ecliptic_longitude_deg))
    beta = math.radians(_finite("ecliptic_latitude_deg", ecliptic_latitude_deg))
    eps = math.radians(_finite("obliquity_deg", obliquity_deg))
    if abs(beta) >= math.pi / 2.0:
        raise ValueError("ecliptic_latitude_deg must lie strictly between -90 and 90")
    y = math.sin(lam) * math.cos(eps) - math.tan(beta) * math.sin(eps)
    x = math.cos(lam) * math.cos(eps)
    return math.degrees(math.atan2(y, x)) % 360.0


def siddhantic_polar_to_ecliptic(dhruvaka_deg: float, vikshepa_deg: float,
                                 obliquity_deg: float = 24.0) -> tuple[float, float]:
    """Reduce a catalogue entry from polar to ecliptic coordinates.

    The star lies on the hour circle through the ecliptic point at longitude
    ``dhruvaka``, ``vikshepa`` degrees from that point toward the pole
    (Raṅganātha on Sūrya Siddhānta viii.12). The default obliquity is the
    texts' own 24°. Returns ecliptic (longitude, latitude) in degrees.
    """
    lam_p = math.radians(_finite("dhruvaka_deg", dhruvaka_deg))
    v = math.radians(_finite("vikshepa_deg", vikshepa_deg))
    eps = math.radians(_finite("obliquity_deg", obliquity_deg))
    alpha = math.atan2(math.sin(lam_p) * math.cos(eps), math.cos(lam_p))
    delta = math.asin(math.sin(eps) * math.sin(lam_p)) + v
    if abs(delta) >= math.pi / 2.0:
        raise ValueError("the reduced declination passes the pole")
    sin_beta = (math.sin(delta) * math.cos(eps)
                - math.cos(delta) * math.sin(eps) * math.sin(alpha))
    y = math.sin(alpha) * math.cos(eps) + math.tan(delta) * math.sin(eps)
    lon = math.degrees(math.atan2(y, math.cos(alpha))) % 360.0
    return lon, math.degrees(math.asin(sin_beta))


def _bhuja(phase_deg: float) -> float:
    if phase_deg <= 90.0:
        return phase_deg
    if phase_deg <= 180.0:
        return 180.0 - phase_deg
    if phase_deg <= 270.0:
        return phase_deg - 180.0
    return 360.0 - phase_deg


def _surya_siddhanta_libration(jd_tt: float, system: SuryaSiddhantaLibrationAyanamsa) -> tuple[float, tuple]:
    days = jd_tt - _KALI_EPOCH_JD
    revolutions = system.cycles_per_mahayuga * days / _SURYA_SIDDHANTA_MAHAYUGA_DAYS
    phase = (revolutions % 1.0) * 360.0
    bhuja = _bhuja(phase)
    sign = -1.0 if phase < 180.0 else 1.0
    value = sign * bhuja * 3.0 / 10.0
    terms = (
        ("cycles_per_mahayuga", system.cycles_per_mahayuga),
        ("kali_epoch_jd", _KALI_EPOCH_JD),
        ("days_since_kali", days),
        ("phase_deg", phase),
        ("bhuja_deg", bhuja),
        ("sign_convention", "negative_first_half_cycle"),
    )
    return value, terms


def _suryadeva_trepidation(jd_tt: float) -> tuple[float, tuple]:
    days = jd_tt - _KALI_EPOCH_JD
    kali_years = days * _MAHAYUGA_YEARS / _ARYABHATA_MAHAYUGA_DAYS
    x = (kali_years - 3600.0) % 5808.0
    if x <= 1452.0:
        bhuja_years, sign = x, 1.0
    elif x <= 2904.0:
        bhuja_years, sign = 2904.0 - x, 1.0
    elif x <= 4356.0:
        bhuja_years, sign = x - 2904.0, -1.0
    else:
        bhuja_years, sign = 5808.0 - x, -1.0
    value = sign * bhuja_years * 2.0 / 121.0
    terms = (
        ("kali_epoch_jd", _KALI_EPOCH_JD),
        ("kali_years", kali_years),
        ("cycle_years", x),
        ("bhuja_years", bhuja_years),
        ("sign_convention", "positive_first_half_cycle"),
    )
    return value, terms


@dataclass(frozen=True, slots=True)
class _DoctrinalResolution:
    """One doctrinal ayanamsa resolved at TT, before truth assembly."""

    value_deg: float
    effective_path: str
    terms: tuple
    nutation_longitude_deg: float | None = None
    anchor_star: str | None = None
    anchor_target_deg: float | None = None
    anchor_tropical_longitude_deg: float | None = None
    anchor_source_mode: str | None = None
    anchor_product: str | None = None


def _polar_star(jd_tt: float, system: PolarStarAyanamsa, mode: str) -> _DoctrinalResolution:
    from .stars import star_at

    star = star_at(system.star, jd_tt, product=system.star_product)
    if mode == "true":
        longitude = star.longitude
        obliquity = true_obliquity(jd_tt)
        obliquity_model = "true_of_date"
    else:
        # True and mean ecliptics of date share one plane: only the equinox
        # moves, by Δψ along the ecliptic.
        longitude = star.longitude - nutation(jd_tt)[0]
        obliquity = mean_obliquity(jd_tt)
        obliquity_model = "mean_of_date"
    polar = polar_longitude(longitude, star.latitude, obliquity)
    value = (polar - system.target_deg) % 360.0
    star_truth = star.computation_truth
    return _DoctrinalResolution(
        value_deg=value,
        effective_path="live_star_polar_anchor",
        terms=(
            ("source", system.source),
            ("nakshatra", system.nakshatra),
            ("star_identification", _YOGATARA[system.nakshatra][1]),
            ("target_polar_longitude_deg", system.target_deg),
            ("star_ecliptic_longitude_deg", longitude),
            ("star_ecliptic_latitude_deg", star.latitude),
            ("star_polar_longitude_deg", polar),
            ("obliquity_deg", obliquity),
            ("obliquity_model", obliquity_model),
        ),
        anchor_star=system.star,
        anchor_target_deg=system.target_deg,
        anchor_tropical_longitude_deg=star.longitude,
        anchor_source_mode=star_truth.source_mode if star_truth is not None else star.source,
        anchor_product=system.star_product,
    )


def _resolve_doctrinal(jd_tt: float, system: DoctrinalAyanamsa, mode: str) -> _DoctrinalResolution:
    """Resolve a doctrinal ayanamsa at TT. Formula families add Δψ in true mode."""
    if isinstance(system, PolarStarAyanamsa):
        return _polar_star(jd_tt, system, mode)
    if isinstance(system, GrahalaghavaAyanamsa):
        value, terms = _grahalaghava(jd_tt, system)
        path = "grahalaghava_formula"
    elif isinstance(system, SuryaSiddhantaLibrationAyanamsa):
        value, terms = _surya_siddhanta_libration(jd_tt, system)
        path = "surya_siddhanta_libration"
    elif isinstance(system, SuryadevaTrepidationAyanamsa):
        value, terms = _suryadeva_trepidation(jd_tt)
        path = "suryadeva_trepidation"
    else:
        raise TypeError(f"not a doctrinal ayanamsa: {system!r}")
    dpsi = None
    if mode == "true":
        dpsi = nutation(jd_tt)[0]
        value += dpsi
        path += "_plus_nutation"
    return _DoctrinalResolution(value_deg=value, effective_path=path, terms=terms,
                                nutation_longitude_deg=dpsi)


# ---------------------------------------------------------------------------
# Doctrine lookup
# ---------------------------------------------------------------------------

def _doctrinal_doctrine(system: DoctrinalAyanamsa) -> AyanamsaDoctrine:
    if isinstance(system, GrahalaghavaAyanamsa):
        return AyanamsaDoctrine(
            system=system.name,
            family=FAMILY_TEXTUAL_FORMULA,
            layer=LAYER_VERSE,
            definition="Ayanamsa = (Śaka − 444) / 60 degrees: zero in Śaka 444 (522 CE), "
                       "1′ a year, no star.",
            zero_epoch="Śaka 444 (522 CE)",
            sources=("Gaṇeśa, Grahalāghava (1520) 2.7 (Jośī ed.)",
                     "Mallāri's commentary (current-year gloss)"),
            caveats=(
                "The verse takes a year number; the year boundary (the mean "
                "Sun reaching the year's ayanamsa) is Moira's reconstruction.",
                "It runs about 9.8″ a year faster than true precession; modern "
                "pañcāṅgas abandoned it.",
            ),
        )
    if isinstance(system, PolarStarAyanamsa):
        catalog, identification, certainty = _YOGATARA[system.nakshatra]
        source = _SS if system.source == "surya_siddhanta" else _GL
        return AyanamsaDoctrine(
            system=system.name,
            family=FAMILY_POLAR_STAR,
            layer=LAYER_COMMENTARY,
            definition=(f"{identification} held at polar longitude "
                        f"{_dms(system.target_deg)} of date: the ecliptic point "
                        "on the star's hour circle."),
            anchor_star=catalog,
            anchor_identification=identification,
            anchor_target_deg=system.target_deg,
            anchor_coordinate="polar",
            anchor_product=system.star_product,
            identification_certainty=certainty,
            attestations=_ATTESTATIONS[system.nakshatra],
            sources=(source, "Raṅganātha (1603) on Sūrya Siddhānta viii.12", _PM_1989),
            caveats=(
                "The value is textual; holding it for every date follows "
                "Raṅganātha's instruction to re-observe the stars in other periods.",
                "A different ayanamsa from the True modes, which hold an "
                "ecliptic longitude.",
            ),
        )
    if isinstance(system, SuryaSiddhantaLibrationAyanamsa):
        return AyanamsaDoctrine(
            system=system.name,
            family=FAMILY_TREPIDATION,
            layer=LAYER_RECONSTRUCTION,
            definition="Sūrya Siddhānta iii.9–10: the doḥ of the libration phase "
                       "times 3/10, at most 27°.",
            zero_epoch="Kali 3600 (499 CE) and every 3,600 years",
            sources=("Sūrya Siddhānta iii.9–12 (Burgess 1860, p. 243–245)",
                     "Parameśvara (1432) and Raṅganātha (1603), libration reading"),
            caveats=(
                "The libration is the commentators' reading of the verse; "
                "Bhāskara II reports 30 cycles, not 600.",
                "Sign and phase are fixed by Burgess's worked value for 1 January 1860.",
            ),
        )
    if isinstance(system, SuryadevaTrepidationAyanamsa):
        return AyanamsaDoctrine(
            system=system.name,
            family=FAMILY_TREPIDATION,
            layer=LAYER_COMMENTARY,
            definition="A ±24° oscillation with a 5,808-year period, zero at Kali 3600.",
            zero_epoch="Kali 3600 (499 CE)",
            sources=("Sūryadeva Yajvan, Prakāśikā on Āryabhaṭīya III.10 "
                     "(Shukla & Sarma 1976; Kern 1874, p. 59)",),
            caveats=("Quoted from unnamed authors; not in the Āryabhaṭīya and "
                     "not Āryabhaṭa's rule.",),
        )
    raise TypeError(f"not a doctrinal ayanamsa: {system!r}")


def ayanamsa_doctrine(system: object) -> AyanamsaDoctrine:
    """Return the provenance record for a named system or a typed ayanamsa."""
    if isinstance(system, DOCTRINAL_TYPES):
        return _doctrinal_doctrine(system)
    from .sidereal import UserDefinedAyanamsa

    if isinstance(system, UserDefinedAyanamsa):
        return AyanamsaDoctrine(
            system="UserDefinedAyanamsa",
            family=FAMILY_USER_DEFINED,
            layer=LAYER_USER_SUPPLIED,
            definition="A caller-supplied J2000 reference value carried by precession.",
        )
    if not isinstance(system, str):
        raise ValueError(f"Unknown ayanamsa system {system!r}")
    return _named_doctrine(system)
