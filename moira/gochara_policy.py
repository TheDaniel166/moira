"""Moira — Gochara policy and doctrine catalogue.

Archetype: Engine
Owns: typed evaluation scope, fixed source selection, admission metadata.
Delegates: numerical rule evaluation to moira.gochara.
Governing object: a source-bound natal-Moon snapshot, never a blended tradition.
Authority: Phaladeepika 26 (Sastri 1950), with separately identified research
alternatives from Brihat Samhita, Prasna Marga and modern commentary.
Boundary: catalogue entries are evidence records, not executable presets.
Engine scope controls are explicitly distinguished from textual doctrine.
Unsupported sources, reference systems and node rules cannot be selected by
constructing an arbitrary string-valued policy. No import-time I/O occurs.
"""

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "GOCHARA_PROFILE", "GOCHARA_PLANETS", "DEFAULT_GOCHARA_POLICY",
    "GocharaSourceProfile", "GocharaVedhaMode", "GocharaCompleteness",
    "GocharaBavMode", "GocharaAdmissionStatus", "GocharaDoctrineOption",
    "GocharaPolicy", "gochara_doctrine_options",
]

GOCHARA_PROFILE = "phaladeepika_26_sastri_1950_seven_classical"
GOCHARA_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")


class GocharaSourceProfile(str, Enum):
    """Executable, source-collated profiles; research options are catalogued separately."""

    PHALADEEPICA_26 = GOCHARA_PROFILE


class GocharaVedhaMode(str, Enum):
    """Evaluation scope over the selected text, preserving omitted-layer receipts."""

    ORDINARY = "ordinary"
    BASELINE_ONLY = "baseline_only"


class GocharaCompleteness(str, Enum):
    """Engineering admission of partial positions versus a required seven-body snapshot."""

    RETAIN_PARTIAL = "retain_partial"
    REQUIRE_COMPLETE = "require_complete"


class GocharaBavMode(str, Enum):
    """Raw context scope; no mode supplies a threshold or strength override."""

    RAW_IF_SUPPLIED = "raw_if_supplied"
    OMIT = "omit"
    REQUIRE_ALL_RAW = "require_all_raw"


class GocharaAdmissionStatus(str, Enum):
    """Implementation admission, distinct from attestation in an inspected source."""

    ADMITTED = "admitted"
    SOURCE_ATTESTED = "source_attested_not_admitted"
    DISPUTED = "disputed_not_admitted"
    RESEARCH_REQUIRED = "research_required"
    OUT_OF_SCOPE = "outside_snapshot_scope"


@dataclass(frozen=True, slots=True)
class GocharaDoctrineOption:
    """One immutable, cited policy decision or research alternative, with its limit."""

    id: str
    topic: str
    status: GocharaAdmissionStatus
    authority_kind: str
    sources: tuple[str, ...]
    statement: str
    limitation: str

    def __post_init__(self):
        if not isinstance(self.status, GocharaAdmissionStatus):
            raise TypeError("status must be a GocharaAdmissionStatus")
        for name in ("id", "topic", "statement", "limitation"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if self.authority_kind not in ("textual", "engine_scope", "modern_author", "research"):
            raise ValueError("unknown authority_kind")
        if isinstance(self.sources, str):
            raise TypeError("sources must be a sequence of source locators")
        sources = tuple(self.sources)
        if not sources or any(not isinstance(s, str) or not s.strip() for s in sources):
            raise ValueError("at least one nonempty source locator is required")
        object.__setattr__(self, "sources", sources)


@dataclass(frozen=True, slots=True)
class GocharaPolicy:
    """Typed choices for the admitted seven-body Phaladeepika snapshot domain.

    Source, natal-Moon reference and participant universe are inseparable from
    the admitted profile. Scope controls may omit ordinary Vedha or raw BAV,
    or require sufficient input; they do not claim a different textual school.
    Unadmitted alternatives remain in the doctrine catalogue. A supplied BAV
    is a caller assertion of natal identity and unreduced provenance.
    """

    source_profile: GocharaSourceProfile = GocharaSourceProfile.PHALADEEPICA_26
    vedha_mode: GocharaVedhaMode = GocharaVedhaMode.ORDINARY
    completeness: GocharaCompleteness = GocharaCompleteness.RETAIN_PARTIAL
    bav_mode: GocharaBavMode = GocharaBavMode.RAW_IF_SUPPLIED
    reference: str = field(init=False, default="natal_moon_rasi")
    subjects: tuple[str, ...] = field(init=False, default=GOCHARA_PLANETS)
    blockers: tuple[str, ...] = field(init=False, default=GOCHARA_PLANETS)

    def __post_init__(self):
        for name, kind in (
            ("source_profile", GocharaSourceProfile), ("vedha_mode", GocharaVedhaMode),
            ("completeness", GocharaCompleteness), ("bav_mode", GocharaBavMode),
        ):
            if not isinstance(getattr(self, name), kind):
                raise TypeError(f"{name} must be a {kind.__name__}; inspect gochara_doctrine_options for alternatives")

    @property
    def selected_options(self) -> tuple[GocharaDoctrineOption, ...]:
        """Cited decisions that actually govern this policy, in fixed axis order."""
        ids = (
            "profile.phaladeepika_26", "reference.natal_moon", "participants.seven_classical",
            f"vedha.{self.vedha_mode.value}", f"completeness.{self.completeness.value}",
            f"bav.{self.bav_mode.value}", "activation.whole_sign_snapshot",
            "astronomy.caller_sidereal",
        )
        return tuple(next(option for option in _OPTIONS if option.id == id_) for id_ in ids)


DEFAULT_GOCHARA_POLICY = GocharaPolicy()
_PHALA = "Phaladeepika, V. Subrahmanya Sastri, second edition 1950"
_BRIHAT = "Brihat Samhita, Sastri/Bhat 1946"
_PRASNA = "Prasna Marga Part II, B. V. Raman, 1992 edition"
_RAO = "P. V. R. Narasimha Rao, Vedic Astrology: An Integrated Approach"
_ENGINE = "Moira Gochara snapshot scope doctrine, 2026-10-06"
_A = GocharaAdmissionStatus


def _option(id_, topic, status, kind, sources, statement, limitation):
    return GocharaDoctrineOption(id_, topic, status, kind, sources, statement, limitation)


_OPTIONS = (
    _option("profile.phaladeepika_26", "source_profile", _A.ADMITTED, "textual",
            (f"{_PHALA}, 26.1-23",), "The collated Phaladeepika profile governs baseline, indications and ordinary Vedha.",
            "A named edition governs; this is not an amalgam of all transit literature."),
    _option("profile.brihat_samhita_104", "source_profile", _A.SOURCE_ATTESTED, "textual",
            (f"{_BRIHAT}, 104.4, 104.17, 104.49-55",), "An independently attested transit treatment includes different indications and timing.",
            "A complete narrative, relation and modifier corpus must be admitted before selecting this profile."),
    _option("reference.natal_moon", "reference", _A.ADMITTED, "textual",
            (f"{_PHALA}, 26.1",), "Count whole signs inclusively from the natal Moon sign.",
            "Lagna, Sun and nakshatra reference products are not interchangeable with this result."),
    _option("reference.alternatives", "reference", _A.RESEARCH_REQUIRED, "research",
            ("Muhurta Chintamani 4.5 transcription lead; printed-edition collation pending",),
            "Other reference or regional views require their own authority and object.",
            "This catalogue lead does not admit alternate reference arithmetic."),
    _option("participants.seven_classical", "participants", _A.ADMITTED, "engine_scope",
            (_ENGINE, f"{_PHALA}, 26.2-8"), "The conservative snapshot domain fixes seven classical subjects and blockers.",
            "This participant restriction is an explicit admission decision, not a claim that the text excludes nodes."),
    _option("nodes.phaladeepika_sun_like", "nodes", _A.SOURCE_ATTESTED, "textual",
            (f"{_PHALA}, 26.2, 26.24",), "The nodal favorable baseline includes 3, 6, 10 and 11; Rahu has separate indications.",
            "Ketu narrative, nodal Vedha, exemptions and node astronomy need separate admission; baseline analogy cannot supply them."),
    _option("nodes.prasna_marga_saturn_like", "nodes", _A.SOURCE_ATTESTED, "textual",
            (f"{_PRASNA}, 22.51",), "A different nodal treatment gives favorable 3, 6, 11 and blocking 12, 9, 5.",
            "This is a separate source alternative; do not merge it with Phaladeepika's tenth-position rule."),
    _option("nodes.blocker_participation", "nodes", _A.RESEARCH_REQUIRED, "research",
            (f"{_PHALA}, 26.2-8; participant interpretation unresolved",),
            "Whether nodes obstruct classical subjects is a distinct participant decision.",
            "A nodal favorable list does not establish blocker participation or inherited exemptions."),
    _option("vedha.ordinary", "vedha", _A.ADMITTED, "textual",
            (f"{_PHALA}, 26.3-8",), "Occupancy of a directed Vedha sign obstructs a favorable baseline, with named exceptions.",
            "No aspect orb, malefic-only filter or reversed-pair relief is inferred."),
    _option("vedha.baseline_only", "vedha", _A.ADMITTED, "engine_scope",
            (_ENGINE, f"{_PHALA}, 26.1-2, 26.9-23"), "A baseline-only request retains the source indication and explicitly omits ordinary Vedha evaluation.",
            "Omission is evaluation scope, not textual permission to declare every favorable baseline unobstructed."),
    _option("vedha.counter_vedha", "counter_vedha", _A.SOURCE_ATTESTED, "textual",
            (f"{_PRASNA}, 22.34-35, 22.43, 22.53", "Muhurta Chintamani 4.4 transcription lead"),
            "Counter-Vedha relief is separately attested.",
            "Worked examples, exceptions and favorable/blocking overlaps must be resolved before executable admission."),
    _option("vedha.venus_modern_table", "source_discrepancies", _A.DISPUTED, "modern_author",
            (f"{_PHALA}, 26.8", f"{_RAO}, Table 63, printed p.347"),
            "The modern table's final Venus blockers differ from the selected edition's 11-to-3 and 12-to-6.",
            "A recorded discrepancy is not an executable alternate preset."),
    _option("indications.mars_tenth", "source_discrepancies", _A.DISPUTED, "textual",
            (f"{_PHALA}, 26.16", f"{_BRIHAT}, 104.17", f"{_PRASNA}, 22.9"),
            "Mars in the tenth has different indications across the inspected texts and translations.",
            "Keep each narrative with its source; favorable membership is not a universal good/bad taxonomy."),
    _option("tables.prasna_marga_1992", "source_discrepancies", _A.DISPUTED, "textual",
            (f"{_PRASNA}, 22.36, 22.38, 22.40-41, 22.47, 22.49-50",),
            "The inspected edition contains conflicting numerical sequences.",
            "Their cause is unresolved; no repaired or automatically zipped alternate table is admitted."),
    _option("activation.whole_sign_snapshot", "activation", _A.ADMITTED, "engine_scope",
            (_ENGINE, f"{_PHALA}, 26.2, 26.9-23"), "Evaluate whole-sign baseline membership at the supplied instant.",
            "No claim about sign-part activation or the date of event fruition is made."),
    _option("activation.phaladeepika_decanates", "activation", _A.SOURCE_ATTESTED, "textual",
            (f"{_PHALA}, 26.25, printed p.296",), "Sign-part timing uses named first, middle and last decanates.",
            "This timing layer is not evaluated by the whole-sign snapshot policy."),
    _option("activation.brihat_samhita_parts", "activation", _A.SOURCE_ATTESTED, "textual",
            (f"{_BRIHAT}, 104.49-50",), "A separate timing treatment uses sign halves and Mercury throughout.",
            "Do not replace distinct source timing rules with one generic ten-degree gate."),
    _option("bav.raw_if_supplied", "ashtakavarga", _A.ADMITTED, "engine_scope",
            (_ENGINE, f"{_PHALA}, 26.41"), "Retain a supplied subject's own unreduced BAV count at the absolute transit sign.",
            "Birth identity and reduction provenance remain caller assertions; the raw count supplies no override."),
    _option("bav.omit", "ashtakavarga", _A.ADMITTED, "engine_scope",
            (_ENGINE,), "Explicitly omit raw BAV context and reject contradictory supplied tables.",
            "Omission does not establish that Ashtakavarga is irrelevant to the tradition."),
    _option("bav.require_all_raw", "ashtakavarga", _A.ADMITTED, "engine_scope",
            (_ENGINE,), "Require own raw BAV context for every supplied subject.",
            "This is input completeness, not a textual interpretation of favorable strength."),
    _option("bav.four_rekhas", "ashtakavarga", _A.DISPUTED, "textual",
            ("Phaladeepika, Kapoor edition, 23.11 and commentary, PDF pp.225-226",
             "Jataka Parijata, Sastri commentary, Vol II PDF pp.341-343"),
            "Treatment of four rekhas differs by passage and commentary context.",
            "No threshold, BAV strength override or correction to existing Moira BAV conventions is admitted here."),
    _option("strength.dasha", "strength_context", _A.SOURCE_ATTESTED, "textual",
            (f"{_BRIHAT}, 104.46", f"{_PRASNA}, notes after 22.26"),
            "Period context can qualify transit testimony.",
            "The sources do not establish one universal weighted transit/dasha score."),
    _option("strength.dignity_aspects", "strength_context", _A.SOURCE_ATTESTED, "textual",
            (f"{_BRIHAT}, 104.52-55", f"{_PRASNA}, 22.44"),
            "Dignity, planetary condition and aspects supply additional testimony.",
            "Graha Drishti, Rasi Drishti and angular aspects are separate relation objects; none is an automatic Vedha replacement."),
    _option("murthi.ingress_moon", "murthi", _A.RESEARCH_REQUIRED, "modern_author",
            (f"{_RAO}, printed pp.346-347",), "The modern method uses the Moon at the exact planet ingress.",
            "Earlier authority, ingress-time astronomy and retrograde re-entry ownership remain unadmitted."),
    _option("nakshatra.chakra_extensions", "nakshatra", _A.SOURCE_ATTESTED, "textual",
            (f"{_PHALA}, 26.26 onward",), "Nakshatra, chakra and Latta techniques are distinct extensions.",
            "Their star geometry and 27/28-position conventions require independent source fixtures and policies."),
    _option("completeness.retain_partial", "completeness", _A.ADMITTED, "engine_scope",
            (_ENGINE,), "Retain partial observations; a known blocker proves obstruction, but absent eligible blockers prevent clearance.",
            "Missing is not a confirmed empty sign."),
    _option("completeness.require_complete", "completeness", _A.ADMITTED, "engine_scope",
            (_ENGINE,), "Require all seven transit positions before evaluating any subject.",
            "This input rule does not change baseline or obstruction semantics."),
    _option("astronomy.caller_sidereal", "astronomy", _A.ADMITTED, "engine_scope",
            (_ENGINE,), "The caller supplies consistently converted sidereal positions at each position's own epoch.",
            "Ayanamsa and correction regime are not inferred or certified by this evaluator; node models remain outside its participant set."),
    _option("forecast.dated_events", "forecast", _A.OUT_OF_SCOPE, "engine_scope",
            (_ENGINE,), "Dated forecasts require sidereal subject and blocker ingress boundaries, including retrograde re-entry.",
            "A snapshot is not an ingress solver or forecast window."),
    _option("remedies.interpretation", "remedies", _A.OUT_OF_SCOPE, "textual",
            (f"{_PHALA}, Chapter 26",), "Classical remedies are an independent interpretive scope.",
            "The computational snapshot produces no ritual, gemstone or donation recommendations."),
)


def gochara_doctrine_options(topic: str | None = None) -> tuple[GocharaDoctrineOption, ...]:
    """Inspect admitted choices and research alternatives; never execute a catalogue entry."""
    if topic is None:
        return _OPTIONS
    if not isinstance(topic, str):
        raise TypeError("topic must be a string or None")
    selected = tuple(option for option in _OPTIONS if option.topic == topic)
    if not selected:
        raise ValueError(f"unknown Gochara doctrine topic {topic!r}")
    return selected
