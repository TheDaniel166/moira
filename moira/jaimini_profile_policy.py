"""VED-013 source-owned profile discovery. Research presence is not executable admission."""

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "JaiminiSource",
    "JaiminiRule",
    "JaiminiConflict",
    "JaiminiProfile",
    "JaiminiProfileCatalogue",
    "list_jaimini_profiles",
]

VERSION = "ved013.1"
CHARA_IDS = (
    "rangacharya_2007_method1_classical7_v1",
    "rangacharya_2007_method2_male_classical7_v1",
    "rangacharya_2007_female_prose_classical7_v1",
)
ARGALA_IDS = (
    "bphs_santhanam_31_literal_assessment_v1",
    "pvr_2000_argala_count_first_v1",
    "rath_argala_article_assessment_v1",
)
CHARACTER_ID = "bphs_santhanam_3_11_root_same_sign_v1"


@dataclass(frozen=True, slots=True)
class JaiminiSource:
    """Identified witness, with a content hash for reviewed PDF editions."""

    source_id: str
    work: str
    author: str
    locator: str
    witness_sha256: str | None
    edition: str


@dataclass(frozen=True, slots=True)
class JaiminiRule:
    """Source clause or explicitly marked engineering composition."""

    rule_id: str
    source_id: str
    passage: str
    printed_pages: tuple[int, ...]
    pdf_pages: tuple[int, ...]
    reading: str


@dataclass(frozen=True, slots=True)
class JaiminiConflict:
    """A retained discrepancy and selected disposition, not a rewritten witness."""

    conflict_id: str
    source_ids: tuple[str, ...]
    decision: str


@dataclass(frozen=True, slots=True)
class JaiminiProfile:
    """Finite capability set; limitations are part of the discoverable contract."""

    profile_id: str
    family: Literal["chara", "argala"]
    admission: Literal["legacy", "admitted_bounded", "research_required"]
    rule_ids: tuple[str, ...]
    capabilities: tuple[str, ...]
    limitations: tuple[str, ...]
    required_inputs: tuple[str, ...]
    operation: str | None
    conflict_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class JaiminiProfileCatalogue:
    """Immutable discovery including explicitly non-executable source leads."""

    catalogue_version: str
    sources: tuple[JaiminiSource, ...]
    rules: tuple[JaiminiRule, ...]
    conflicts: tuple[JaiminiConflict, ...]
    profiles: tuple[JaiminiProfile, ...]


_SOURCES = (
    JaiminiSource(
        "S08",
        "A Manual of Jaimini Astrology",
        "Iranganti Rangacharya",
        "Books by Authors/Jaimini/A Manual of Jaimini Astrology_Iranganti Rangacharya 2009.pdf",
        "8290bc9d8a9d5eedd5ac0724f15554c7ff70f276a26103b58cbd7e068ea5a5f8",
        "First edition 2007; filename says 2009",
    ),
    JaiminiSource(
        "S05",
        "Brihat Parashara Hora Sastra I",
        "R. Santhanam, translator",
        "Classics books/BPHS-Santhanam-Vol-1.pdf",
        "13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f",
        "Printing identified by scan hash",
    ),
    JaiminiSource(
        "S06",
        "Brihat Parashara Hora Sastra II",
        "R. Santhanam, translator",
        "Classics books/BPHS-Santhanam-Vol-2.pdf",
        "ad7172b615568eb812961c71cff352f354c5676b955bc34cfcfdcf431404cd45",
        "Printing identified by scan hash",
    ),
    JaiminiSource(
        "W03",
        "Vedic Astrology: An Integrated Approach",
        "P.V.R. Narasimha Rao",
        "https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf",
        "1cafa828f34764ed5e85816882df2e8f0bc014c5c57ccdb27169416e117fd4db",
        "2000 textbook; author-hosted witness",
    ),
    JaiminiSource(
        "W04",
        "Argala: Planetary Intervention",
        "Sanjay Rath",
        "https://srath.com/jyoti%E1%B9%A3a/amateur/argala-planetary-intervention/",
        None,
        "Live author page inspected 2026-10-12; fixture contains bounded witnesses",
    ),
    JaiminiSource(
        "W01",
        "Unlocking the Power of Parasara's Chara Dasa",
        "P.V.R. Narasimha Rao",
        "https://www.vedicastrologer.org/articles/pp_chara_dasa.pdf",
        "2a6b1b224fb0f1b2bd7f1f55403f5a6f3c805277f71c5389b1ae8d14afb00fb0",
        "14 April 2014 v1",
    ),
    JaiminiSource(
        "W02",
        "Narayana Dasa",
        "Sanjay Rath",
        "https://scienceoflight.net/wp-content/uploads/extra/Narayana%20Dasa%20by%20Sanjay%20Rath.pdf",
        "8ed7732034092828dca800cdc6aa9422c742c498517700c0a0654ec4926d1206",
        "Witness identified by scan hash",
    ),
)
_RULES = (
    JaiminiRule(
        "rangacharya.method1",
        "S08",
        "Chara method 1",
        (65, 66),
        (71, 72),
        "Ninth-footed sequence; sign-footed count minus one; own twelve before dignity adjustment; classical lords.",
    ),
    JaiminiRule(
        "rangacharya.method2.male",
        "S08",
        "Chara method 2",
        (66, 67, 68),
        (72, 73, 74),
        "Lagna parity and seed modality; lord-to-sign inclusive count using lord parity; own twelve.",
    ),
    JaiminiRule(
        "rangacharya.female.prose",
        "S08",
        "Female-chart recipe",
        (68, 69, 70),
        (74, 75, 76),
        "Prakriti fourth seed; Lagna parity; lord-to-sign count minus one using dasha-sign parity; own twelve, opposite ten.",
    ),
    JaiminiRule(
        "bphs.31.formation",
        "S05",
        "31.2-9.5",
        (311, 312, 313),
        (310, 311, 312),
        "Four pairs, node-reference reversal, count grades and greater-number alternative; three-malefic special third.",
    ),
    JaiminiRule(
        "bphs.31.quarters",
        "S05",
        "31.10 and commentary",
        (314,),
        (313,),
        "Directed Q1/Q4 and Q2/Q3 only; mixed multioccupant aggregation unestablished.",
    ),
    JaiminiRule(
        "bphs.3.11.character",
        "S05",
        "3.11 root verse",
        (27,),
        (26,),
        "Nine-body natural character; same-sign Mercury association; Moon half-cycle boundaries are explicit engineering choices.",
    ),
    JaiminiRule(
        "bphs.erratum.313",
        "S05",
        "Errata row for page 313",
        (483,),
        (482,),
        "Add Rahu in Gemini to the Argala chart.",
    ),
    JaiminiRule(
        "pvr2000.argala",
        "W03",
        "10.6-10.7; Exercise 16",
        (105, 106, 110, 111),
        (117, 118, 122, 123),
        "Count-first assessment and Ketu-occupied-reference reversal; no admitted equal-count strength comparator.",
    ),
    JaiminiRule(
        "rath.article.argala",
        "W04",
        "Primary, secondary and special intervention illustrations",
        (),
        (),
        "Nine-body subset including 8/6 and 7/1; own-sign/Jupiter rasi-aspect factors without a universal strength ranking.",
    ),
)
_CONFLICTS = (
    JaiminiConflict(
        "C04",
        ("S08",),
        "Female Cancer: select own-sign prose twelve; preserve printed ten.",
    ),
    JaiminiConflict(
        "C06",
        ("S06",),
        "Chara diagram nodes and Scorpio duration conflict remain unresolved; no full BPHS Chara admission.",
    ),
    JaiminiConflict(
        "C07", ("S05",), "Argala omission resolved by printed erratum: Rahu in Gemini."
    ),
    JaiminiConflict(
        "PVR2014",
        ("W01",),
        "Seed priority, direction, weakness cutoffs and solar-year clock remain research gates.",
    ),
    JaiminiConflict(
        "C12",
        ("W04",),
        "Standard nativity: Jupiter in Pisces casts rasi aspects to both Gemini and Sagittarius. This factor alone cannot reproduce the article's Ketu-side winner; no asymmetric aspect or priority is invented.",
    ),
)
_CHARA_ROUTE = "/v1/jaimini/extended/chara-dasha/profile"
_ARGALA_ROUTE = "/v1/jaimini/extended/argala/assessment"
_PROFILES = (
    JaiminiProfile(
        "moira_kn_rao_existing_v1",
        "chara",
        "legacy",
        (),
        ("one_or_two_cycles", "antardashas", "julian_365.25"),
        ("retained co-lord convention; full lineage collation incomplete",),
        ("seven_longitudes", "lagna", "epoch_jd"),
        "/v1/jaimini/extended/chara-dasha",
    ),
    *(
        JaiminiProfile(
            pid,
            "chara",
            "admitted_bounded",
            (rule,),
            (
                "twelve_arithmetic_rows",
                "one_cycle",
                "mahadashas",
                "optional_fixed_day_projection",
            ),
            (
                "no_antardashas",
                "no_second_cycle",
                "no_node_co_lords",
                "projection_is_moira_convention",
            ),
            ("seven_positions", "lagna", "explicit_profile"),
            _CHARA_ROUTE,
            ("C04",) if i == 2 else (),
        )
        for i, (pid, rule) in enumerate(
            zip(
                CHARA_IDS,
                (
                    "rangacharya.method1",
                    "rangacharya.method2.male",
                    "rangacharya.female.prose",
                ),
            )
        )
    ),
    JaiminiProfile(
        "moira_argala_existing_v1",
        "argala",
        "legacy",
        (),
        ("seven_occupants", "count_only", "optional_partial_nodes_for_reversal"),
        ("two_malefic_threshold_is_legacy", "no_strength_grade"),
        ("seven_longitudes", "lagna"),
        "/v1/jaimini/extended/argala",
    ),
    JaiminiProfile(
        ARGALA_IDS[0],
        "argala",
        "admitted_bounded",
        (
            "bphs.31.formation",
            "bphs.31.quarters",
            "bphs.3.11.character",
            "bphs.erratum.313",
        ),
        (
            "four_pairs",
            "count_grade",
            "directed_quarters",
            "three_malefic_third",
            "node_reference_reversal",
            CHARACTER_ID,
        ),
        (
            "strength_comparator_not_admitted",
            "multioccupant_quarter_composition_unestablished",
        ),
        ("nine_positions", "lagna", "references", "explicit_profile"),
        _ARGALA_ROUTE,
        ("C07",),
    ),
    JaiminiProfile(
        ARGALA_IDS[1],
        "argala",
        "admitted_bounded",
        ("pvr2000.argala", "bphs.3.11.character"),
        ("four_pairs", "count_first", "ketu_occupied_sign_reversal", CHARACTER_ID),
        (
            "strength_comparator_not_admitted",
            "special_third_threshold_not_admitted",
            "count_grade_not_assessed",
        ),
        ("nine_positions", "lagna", "references", "explicit_profile"),
        _ARGALA_ROUTE,
    ),
    JaiminiProfile(
        ARGALA_IDS[2],
        "argala",
        "admitted_bounded",
        ("rath.article.argala", "bphs.3.11.character"),
        (
            "six_pairs",
            "strength_factor_witnesses",
            "ketu_occupied_sign_reversal",
            CHARACTER_ID,
        ),
        (
            "factor_priority_not_admitted",
            "special_third_threshold_not_admitted",
            "count_grade_not_assessed",
            "no_upagrahas_or_empty_sign_interventions",
        ),
        ("nine_positions", "lagna", "references", "explicit_profile"),
        _ARGALA_ROUTE,
        ("C12",),
    ),
    JaiminiProfile(
        "bphs_chara_research",
        "chara",
        "research_required",
        (),
        (),
        (
            "co_lord_precedence_ties_dignities",
            "diagram_conflict",
            "subperiod_clock_cycle_admission",
        ),
        (),
        None,
        ("C06",),
    ),
    JaiminiProfile(
        "pvr_2014_chara_research",
        "chara",
        "research_required",
        (),
        (),
        ("seed_and_direction_conflicts", "weakness_cutoffs", "solar_year_clock"),
        (),
        None,
        ("PVR2014",),
    ),
    JaiminiProfile(
        "rath_narayana_research",
        "chara",
        "research_required",
        (),
        (),
        ("separate_family", "exceptions_subperiods_complement_cycle"),
        (),
        None,
    ),
    JaiminiProfile(
        "rangacharya_yogada_research",
        "argala",
        "research_required",
        (),
        (),
        (
            "aspecting_planet_orders",
            "source_varga_conventions",
            "merit_demerit_aggregation",
        ),
        (),
        None,
    ),
    JaiminiProfile(
        "argala_general_strength_research",
        "argala",
        "research_required",
        (),
        (),
        ("source_comparator_group_aggregation_and_ties",),
        (),
        None,
    ),
)


def list_jaimini_profiles() -> JaiminiProfileCatalogue:
    """Return immutable discovery; nothing in this operation reads books at runtime."""
    return JaiminiProfileCatalogue(VERSION, _SOURCES, _RULES, _CONFLICTS, _PROFILES)


def admit_profile(profile_id, family):
    """Return the exact executable profile or reject unsupported selectors."""
    ids = CHARA_IDS if family == "chara" else ARGALA_IDS
    if type(profile_id) is not str or profile_id not in ids:
        raise ValueError(f"unsupported {family} profile")
    return next(p for p in _PROFILES if p.profile_id == profile_id)
