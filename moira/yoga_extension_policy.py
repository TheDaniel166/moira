"""Finite, source-owned VED-012 catalogue; source presence is not admission.

Authority: JP/Sastri 7.14; Raman, Three Hundred Important Combinations 252;
BPHS/Santhanam 41.2-15 and 39.33-34,36-39. Scan hashes and page locators
identify the reviewed witnesses; exact printing years are not invented.
No runtime source files, ephemeris, or third-party libraries are required.
"""

from dataclasses import dataclass

__all__ = [
    "YogaExtensionSource",
    "YogaExtensionRule",
    "YogaExtensionProfile",
    "YogaExtensionPolicy",
    "YogaExtensionCatalogue",
    "list_yoga_extension_rules",
]

_VERSION = "ved012.1"
_PROFILE_IDS = (
    "jp_sastri_7_14_v1",
    "raman_300_252_all_debilitated_v1",
    "bphs_santhanam_41_2_15_v1",
    "bphs_santhanam_39_selected_v1",
)


@dataclass(frozen=True, slots=True)
class YogaExtensionSource:
    """Immutable identity of an inspected source witness, including its scan hash."""

    source_id: str
    work: str
    translator_or_author: str
    publisher: str
    witness_sha256: str
    local_corpus_path: str
    printing: str = "exact printing year unestablished; identified by scan hash"


@dataclass(frozen=True, slots=True)
class YogaExtensionRule:
    """One passage-owned rule, its selected reading and explicit admission state."""

    rule_id: str
    profile_id: str
    name: str
    family: str
    effect_kind: str
    source: YogaExtensionSource
    passage: str
    printed_pages: tuple[int, ...]
    pdf_pages: tuple[int, ...]
    interpretation: str
    admission: str = "admitted"
    limitation: str = ""
    overlaps: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class YogaExtensionProfile:
    """Finite rule selection and whether its computation requires Navamsa."""

    profile_id: str
    rule_ids: tuple[str, ...]
    requires_navamsa: bool


@dataclass(frozen=True, slots=True)
class YogaExtensionPolicy:
    """Explicit selection; order is canonical, never caller-dependent."""

    profile_ids: tuple[str, ...]

    def __post_init__(self):
        ids = self.profile_ids
        if type(ids) not in (list, tuple) or not 1 <= len(ids) <= 4:
            raise ValueError("profile_ids must contain one to four supported profiles")
        if any(type(p) is not str or p not in _PROFILE_IDS for p in ids):
            raise ValueError("unsupported yoga extension profile")
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate yoga extension profile")
        object.__setattr__(
            self, "profile_ids", tuple(p for p in _PROFILE_IDS if p in ids)
        )

    @property
    def catalogue_version(self) -> str:
        return _VERSION

    @property
    def house_frame(self) -> str:
        return "sidereal_whole_sign_lagna"

    @property
    def aspect_model(self) -> str:
        return "full_graha_drishti"

    @property
    def conjunction_model(self) -> str:
        return "same_sign_distinct_bodies"

    @property
    def navamsa_model(self) -> str:
        return "moira.varga.navamsa_exact_partition"


@dataclass(frozen=True, slots=True)
class YogaExtensionCatalogue:
    """Immutable discovery record for admitted profiles and unresolved source leads."""

    catalogue_version: str
    profiles: tuple[YogaExtensionProfile, ...]
    rules: tuple[YogaExtensionRule, ...]
    house_frame: str = "sidereal_whole_sign_lagna"
    aspect_model: str = "full_graha_drishti"
    conjunction_model: str = "same_sign_distinct_bodies"
    navamsa_model: str = "moira.varga.navamsa_exact_partition"
    required_inputs: tuple[str, ...] = (
        "seven_classical_sidereal_longitudes",
        "sidereal_lagna",
        "profile_ids",
    )
    longitude_range: str = "[0,360) degrees"
    outcome_scope: str = (
        "source-defined formation; life outcomes, dasha and strength not assessed"
    )


_JP = YogaExtensionSource(
    "jp_sastri_scan",
    "Jataka Parijata, Volume II",
    "V. Subrahmanya Sastri (translator)",
    "Ranjan Publications",
    "898de4c6f212c46e4376a64c3fd341bc64c8d11d6ace504a3acc25142a00b2dd",
    "Classics books/Jataka-Parijata-Vol-2.pdf",
)
_RAMAN = YogaExtensionSource(
    "raman_300_scan",
    "Three Hundred Important Combinations",
    "B. V. Raman",
    "Motilal Banarsidass",
    "3d511f6237659d72ea590324fcc7c41c4403d2ac9266715872315b3d930646cc",
    "Books by Authors/BV Raman/300 Important Combinations.pdf",
)
_BPHS = YogaExtensionSource(
    "bphs_santhanam_scan",
    "Brihat Parashara Hora Sastra, Volume I",
    "R. Santhanam (translator)",
    "Ranjan Publications",
    "13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f",
    "Classics books/BPHS-Santhanam-Vol-1.pdf",
)

_NAVAMSA_RULES = (
    YogaExtensionRule(
        "jp.7.14",
        _PROFILE_IDS[0],
        "Navamsa-lord relief",
        "navamsa",
        "debilitation_relief",
        _JP,
        "7.14",
        (387,),
        (71,),
        "Any debilitated D1 body: its D9 lord in a D1 Lagna kendra/trikona AND "
        "(movable D1 Lagna OR movable D9 sign of the D1 Lagna lord).",
    ),
    YogaExtensionRule(
        "raman.252",
        _PROFILE_IDS[1],
        "Exalted Navamsa relief",
        "navamsa",
        "debilitation_relief",
        _RAMAN,
        "252; Chart 122",
        (245, 248),
        (255, 258),
        "Nonempty set of D1-debilitated classical bodies, ALL exalted in D9. "
        "Selected plural reading; distinct from JP 7.14.",
    ),
)
_WEALTH_RULES = tuple(
    YogaExtensionRule(
        f"bphs.41.{v}",
        _PROFILE_IDS[2],
        f"BPHS wealth {v}",
        "dhana",
        "wealth_combination",
        _BPHS,
        f"41.{v}",
        ((402,) if v == 2 else (403,) if v <= 5 else (404,) if v <= 9 else (405,)),
        ((401,) if v == 2 else (402,) if v <= 5 else (403,) if v <= 9 else (404,)),
        (
            "Named planet owns/occupies H5; ALL named H11 occupants required."
            if v <= 8
            else "Named planet owns/occupies H1; ALL supporters each conjunct OR cast a full aspect on it."
        ),
        limitation="BPHS 41.17 strength/disposition and 41.16 dasha context are not assessed.",
    )
    for v in range(2, 16)
)
_RAJA_DEFINITIONS = (
    (
        "33-34",
        "L5/L9 mutual full aspects OR conjunction OR opposite signs; royal-lineage outcome premise not assessed.",
    ),
    ("36", "L5, L10, L4 and L1 ALL in H9; one body may hold several roles."),
    (
        "37",
        "ANY distinct-body conjunction of L4/L10 with L5/L9; retain all four branches.",
    ),
    ("38", "L5 in H1/H4/H10 AND conjunct L9 or L1, with distinct physical bodies."),
    ("39", "Jupiter owns/occupies H9 AND joins Venus or L5."),
)
_RAJA_RULES = tuple(
    YogaExtensionRule(
        f"bphs.39.{v}",
        _PROFILE_IDS[3],
        f"BPHS Raja {v}",
        "raja",
        "royal_combination",
        _BPHS,
        f"39.{v}",
        (395 if v in ("33-34", "36", "37") else 396,),
        (394 if v in ("33-34", "36", "37") else 395,),
        reading,
        limitation="Historical outcome/ancestry context is not chart-derived or evaluated.",
        overlaps=("legacy_kendra_trikona_family",) if v in ("37", "38") else (),
    )
    for v, reading in _RAJA_DEFINITIONS
)
_DEFERRED = YogaExtensionRule(
    "bphs.39.35",
    _PROFILE_IDS[3],
    "Fourth/tenth exchange with aspects",
    "raja",
    "royal_combination",
    _BPHS,
    "39.35",
    (395,),
    (394,),
    "Aspect targets/type unresolved; no executable interpretation selected.",
    admission="research_required",
    limitation="Requiring each L5/L9 supporter to fully aspect BOTH "
    "opposite H4/H10 occupants is impossible under this graha-aspect model. "
    "Collate a primary target/type reading and a satisfiable witness before admission.",
)
_RULES = _NAVAMSA_RULES + _WEALTH_RULES + _RAJA_RULES
_PROFILES = tuple(
    YogaExtensionProfile(
        p, tuple(r.rule_id for r in _RULES if r.profile_id == p), p in _PROFILE_IDS[:2]
    )
    for p in _PROFILE_IDS
)


def list_yoga_extension_rules() -> YogaExtensionCatalogue:
    """Return the immutable catalogue, including explicitly non-admitted 39.35."""
    return YogaExtensionCatalogue(_VERSION, _PROFILES, _RULES + (_DEFERRED,))


def _selected_rules(policy: YogaExtensionPolicy) -> tuple[YogaExtensionRule, ...]:
    return tuple(r for r in _RULES if r.profile_id in policy.profile_ids)
