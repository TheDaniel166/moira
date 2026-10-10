"""Source-selected Muhurta restrictions and independently witnessed exceptions.

Six finite detectors preserve temporal uncertainty and their original evidence
even when a selected Parihara applies. They do not grade a complete election.
Source loci and alternative readings are recorded in the VED-009 source packet.
"""
from dataclasses import dataclass, field
from datetime import date

from .daily_panchanga import PanchangaSunriseDefinition
from .named_muhurta import NamedMuhurtaPolicy
from .panchanga_shuddhi import (
    ShuddhiBoundary, ShuddhiInterval, _number, _integer, _longitude, _sector,
)
from .sidereal import list_ayanamsa_systems

MC_TABLE = "mc_vivaha_49_51.v1"
KP_TABLE = "kp_185_single_mula.v1"
KP_DUAL_TABLE = "kp_185_dual_mula.v1"
FIXED_WIDTH = "mc_avasthi_scaled_start_fixed_width.v1"
SCALED_WIDTH = "normalized_nakshatra_sixtieths.v1"
MC_GANDANTA = "mc_vivaha_43_fixed_ghati.v1"
BP_GANDANTA = "bphs_santhanam_92_fixed_ghati.v1"
YAMA_STAR = "mc_shubhashubha_9_yamaghanta.v1"
YAMA_TIME = "mc_shubhashubha_37_sixteenths.v1"
KP_EXEMPT = "kp_195_seven_star_tyajya_exemption.v1"
MC_NECESSARY = "mc_shubhashubha_37_necessary_first_half.v1"
MC_ABHIJIT = "mc_avasthi_vivaha_43_abhijit.v1"
_TABLES = (MC_TABLE, KP_TABLE, KP_DUAL_TABLE)
_CLOCKS = (FIXED_WIDTH, SCALED_WIDTH)
_GANDANTAS = (MC_GANDANTA, BP_GANDANTA)
_PARIHARAS = (KP_EXEMPT, MC_NECESSARY, MC_ABHIJIT)
_OFFSETS = (50, 24, 30, 40, 14, 21, 30, 20, 32, 30, 20, 18, 21, 20,
            14, 14, 10, 14, 56, 24, 20, 10, 10, 18, 16, 24, 30)
_YAMA_STARS = (9, 15, 5, 18, 2, 3, 12)
_EXEMPT_STARS = (5, 21, 4, 14, 20, 3, 16)
_RULES = ("vishanadi", "yamaghanta_yoga", "yamaghanta_kala",
          "nakshatra_gandanta", "tithi_gandanta", "lagna_gandanta")
_EXCLUDED = (
    "weekday_tithi_and_rashi_tyajya", "abhukta_mula",
    "angular_gandanta_variants", "strength_aspect_navamsa_parihara",
    "universal_auspicious_yoga_override", "ritual_performance",
    "complete_twenty_one_dosha_catalogue", "purpose_suitability",
)
_CITATIONS = {
    MC_TABLE: "MC Avasthi 2004, Vivaha 49-51, printed 124-126",
    KP_TABLE: "Kalaprakasika, Iyer 1982, printed 185, main text",
    KP_DUAL_TABLE: "Kalaprakasika, Iyer 1982, printed 185, main text and footnote",
    FIXED_WIDTH: "MC Avasthi 2004, Vivaha 51 commentary and Rohini example, printed 125-126",
    SCALED_WIDTH: "Declared proportional-sixtieths interpretation of nominal ghatis; VED-009 source record section 3",
    MC_GANDANTA: "MC Avasthi 2004, Vivaha 43, printed 121-122",
    BP_GANDANTA: "BPHS Santhanam II, 92.2-4, printed 1026-1027",
    YAMA_STAR: "MC Avasthi 2004, Shubhashubha 9, printed 5-6",
    YAMA_TIME: "MC Avasthi 2004, Shubhashubha 37 commentary/table, printed 17-18",
    KP_EXEMPT: "Kalaprakasika, Iyer 1982, chapter XXXIV, printed 195",
    MC_NECESSARY: "MC Avasthi 2004, Shubhashubha 37 commentary, printed 18",
    MC_ABHIJIT: "MC Avasthi 2004, Vivaha 43 commentary, printed 122; 52, printed 126",
}


def _choice(name, value, choices):
    if type(value) is not str or value not in choices:
        raise ValueError(f"{name} must be one of {choices}")


def _tuple(name, value, cls, maximum=64):
    if type(value) is not tuple or len(value) > maximum or any(not isinstance(v, cls) for v in value):
        raise ValueError(f"{name} must be an immutable tuple of {cls.__name__}, at most {maximum}")


@dataclass(frozen=True, slots=True)
class MuhurtaDoshaPolicy:
    """Independent source tables, clocks, Gandanta widths and opt-in exceptions."""

    vishanadi_profile: str = MC_TABLE
    vishanadi_clock: str = FIXED_WIDTH
    gandanta_profile: str = MC_GANDANTA
    parihara_profiles: tuple[str, ...] = ()
    ayanamsa_system: str = "Lahiri"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: float = .1
    ghati_seconds: int = field(init=False, default=1440)
    weekday_basis: str = field(init=False, default="Sunday=0; local sunrise-date ownership")
    endpoint_convention: str = field(init=False, default="[start,end); nonzero root bands uncertain")
    cancellation_scope: str = field(init=False, default="selected_profile_and_witness_only")

    def __post_init__(self):
        _choice("vishanadi_profile", self.vishanadi_profile, _TABLES)
        _choice("vishanadi_clock", self.vishanadi_clock, _CLOCKS)
        _choice("gandanta_profile", self.gandanta_profile, _GANDANTAS)
        _tuple("parihara_profiles", self.parihara_profiles, str, 3)
        if len(set(self.parihara_profiles)) != len(self.parihara_profiles):
            raise ValueError("parihara_profiles must not contain duplicates")
        for profile in self.parihara_profiles:
            _choice("parihara profile", profile, _PARIHARAS)
        if type(self.ayanamsa_system) is not str or self.ayanamsa_system not in list_ayanamsa_systems():
            raise ValueError("ayanamsa_system must be an admitted sidereal system")
        NamedMuhurtaPolicy(sunrise_definition=self.sunrise_definition,
                           solver_tolerance_seconds=self.solver_tolerance_seconds)


@dataclass(frozen=True, slots=True)
class DoshaPhaseSpan:
    """A complete, caller-identified nakshatra, tithi or Lagna sign event in UT1."""

    kind: str
    index: int
    interval: ShuddhiInterval

    def __post_init__(self):
        _choice("phase kind", self.kind, ("nakshatra", "tithi", "lagna"))
        _integer("phase index", self.index, 0, {"nakshatra": 26, "tithi": 29, "lagna": 11}[self.kind])
        if not isinstance(self.interval, ShuddhiInterval):
            raise ValueError("phase interval must be ShuddhiInterval")
        if self.interval.start.upper_jd_ut1 >= self.interval.end.lower_jd_ut1:
            raise ValueError("complete phase event requires separated endpoint brackets")


@dataclass(frozen=True, slots=True)
class MuhurtaDoshaInputs:
    """Sidereal positions and optional complete event/solar evidence for one instant."""

    sun_sidereal_longitude: float
    moon_sidereal_longitude: float
    jd_ut1: float
    weekday: int | None = None
    lagna_sidereal_longitude: float | None = None
    phase_spans: tuple[DoshaPhaseSpan, ...] = ()
    sunrise_day: ShuddhiInterval | None = None
    sunset: ShuddhiBoundary | None = None
    necessary_activity: bool | None = None

    def __post_init__(self):
        _longitude("sun_sidereal_longitude", self.sun_sidereal_longitude)
        _longitude("moon_sidereal_longitude", self.moon_sidereal_longitude)
        jd = _number("jd_ut1", self.jd_ut1)
        if self.weekday is not None:
            _integer("weekday", self.weekday, 0, 6)
        if self.lagna_sidereal_longitude is not None:
            _longitude("lagna_sidereal_longitude", self.lagna_sidereal_longitude)
        if self.necessary_activity is not None and type(self.necessary_activity) is not bool:
            raise ValueError("necessary_activity must be a boolean or None")
        _tuple("phase_spans", self.phase_spans, DoshaPhaseSpan)
        indices = {"nakshatra": _sector(self.moon_sidereal_longitude, 27),
                   "tithi": _sector((self.moon_sidereal_longitude-self.sun_sidereal_longitude) % 360, 30),
                   "lagna": None if self.lagna_sidereal_longitude is None else _sector(self.lagna_sidereal_longitude, 12)}
        for kind, count in (("nakshatra", 27), ("tithi", 30), ("lagna", 12)):
            spans = [s for s in self.phase_spans if s.kind == kind]
            for a, b in zip(spans, spans[1:]):
                if a.interval.end != b.interval.start or b.index != (a.index+1) % count:
                    raise ValueError(f"{kind} spans must be ordered, contiguous, consecutive events")
            if spans and not any(s.interval.contains(jd) is not False for s in spans):
                raise ValueError(f"{kind} spans must cover jd_ut1")
            if spans and indices[kind] is not None and not any(
                s.index == indices[kind] and s.interval.contains(jd) is not False for s in spans
            ):
                raise ValueError(f"{kind} spans must include the supplied longitude's possible parent")
            for span in spans:
                if span.interval.contains(jd) is True and indices[kind] is not None and span.index != indices[kind]:
                    raise ValueError(f"{kind} event index disagrees with the supplied longitude")
        if self.sunrise_day is not None:
            if not isinstance(self.sunrise_day, ShuddhiInterval) or self.sunrise_day.end.jd_ut1-self.sunrise_day.start.jd_ut1 > 2:
                raise ValueError("sunrise_day must be a typed interval at most two days")
            if self.sunrise_day.contains(jd) is False:
                raise ValueError("sunrise_day must contain jd_ut1")
        if self.sunset is not None:
            if not isinstance(self.sunset, ShuddhiBoundary) or self.sunrise_day is None:
                raise ValueError("sunset requires a typed sunrise_day")
            if not (self.sunrise_day.start.upper_jd_ut1 < self.sunset.lower_jd_ut1
                    <= self.sunset.upper_jd_ut1 < self.sunrise_day.end.lower_jd_ut1):
                raise ValueError("sunset must lie strictly between the two sunrise brackets")


@dataclass(frozen=True, slots=True)
class DoshaWitness:
    """A raw restriction window and parent identity, preserved after neutralization."""

    label: str
    parent_index: int | None
    window: ShuddhiInterval | None
    unclipped_window: ShuddhiInterval | None
    detected: bool | None

    def __post_init__(self):
        if self.detected is not None and type(self.detected) is not bool:
            raise ValueError("witness detected must be boolean or None")
        if self.parent_index is not None:
            _integer("parent_index", self.parent_index, 0, 29)
        for window in (self.window, self.unclipped_window):
            if window is not None and not isinstance(window, ShuddhiInterval):
                raise ValueError("witness windows must be typed")


@dataclass(frozen=True, slots=True)
class DoshaPredicate:
    """One named exception prerequisite with a nullable truth value and explanation."""

    name: str
    satisfied: bool | None
    evidence: str

    def __post_init__(self):
        if type(self.name) is not str or not self.name or type(self.evidence) is not str or not self.evidence:
            raise ValueError("predicate name and evidence must be nonempty strings")
        if self.satisfied is not None and type(self.satisfied) is not bool:
            raise ValueError("predicate satisfied must be boolean or None")


@dataclass(frozen=True, slots=True)
class PariharaEvidence:
    """A selected or excluded exception evaluated against one retained witness."""

    profile: str
    witness_index: int
    state: str
    prerequisites: tuple[DoshaPredicate, ...]
    window: ShuddhiInterval | None
    citations: tuple[str, ...]

    def __post_init__(self):
        _choice("parihara profile", self.profile, _PARIHARAS)
        _integer("witness_index", self.witness_index, 0, 127)
        _choice("parihara state", self.state, ("not_selected", "excluded", "not_applicable",
                "not_satisfied", "unavailable", "uncertain", "applied"))
        _tuple("prerequisites", self.prerequisites, DoshaPredicate, 8)
        if self.window is not None and not isinstance(self.window, ShuddhiInterval):
            raise ValueError("parihara window must be typed")
        if self.state == "applied" and (not self.prerequisites or any(p.satisfied is not True for p in self.prerequisites)):
            raise ValueError("applied parihara requires every prerequisite to be affirmative")


@dataclass(frozen=True, slots=True)
class MuhurtaDoshaFinding:
    """Independent detection and neutralization with all source and temporal evidence."""

    rule_id: str
    profile: str
    citations: tuple[str, ...]
    state: str
    detected: bool | None
    neutralized: bool | None
    witnesses: tuple[DoshaWitness, ...]
    parihara: tuple[PariharaEvidence, ...]
    unavailable_reasons: tuple[str, ...] = ()

    def __post_init__(self):
        _choice("rule_id", self.rule_id, _RULES)
        _choice("finding state", self.state, ("clear", "detected", "neutralized", "uncertain", "unavailable"))
        for value in (self.detected, self.neutralized):
            if value is not None and type(value) is not bool:
                raise ValueError("finding truth values must be boolean or None")
        _tuple("witnesses", self.witnesses, DoshaWitness, 128)
        _tuple("parihara", self.parihara, PariharaEvidence, 128)
        if self.neutralized is True and self.detected is not True:
            raise ValueError("neutralization must preserve an affirmative detected condition")
        expected = "neutralized" if self.neutralized is True else "detected" if self.detected is True else "clear" if self.detected is False else None
        if expected is not None and self.state != expected:
            raise ValueError("finding state disagrees with independent truth values")
        if any(p.witness_index >= len(self.witnesses) for p in self.parihara):
            raise ValueError("parihara must reference a retained witness")


@dataclass(frozen=True, slots=True)
class MuhurtaDoshaAssessment:
    """Six ordered findings under an explicit policy without an overall election score."""

    policy: MuhurtaDoshaPolicy
    inputs: MuhurtaDoshaInputs
    findings: tuple[MuhurtaDoshaFinding, ...]
    excluded_rules: tuple[str, ...] = _EXCLUDED
    input_basis: str = "caller_supplied_sidereal_and_ut1; event_identity_caller_owned"
    activity_suitability: str = field(init=False, default="not_evaluated")

    def __post_init__(self):
        if not isinstance(self.policy, MuhurtaDoshaPolicy) or not isinstance(self.inputs, MuhurtaDoshaInputs):
            raise ValueError("assessment requires typed policy and inputs")
        _tuple("findings", self.findings, MuhurtaDoshaFinding, 6)
        if tuple(f.rule_id for f in self.findings) != _RULES:
            raise ValueError("assessment requires all six findings in canonical order")


@dataclass(frozen=True, slots=True)
class DoshaCatalogueEntry:
    """One supported profile with its precise role and source attribution."""

    profile: str
    kind: str
    citations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MuhurtaDoshaCatalogue:
    """Finite profile inventory and deliberately excluded wider Muhurta rules."""

    profiles: tuple[DoshaCatalogueEntry, ...]
    rules: tuple[str, ...] = _RULES
    excluded_rules: tuple[str, ...] = _EXCLUDED


def muhurta_dosha_catalogue():
    """Discover supported source tables, clocks, detection and cancellation profiles."""
    groups = (("vishanadi_table", _TABLES), ("vishanadi_clock", _CLOCKS),
              ("gandanta", _GANDANTAS), ("yamaghanta", (YAMA_STAR, YAMA_TIME)),
              ("parihara", _PARIHARAS))
    return MuhurtaDoshaCatalogue(tuple(DoshaCatalogueEntry(p, kind, (_CITATIONS[p],))
                                      for kind, profiles in groups for p in profiles))


def _affine(a, b, fraction, kind):
    """Positive affine endpoint arithmetic propagates numerical brackets."""
    return ShuddhiBoundary(kind, a.jd_ut1+(b.jd_ut1-a.jd_ut1)*fraction,
        a.lower_jd_ut1+(b.lower_jd_ut1-a.lower_jd_ut1)*fraction,
        a.upper_jd_ut1+(b.upper_jd_ut1-a.upper_jd_ut1)*fraction)


def _shift(boundary, days, kind):
    return ShuddhiBoundary(kind, boundary.jd_ut1+days,
                          boundary.lower_jd_ut1+days, boundary.upper_jd_ut1+days)


def _solar_window(inputs, low, high, kind):
    if inputs.sunrise_day is None or inputs.sunset is None:
        return None
    return ShuddhiInterval(_affine(inputs.sunrise_day.start, inputs.sunset, low, kind+"_start"),
                           _affine(inputs.sunrise_day.start, inputs.sunset, high, kind+"_end"))


def _clip(raw, parent):
    # Endpoint-wise maxima/minima propagate uncertain clipping boundaries.
    def edge(a, b, fn):
        return ShuddhiBoundary(a.kind+"_clipped", fn(a.jd_ut1, b.jd_ut1),
            fn(a.lower_jd_ut1, b.lower_jd_ut1), fn(a.upper_jd_ut1, b.upper_jd_ut1))
    return ShuddhiInterval(edge(raw.start, parent.start, max), edge(raw.end, parent.end, min))


def _witness(label, parent, window, jd, raw=None):
    return DoshaWitness(label, parent, window, window if raw is None else raw,
                        None if window is None else window.contains(jd))


def _parihara(rule, profile, witness, index, inputs, active):
    candidate = KP_EXEMPT if rule == "vishanadi" else MC_NECESSARY if rule == "yamaghanta_kala" else MC_ABHIJIT if rule.endswith("gandanta") else None
    if candidate is None:
        return None
    if candidate not in active.parihara_profiles:
        return PariharaEvidence(candidate, index, "not_selected", (), None, (_CITATIONS[candidate],))
    scope = profile in (KP_TABLE, KP_DUAL_TABLE) if candidate == KP_EXEMPT else profile == MC_GANDANTA if candidate == MC_ABHIJIT else True
    predicates = [DoshaPredicate("source_scope", scope, "exception applies only to its named detection source")]
    window = None
    if candidate == KP_EXEMPT:
        predicates.append(DoshaPredicate("parent_star_exempt", None if witness.parent_index is None else witness.parent_index in _EXEMPT_STARS,
                                        f"parent nakshatra index={witness.parent_index}; KP printed 195"))
    elif candidate == MC_NECESSARY:
        predicates.append(DoshaPredicate("necessary_activity", inputs.necessary_activity, "caller-declared necessary activity; never inferred"))
        if witness.window is not None:
            window = ShuddhiInterval(witness.window.start, _affine(witness.window.start, witness.window.end, .5, "necessary_half_end"))
        predicates.append(DoshaPredicate("first_half", None if window is None else window.contains(inputs.jd_ut1), "first temporal half of the daytime fault"))
    else:
        window = _solar_window(inputs, 7/15, 8/15, "abhijit")
        predicates.append(DoshaPredicate("abhijit_geometry", None if window is None else window.contains(inputs.jd_ut1), "eighth of fifteen daylight divisions; separate weekday eligibility unchanged"))
    values = tuple(p.satisfied for p in predicates)
    if not scope:
        state = "excluded"
    elif witness.detected is False:
        state = "not_applicable"
    elif False in values:
        state = "not_satisfied"
    elif None in values:
        missing = (candidate == KP_EXEMPT and witness.parent_index is None
                   or candidate == MC_NECESSARY and inputs.necessary_activity is None
                   or candidate != KP_EXEMPT and window is None)
        state = "unavailable" if missing else "uncertain"
    else:
        state = "uncertain" if witness.detected is None else "applied"
    return PariharaEvidence(candidate, index, state, tuple(predicates), window, (_CITATIONS[candidate],))


def _finding(rule, profile, witnesses, inputs, active, reasons=(), extra_citations=()):
    witnesses = tuple(witnesses)
    evidence = tuple(p for i, w in enumerate(witnesses)
                     if (p := _parihara(rule, profile, w, i, inputs, active)) is not None)
    detected = True if any(w.detected is True for w in witnesses) else None if reasons or any(w.detected is None for w in witnesses) else False
    neutralized = False if detected is False else None
    if detected is True:
        outcomes = []
        for i, witness in enumerate(witnesses):
            if witness.detected is False:
                continue
            p = next((p for p in evidence if p.witness_index == i), None)
            outcomes.append(True if p is not None and p.state == "applied" else None if witness.detected is None or (p is not None and p.state in ("unavailable", "uncertain")) else False)
        if reasons:
            outcomes.append(None)
        neutralized = False if False in outcomes else None if None in outcomes else True
    state = "neutralized" if neutralized is True else "detected" if detected is True else "clear" if detected is False else "unavailable" if reasons else "uncertain"
    return MuhurtaDoshaFinding(rule, profile, (_CITATIONS[profile], *extra_citations), state,
                               detected, neutralized, witnesses, evidence, tuple(reasons))


def detect_muhurta_doshas(sun_sidereal_longitude, moon_sidereal_longitude, *, jd_ut1,
        weekday=None, lagna_sidereal_longitude=None, phase_spans=(), sunrise_day=None,
        sunset=None, necessary_activity=None, policy=None):
    """Assess six named rules using explicit sidereal positions and UT1 witnesses.

    Complete event spans retain their zero-based indices. Fixed-width Vishanadi
    needs preceding coverage for carryover; missing evidence never means clear.
    Selected exceptions affect only their documented rule and source profile.
    """
    active = MuhurtaDoshaPolicy() if policy is None else policy
    if not isinstance(active, MuhurtaDoshaPolicy):
        raise ValueError("policy must be MuhurtaDoshaPolicy")
    inputs = MuhurtaDoshaInputs(sun_sidereal_longitude, moon_sidereal_longitude,
        jd_ut1, weekday, lagna_sidereal_longitude, phase_spans, sunrise_day, sunset, necessary_activity)
    jd = float(jd_ut1)
    spans = {kind: tuple(s for s in phase_spans if s.kind == kind) for kind in ("nakshatra", "tithi", "lagna")}
    star = _sector(moon_sidereal_longitude, 27)
    tithi = _sector((moon_sidereal_longitude-sun_sidereal_longitude) % 360, 30)
    lagna = None if lagna_sidereal_longitude is None else _sector(lagna_sidereal_longitude, 12)
    witnesses = []
    for span in spans["nakshatra"]:
        offsets = (_OFFSETS[span.index],)
        if active.vishanadi_profile != MC_TABLE:
            if span.index == 24:
                offsets = (6,)
            elif span.index == 18:
                offsets = (20, 56) if active.vishanadi_profile == KP_DUAL_TABLE else (20,)
        for offset in offsets:
            start = _affine(span.interval.start, span.interval.end, offset/60, "vishanadi_start")
            end = _shift(start, 4/60, "vishanadi_end") if active.vishanadi_clock == FIXED_WIDTH else _affine(span.interval.start, span.interval.end, (offset+4)/60, "vishanadi_end")
            witnesses.append(_witness(f"nakshatra_{span.index}_offset_{offset}", span.index, ShuddhiInterval(start, end), jd))
    reasons = []
    if not spans["nakshatra"]:
        reasons.append("complete_nakshatra_span_missing")
    elif active.vishanadi_clock == FIXED_WIDTH and spans["nakshatra"][0].interval.start.upper_jd_ut1 > jd-4/60:
        reasons.append("preceding_nakshatra_carryover_context_missing")
    findings = [_finding("vishanadi", active.vishanadi_profile, witnesses or [DoshaWitness("parent_unavailable", None, None, None, None)],
                        inputs, active, reasons, (_CITATIONS[active.vishanadi_clock],))]
    current_star = next((s.interval for s in spans["nakshatra"] if s.index == star and s.interval.contains(jd) is not False), None)
    yama = None if weekday is None else star == _YAMA_STARS[weekday]
    if weekday is not None and any(s.index == _YAMA_STARS[weekday] and s.interval.contains(jd) is None for s in spans["nakshatra"]):
        yama = None
    findings.append(_finding("yamaghanta_yoga", YAMA_STAR,
        [DoshaWitness("weekday_nakshatra_pair", star, current_star, current_star, yama)], inputs, active,
        ("weekday_missing",) if weekday is None else ()))
    ordinal = None if weekday is None else 2*((4-weekday) % 7+1)
    window = None if ordinal is None else _solar_window(inputs, (ordinal-1)/16, ordinal/16, "yamaghanta_kala")
    findings.append(_finding("yamaghanta_kala", YAMA_TIME, [_witness("daylight_sixteenth", None, window, jd)], inputs, active,
        ("weekday_or_solar_anchors_missing",) if window is None else ()))
    for kind, index, first, last, width in (
        ("nakshatra", star, (0, 9, 18), (8, 17, 26), 2/60),
        ("tithi", tithi, (0, 5, 10, 15, 20, 25), (4, 9, 14, 19, 24, 29), (1 if active.gandanta_profile == MC_GANDANTA else 2)/60),
        ("lagna", lagna, (0, 4, 8), (3, 7, 11), .5/60),
    ):
        witnesses, reasons = [], []
        for span in spans[kind]:
            if span.index in first:
                raw = ShuddhiInterval(span.interval.start, _shift(span.interval.start, width, kind+"_gandanta_end"))
            elif span.index in last:
                raw = ShuddhiInterval(_shift(span.interval.end, -width, kind+"_gandanta_start"), span.interval.end)
            else:
                continue
            witnesses.append(_witness(kind+"_edge", span.index, _clip(raw, span.interval), jd, raw))
        if index is None:
            reasons.append("lagna_longitude_missing")
        elif not spans[kind] and index in (*first, *last):
            reasons.append("complete_"+kind+"_span_missing")
        if reasons and not witnesses:
            witnesses.append(DoshaWitness(kind+"_edge_unavailable", index, None, None, None))
        findings.append(_finding(kind+"_gandanta", active.gandanta_profile, witnesses, inputs, active, reasons))
    return MuhurtaDoshaAssessment(active, inputs, tuple(findings))


@dataclass(frozen=True, slots=True)
class MuhurtaDoshaCell:
    """An interval whose detection and cancellation states are constant off root bands."""

    interval: ShuddhiInterval
    assessment: MuhurtaDoshaAssessment

    def __post_init__(self):
        if not isinstance(self.interval, ShuddhiInterval) or not isinstance(self.assessment, MuhurtaDoshaAssessment):
            raise ValueError("cell interval and assessment must be typed")


@dataclass(frozen=True, slots=True)
class MuhurtaDoshaDay:
    """A sunrise-owned day of dosha cells with explicit unavailable components."""

    local_date: date
    timezone: str
    latitude: float
    longitude: float
    policy: MuhurtaDoshaPolicy
    status: str
    unavailable_reasons: tuple[str, ...]
    sunrise: ShuddhiBoundary | None
    next_sunrise: ShuddhiBoundary | None
    sunset: ShuddhiBoundary | None
    cells: tuple[MuhurtaDoshaCell, ...]
    transition_bands: tuple[ShuddhiBoundary, ...]
    kernel_label: str
    reader_binding: str
    activity_suitability: str = field(init=False, default="not_evaluated")

    def __post_init__(self):
        if type(self.local_date) is not date or not isinstance(self.policy, MuhurtaDoshaPolicy):
            raise ValueError("day requires typed date and policy")
        _choice("day status", self.status, ("available", "partial", "unavailable"))
        _tuple("cells", self.cells, MuhurtaDoshaCell, 511)
        _tuple("transition_bands", self.transition_bands, ShuddhiBoundary, 512)
        if bool(self.cells) != (self.status != "unavailable") or bool(self.unavailable_reasons) != (self.status != "available"):
            raise ValueError("day availability must agree with cells and reasons")
        if any(c.assessment.policy != self.policy for c in self.cells):
            raise ValueError("day cells must use the same policy")
        if any(a.interval.end != b.interval.start for a, b in zip(self.cells, self.cells[1:])):
            raise ValueError("day cells must be contiguous at their uncertainty bands")

    def at(self, jd_ut1):
        """Return a representative cell assessment, or None outside/in a root band."""
        jd = _number("jd_ut1", jd_ut1)
        if any(b.lower_jd_ut1 < b.upper_jd_ut1 and b.lower_jd_ut1 <= jd <= b.upper_jd_ut1 for b in self.transition_bands):
            return None
        return next((c.assessment for c in self.cells if c.interval.contains(jd) is True), None)


def muhurta_doshas_for_date(local_date, latitude, longitude, *, timezone,
                          necessary_activity=None, policy=None, reader=None):
    """Compose bounded exact-transition cells for one local sunrise-owned day."""
    from ._muhurta_dosha_day import calculate_day
    return calculate_day(local_date, latitude, longitude, timezone=timezone,
        necessary_activity=necessary_activity, policy=policy, reader=reader)
