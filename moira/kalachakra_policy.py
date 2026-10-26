"""Santhanam/BPHS Kalachakra catalogue; source corrections are public doctrine."""
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType

PROFILE_ID = "bphs_santhanam_longitude_row_cycle_v1"
VERSION = "ved014.1"
RAO_PROFILE_ID = "rao_2000_longitude_continuous_v1"
RAO_VERSION = "ved014.rao2000.1"
CATALOGUE_VERSION = "ved014.2"
PROFILE_IDS = (PROFILE_ID, RAO_PROFILE_ID)
SIGNS = ("Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi")
RULERS = ("Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter")
WEIGHTS = (7, 16, 9, 21, 5, 9, 16, 7, 10, 4, 4, 10)
GROUPS = MappingProxyType({
    "S1": (1,3,7,9,13,15,19,21,25,27), "S2": (2,8,14,20,26),
    "A1": (4,10,16,22), "A2": (5,6,11,12,17,18,23,24),
})
# Reconciled L01 printed 539-540, with explicit KC-01 through KC-04 decisions.
ROWS = MappingProxyType({
    "S1/1": (0,1,2,3,4,5,6,7,8), "S1/2": (9,10,11,7,6,5,3,4,2),
    "S1/3": (1,0,11,10,9,8,0,1,2), "S1/4": (3,4,5,6,7,8,9,10,11),
    "S2/1": (7,6,5,3,4,2,1,0,11), "S2/2": (10,9,8,0,1,2,3,4,5),
    "S2/3": (6,7,8,9,10,11,7,6,5), "S2/4": (3,4,2,1,0,11,10,9,8),
    "A1/1": (8,9,10,11,0,1,2,4,3), "A1/2": (5,6,7,11,10,9,8,7,6),
    "A1/3": (5,4,3,2,1,0,8,9,10), "A1/4": (11,0,1,2,4,3,5,6,7),
    "A2/1": (11,10,9,8,7,6,5,4,3), "A2/2": (2,1,0,8,9,10,11,0,1),
    "A2/3": (2,4,3,5,6,7,11,10,9), "A2/4": (8,7,6,5,4,3,2,1,0),
})
CLOCKS = MappingProxyType({"savana_360": Fraction(360), "julian_365.25": Fraction(1461,4)})


@dataclass(frozen=True, slots=True)
class KalachakraSource:
    """Edition-specific witness and inspected coordinates."""
    source_id: str
    title: str
    sha256: str
    coordinates: str


@dataclass(frozen=True, slots=True)
class KalachakraRule:
    """A source reading or explicitly named engineering convention."""
    rule_id: str
    source_ids: tuple[str, ...]
    reading: str


@dataclass(frozen=True, slots=True)
class KalachakraConflict:
    """Conflict, evidence coordinates and selected treatment."""
    conflict_id: str
    witness: str
    decision: str


@dataclass(frozen=True, slots=True)
class KalachakraProfile:
    """Bounded executable profile or a non-selectable research candidate."""
    profile_id: str
    admission_status: str
    selectable: bool
    description: str
    profile_version: str | None = None
    source_ids: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    conflict_ids: tuple[str, ...] = ()
    row_namespace: str | None = None
    continuation: str | None = None
    deha_jeeva_reference: str | None = None


@dataclass(frozen=True, slots=True)
class KalachakraCatalogue:
    """Immutable discovery shared by engine and transport."""
    catalogue_version: str
    profiles: tuple[KalachakraProfile, ...]
    sources: tuple[KalachakraSource, ...]
    rules: tuple[KalachakraRule, ...]
    conflicts: tuple[KalachakraConflict, ...]
    ayanamsa_systems: tuple[str, ...]
    supported_levels: tuple[int, ...] = (1,2)
    year_bases: tuple[str, ...] = ("savana_360", "julian_365.25")
    major_period_count: int = 9
    maximum_period_nodes: int = 90
    eligibility_status: str = "not_evaluated"


SOURCES = (
    KalachakraSource("L01", "BPHS, Santhanam, volume 2",
        "ad7172b615568eb812961c71cff352f354c5676b955bc34cfcfdcf431404cd45",
        "PDF 39-54 / printed 529-544, 46.52-100; PDF 309-313 / printed 799-803, chapter 64"),
    KalachakraSource("L02", "PVR Narasimha Rao, Vedic Astrology, 2000",
        "2971851a3cda30929cf5b1ec56b88902bd4a141c8d5479599573ddf1c5f78242",
        "PDF 301-309 / printed 289-297, chapter 24; PDF 319-322 / printed 307-310"),
    KalachakraSource("L09", "Jataka Parijata, Sastri, volume 3",
        "e77f6300e66b5056cb85d42e617c0c33f3b1fbf1a5d614863fac912a8ce023fd",
        "PDF 294-298 / printed 1000-1004, 17.105 commentary and 107-111"),
    KalachakraSource("L11", "Phaladeepika, Kapoor reflow",
        "8b1a4dbb18e9a23c74870a6936b5b74f49e55d2cbfd1422d81eb5dccbaa2c898",
        "PDF 209-218, chapter 22; based on Sastri per PDF 218"),
)
RULES = (
    KalachakraRule("KC_ROWS", ("L01","L02","L09"), "Reconciled 16 rows and 27 memberships; BPHS 46.58-81 and printed 539-540"),
    KalachakraRule("KC_WEIGHTS", ("L01",), "BPHS 46.84 seven classical rulers' sign years"),
    KalachakraRule("KC_BALANCE", ("L01",), "BPHS 46.93 longitude fraction of full natal row"),
    KalachakraRule("KC_CONTINUATION", ("L01",), "Santhanam printed 541-542 repeats the natal row"),
    KalachakraRule("KC_AD", ("L01",), "Chapter 64 rotates the natal row with its unchanged denominator"),
    KalachakraRule("KC_DEHA_JEEVA", ("L01",), "46.94-95 natal-row endpoints, reversed in Apasavya"),
    KalachakraRule("KC_GATI", ("L01",), "46.96-100 named examples only; Cancer/Leo unresolved; seams unclassified"),
    KalachakraRule("KC_PROJECTION", (), "Moira common-origin fixed-day UTC-JD projection; explicit 360 or 365.25 clock"),
    KalachakraRule("KC_BOUND", (), "Moira nine-MD product bound, levels 1-2, exact half-open occurrence ownership"),
)
_CONFLICT_TEXT = (
    ("L01 printed 533 vs 539; L02 Table 46", "Rohini-1 ends Cancer and Rohini-2 ends Libra; retain legitimate duplicate signs"),
    ("L01 printed 534 vs 539; L02 Table 47", "Remove duplicated prose segment, retaining Ge Ta Ar Sg Cp Aq Pi Ar Ta"),
    ("L02 printed 291 vs L01 and JP 17.102-103", "Revati in S1; Uttara Bhadrapada in S2"),
    ("L01 printed 540 upper/lower Krittika diagrams", "Use corroborated Cp/Aq, not duplicate Cp/Cp"),
    ("L01 printed 799/801 extraction flags; 46.84", "Formula weights govern; only visually checked cells are oracles"),
    ("L01 46.90-93", "Longitude method only; no fixed-15 or actual-quarter time-fraction switches"),
    ("L01 printed 541-542; L02 chapter 24; L09 after 17.105", "Natal-row repetition selected; continuous and pada-sign methods remain distinct candidates"),
    ("L01 chapter 64; L02 Example 97; L09 17.107-111", "Natal-row AD rotation and denominator selected"),
    ("L01 46.94-95; L02 24.3.2", "Deha/Jeeva reference is natal_row"),
    ("L01 46.99-100; L09 17.91; L02 24.3.3", "Both Cancer/Leo directions unresolved; no Markati correction borrowed from Rao"),
    ("L11 22.1-8", "Kapoor conflicting labels and rows do not override selected sequence authority"),
    ("L11 22.30; L02 printed 308", "Eligibility not evaluated; no invented strength gate"),
    ("L01 traditional arithmetic; L02 printed 211 footnote 65", "Explicit Moira projection clock; retain exact source years"),
    ("L02 footnote 64 vs printed 309-310 Exercise 34", "Nine-MD product bound; preserve ten-entry printed witness as candidate evidence"),
)
CONFLICTS = tuple(KalachakraConflict(f"KC-{i:02}", *text) for i,text in enumerate(_CONFLICT_TEXT,1))
RULE_IDS = tuple(r.rule_id for r in RULES)
CONFLICT_IDS = tuple(c.conflict_id for c in CONFLICTS)

RAO_RULES = (
    KalachakraRule("R2000_ROWS", ("L01","L02","L09"), "Reconciled memberships (KC-03); L02 Tables 43-48 and weight-derived row totals"),
    KalachakraRule("R2000_WEIGHTS", ("L02",), "Table 48 seven classical rulers' sign years"),
    KalachakraRule("R2000_BALANCE", ("L02",), "Chapter 24 rules 1-3: elapsed longitude fraction of natal row"),
    KalachakraRule("R2000_CONTINUATION", ("L02",), "Rule 4: advance through four padas then the other subgroup in the same family"),
    KalachakraRule("R2000_AD", ("L02",), "Rule 5 / Example 97: nine forward occurrences from parent; recompute denominator; full axis before clipping"),
    KalachakraRule("R2000_DEHA_JEEVA", ("L02",), "24.3.2: first/ninth birth MDs, reversed in Apasavya"),
    KalachakraRule("R2000_GATI", ("L02",), "24.3.3 directed gati readings, including continuous row seams; no predictive prose"),
)
_RAO_DECISIONS = (
    ("Table 45 vs L01/L09; KC-03", "Revati=S1, Uttara Bhadrapada=S2; retain explicit membership correction"),
    ("Tables 44-48", "Row totals derive from weights; S2 totals 100,85,83,86"),
    ("Rule 4 and Example 96", "Continue through rows/subgroups in the same family, not physical nakshatra order"),
    ("Rule 5 / Example 97 / footnote 66", "Nine forward ADs; recomputed denominator; full-parent birth clipping"),
    ("24.3.2", "Deha/Jeeva reference is birth_nine_md_window"),
    ("24.3.3 vs KC-10", "Rao directed gati readings do not resolve Santhanam's conflicting reading"),
    ("Footnote 64 vs Exercise 34 answer", "Nine-MD product; retain tenth printed entry outside admitted coverage"),
    ("Footnote 65", "360 is the author's preferred clock; explicit 365.25 remains a Moira projection, not textbook date parity"),
    ("Chapter 24 and separately identified later schools", "Eligibility not evaluated; no prediction prose; Rao 2018/Rath remain separate"),
)
RAO_CONFLICTS = tuple(KalachakraConflict(f"R2000-{i:02}", *text) for i,text in enumerate(_RAO_DECISIONS,1))
RAO_RULE_IDS = tuple(r.rule_id for r in RAO_RULES) + ("KC_PROJECTION","KC_BOUND")
RAO_CONFLICT_IDS = ("KC-03",) + tuple(c.conflict_id for c in RAO_CONFLICTS)


def kalachakra_profiles() -> KalachakraCatalogue:
    """Discover two named recipes and explicitly non-executable candidates."""
    from .sidereal import Ayanamsa
    from ._kalachakra_recipes import RECIPES
    candidates = (
        ("candidate_sastri_pada_sign", "JP/Sastri pada-sign MD school"),
        ("candidate_rao_2018", "Rao later reformulation, separate from his 2000 profile"),
        ("candidate_rath_alternatives", "Rath's named continuation alternatives"),
        ("candidate_software_listed", "Software-listed variants without a complete reviewed recipe"),
    )
    descriptions = (
        "BPHS/Santhanam longitude balance, natal-row repetition and cyclic ADs",
        "Rao 2000 longitude balance, continuous family rows and recomputed AD denominators",
    )
    profiles = tuple(KalachakraProfile(key, "admitted_bounded", True, description,
        RECIPES[key].version, RECIPES[key].source_ids, RECIPES[key].rule_ids,
        RECIPES[key].conflict_ids, RECIPES[key].namespace, RECIPES[key].continuation,
        RECIPES[key].deha_jeeva_reference) for key,description in zip(PROFILE_IDS,descriptions))
    return KalachakraCatalogue(CATALOGUE_VERSION, profiles +
        tuple(KalachakraProfile(k,"research_candidate",False,d) for k,d in candidates),
        SOURCES, RULES+RAO_RULES, CONFLICTS+RAO_CONFLICTS,tuple(Ayanamsa.ALL))


def _validate_catalogue():
    if sorted(n for ns in GROUPS.values() for n in ns) != list(range(1,28)):
        raise RuntimeError("invalid Kalachakra membership catalogue")
    for group in GROUPS:
        totals = (100,85,83,86) if group[0] == "S" else (86,83,85,100)
        for p,total in enumerate(totals,1):
            row = ROWS[f"{group}/{p}"]
            if len(row) != 9 or any(type(s) is not int or not 0 <= s < 12 for s in row) or sum(WEIGHTS[s] for s in row) != total:
                raise RuntimeError("invalid Kalachakra row catalogue")


_validate_catalogue()
__all__ = ["KalachakraSource", "KalachakraRule", "KalachakraConflict", "KalachakraProfile", "KalachakraCatalogue", "kalachakra_profiles"]
