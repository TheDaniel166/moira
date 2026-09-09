"""Planet-first concentration evidence under the named moira.stellium.v1 policy.

This product owns a *set of selected canonical planets* satisfying a sign,
house, or bounded circular-arc criterion. It is not an aspect-edge pattern or
an interpretive strength measure. Strict (four) and Broad (three) are explicit
Moira policies, not assertions of a universal historical definition.

Positions are already expressed in the declared zodiac. Offset metadata is a
receipt, not an instruction to rotate them again. House membership delegates
to ``assign_house`` only after its geometry and longitude frame are admitted.
The tight criterion follows the geometry of the shortest enclosing circular
arc: its complement is a largest empty gap. Non-core factors are inspected
only after each planetary match and its arc have been frozen.

The older centroid/clique detectors in patterns/aspects are intentionally
unchanged. No kernel, ephemeris calculation, UI state or aspect score is used.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import combinations
import json
import math

from .constants import Body, SIGNS
from .houses import HouseCusps, assign_house, classify_house_system


STELLIUM_SCHEMA_VERSION = "moira.stellium.v1"
STELLIUM_CORE = tuple(Body.ALL_PLANETS)
_CRITERIA = ("sign", "house", "tight")
_ZODIACS = ("tropical", "sidereal", "draconic")
_MAX_POSITIONS = 256
_ALIASES = {
    name.casefold(): name
    for name in (
        *STELLIUM_CORE,
        *Body.ALL_POINTS,
        "Chiron",
        "Fortune",
        "Spirit",
        "North Node",
        "South Node",
        "Asc",
        "MC",
        "DSC",
        "IC",
        "Vertex",
        "Anti-Vertex",
    )
}
_ALIASES.update(
    {"ascendant": "Asc", "asc": "Asc", "midheaven": "MC", "mean lilith": "Lilith"}
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: float, label: str) -> float:
    _require(
        not isinstance(value, bool) and isinstance(value, (int, float)),
        f"{label} must be a finite number",
    )
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    _require(math.isfinite(result), f"{label} must be a finite number")
    return result


def _identity(value: str) -> str:
    _require(
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and len(value) <= 128,
        "body identities must be non-empty trimmed strings of at most 128 characters",
    )
    return _ALIASES.get(value.casefold(), value)


def _identities(values: tuple[str, ...], *, core: bool) -> tuple[str, ...]:
    _require(
        isinstance(values, (tuple, list)) and len(values) <= _MAX_POSITIONS,
        "selection must be a bounded sequence",
    )
    names = tuple(_identity(value) for value in values)
    _require(len(set(names)) == len(names), "duplicate canonical body in selection")
    if core:
        _require(
            all(name in STELLIUM_CORE for name in names),
            "only the canonical ten planets may be selected as core",
        )
        return tuple(name for name in STELLIUM_CORE if name in names)
    _require(
        all(name not in STELLIUM_CORE for name in names),
        "core planets cannot be selected as associated factors",
    )
    return tuple(sorted(names))


def _digest(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class StelliumAnalysisPolicy:
    """Independent count and geometry policy; no legacy orb-factor scaling."""

    preset: str = "strict"
    max_span_degrees: float = 8.0
    criteria: tuple[str, ...] = _CRITERIA

    def __post_init__(self) -> None:
        _require(
            self.preset in ("strict", "broad"),
            "stellium preset must be strict or broad",
        )
        span = _number(self.max_span_degrees, "max_span_degrees")
        _require(0 <= span < 180, "max_span_degrees must be in [0, 180)")
        _require(
            isinstance(self.criteria, (tuple, list)) and bool(self.criteria),
            "criteria must be a non-empty sequence",
        )
        _require(
            all(c in _CRITERIA for c in self.criteria)
            and len(set(self.criteria)) == len(self.criteria),
            "criteria must be unique sign, house or tight values",
        )
        object.__setattr__(self, "max_span_degrees", span)
        object.__setattr__(
            self, "criteria", tuple(c for c in _CRITERIA if c in self.criteria)
        )

    @property
    def min_planets(self) -> int:
        return 4 if self.preset == "strict" else 3


@dataclass(frozen=True, slots=True)
class StelliumContext:
    """Source receipt for already transformed ecliptic longitudes."""

    source_id: str = "provided_positions"
    zodiac: str = "tropical"
    zodiac_offset_degrees: float = 0.0
    ayanamsa: str | None = None
    coordinate_regime: str = "unspecified"

    def __post_init__(self) -> None:
        for label in ("source_id", "coordinate_regime"):
            value = getattr(self, label)
            _require(
                isinstance(value, str) and bool(value.strip()) and len(value) <= 256,
                f"{label} must be a non-empty bounded string",
            )
        _require(self.zodiac in _ZODIACS, "unsupported zodiac frame")
        offset = _number(self.zodiac_offset_degrees, "zodiac_offset_degrees")
        _require(
            -360 < offset < 360, "zodiac offset must lie between -360 and 360 degrees"
        )
        _require(
            self.zodiac != "tropical" or offset == 0,
            "tropical context cannot carry a zodiac offset",
        )
        _require(
            self.ayanamsa is None
            or (
                isinstance(self.ayanamsa, str)
                and bool(self.ayanamsa.strip())
                and len(self.ayanamsa) <= 128
            ),
            "ayanamsa must be a non-empty bounded name when supplied",
        )
        object.__setattr__(self, "zodiac_offset_degrees", offset)


@dataclass(frozen=True, slots=True)
class StelliumSelection:
    """Explicit counting-planet and non-counting associated-factor selection."""

    core: tuple[str, ...] = STELLIUM_CORE
    associated: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "core", _identities(self.core, core=True))
        object.__setattr__(self, "associated", _identities(self.associated, core=False))


@dataclass(frozen=True, slots=True)
class StelliumHouseContext:
    """An admitted circular house partition in the same frame as positions."""

    houses: HouseCusps
    longitude_frame: str = "tropical"

    def __post_init__(self) -> None:
        _require(
            isinstance(self.houses, HouseCusps),
            "houses must be an engine HouseCusps vessel",
        )
        _require(self.longitude_frame in _ZODIACS, "unsupported house longitude frame")
        h = self.houses
        h.__post_init__()
        _require(bool(h.effective_system), "effective house system must be declared")
        _require(
            h.classification == classify_house_system(h.effective_system),
            "house classification disagrees with effective system",
        )
        for field in ("asc", "mc", "armc", "east_point", "vertex", "anti_vertex"):
            value = getattr(h, field)
            if value is not None:
                _require(
                    0 <= _number(value, f"house {field}") < 360,
                    f"house {field} must be normalized",
                )
        _require(len(h.cusps) == 12, "house context must contain twelve cusps")
        cusps = tuple(_number(c, "house cusp") for c in h.cusps)
        _require(
            all(0 <= c < 360 for c in cusps) and len(set(cusps)) == 12,
            "house cusps must be distinct normalized longitudes",
        )
        # A lawful twelve-house partition winds once, not twice or backwards.
        winding = sum((cusps[(i + 1) % 12] - c) % 360 for i, c in enumerate(cusps))
        _require(
            math.isclose(winding, 360.0, rel_tol=0, abs_tol=1e-8),
            "house cusps must partition one circular revolution",
        )
        if h.boundary_geometry is not None:
            for boundary in h.boundary_geometry.boundaries:
                residual = (
                    boundary.cusp_longitude - cusps[boundary.house - 1] + 180
                ) % 360 - 180
                _require(
                    math.isclose(residual, 0, rel_tol=0, abs_tol=1e-9),
                    "spatial boundary and house cusp evidence disagree",
                )


@dataclass(frozen=True, slots=True)
class StelliumArc:
    """Shortest enclosing core arc; inclusive endpoints and total span in degrees."""

    start: float
    end: float
    span: float
    wraps: bool

    def __post_init__(self) -> None:
        _require(
            all(0 <= _number(v, "arc endpoint") < 360 for v in (self.start, self.end)),
            "arc endpoints must be normalized finite longitudes",
        )
        _require(
            0 <= _number(self.span, "arc span") < 180,
            "tight arc span must be below 180 degrees",
        )
        _require(
            math.isclose(
                (self.end - self.start) % 360, self.span, rel_tol=0, abs_tol=1e-12
            ),
            "arc endpoint and span evidence disagree",
        )
        _require(
            type(self.wraps) is bool
            and self.wraps == (self.span > 0 and self.end < self.start),
            "arc wrap evidence disagrees",
        )


@dataclass(frozen=True, slots=True)
class StelliumAssociation:
    """Explicitly selected non-core evidence; never part of the qualifying count."""

    body: str
    longitude: float

    def __post_init__(self) -> None:
        _require(
            _identity(self.body) == self.body and self.body not in STELLIUM_CORE,
            "association must name a canonical non-core factor",
        )
        _require(
            0 <= _number(self.longitude, "association longitude") < 360,
            "association longitude must be normalized",
        )


@dataclass(frozen=True, slots=True)
class StelliumMatch:
    """One independent criterion and its own non-counting associations."""

    id: str
    criterion: str
    sign_index: int | None = None
    sign_name: str | None = None
    house: int | None = None
    arc: StelliumArc | None = None
    associations: tuple[StelliumAssociation, ...] = ()

    def __post_init__(self) -> None:
        _require(
            bool(self.id) and self.criterion in _CRITERIA,
            "invalid stellium match identity/criterion",
        )
        if self.criterion == "sign":
            _require(
                type(self.sign_index) is int
                and 0 <= self.sign_index < 12
                and self.sign_name == SIGNS[self.sign_index],
                "sign match identity disagrees",
            )
        else:
            _require(
                self.sign_index is None and self.sign_name is None,
                "non-sign match cannot carry a sign bucket",
            )
        _require(
            (type(self.house) is int and 1 <= self.house <= 12)
            if self.criterion == "house"
            else self.house is None,
            "house match identity disagrees",
        )
        _require(
            isinstance(self.arc, StelliumArc)
            if self.criterion == "tight"
            else self.arc is None,
            "tight match requires only its own arc evidence",
        )
        _require(
            isinstance(self.associations, (tuple, list))
            and all(isinstance(a, StelliumAssociation) for a in self.associations),
            "invalid match associations",
        )
        object.__setattr__(self, "associations", tuple(self.associations))
        _require(
            len({a.body for a in self.associations}) == len(self.associations),
            "duplicate match association",
        )


@dataclass(frozen=True, slots=True)
class StelliumGroup:
    """One canonical core membership with all its independent matches."""

    id: str
    core_members: tuple[str, ...]
    core_count: int
    matches: tuple[StelliumMatch, ...]

    def __post_init__(self) -> None:
        _require(
            bool(self.id)
            and self.core_members == _identities(self.core_members, core=True),
            "invalid core group identity/order",
        )
        _require(
            type(self.core_count) is int
            and self.core_count == len(self.core_members)
            and self.core_count >= 3,
            "group core count disagrees",
        )
        _require(
            isinstance(self.matches, (tuple, list))
            and all(isinstance(m, StelliumMatch) for m in self.matches),
            "invalid group matches",
        )
        object.__setattr__(self, "matches", tuple(self.matches))
        _require(
            bool(self.matches)
            and len({m.criterion for m in self.matches}) == len(self.matches),
            "group requires unique criterion matches",
        )


@dataclass(frozen=True, slots=True)
class StelliumEvaluation:
    """Criterion-level distinction between no match, missing data and no request."""

    criterion: str
    status: str
    reason: str | None = None

    def __post_init__(self) -> None:
        _require(
            self.criterion in _CRITERIA
            and self.status
            in ("evaluated", "partial", "not_evaluable", "not_requested"),
            "invalid criterion evaluation",
        )
        _require(
            self.status not in ("partial", "not_evaluable") or bool(self.reason),
            "incomplete evaluation needs a reason",
        )


@dataclass(frozen=True, slots=True)
class StelliumCoverage:
    """Selected, available, missing and intentionally excluded snapshot identities."""

    requested_core: tuple[str, ...]
    computed_core: tuple[str, ...]
    missing_core: tuple[str, ...]
    missing_associated: tuple[str, ...]
    excluded: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("requested_core", "computed_core", "missing_core"):
            object.__setattr__(
                self, field, _identities(getattr(self, field), core=True)
            )
        object.__setattr__(
            self, "missing_associated", _identities(self.missing_associated, core=False)
        )
        object.__setattr__(self, "excluded", tuple(self.excluded))
        _require(
            len(set(self.excluded)) == len(self.excluded)
            and all(_identity(n) == n for n in self.excluded),
            "invalid excluded identities",
        )
        _require(
            not (set(self.computed_core) & set(self.missing_core))
            and set(self.requested_core)
            == set(self.computed_core) | set(self.missing_core),
            "core coverage partition disagrees",
        )


@dataclass(frozen=True, slots=True)
class StelliumHouseReceipt:
    """Requested/effective system and fallback truth for the admitted snapshot."""

    requested_system: str
    effective_system: str
    fallback: bool
    fallback_reason: str | None
    longitude_frame: str


@dataclass(frozen=True, slots=True)
class StelliumAnalysis:
    """Versioned, deterministic evidence without aspect edges or strength scoring."""

    schema_version: str
    input_fingerprint: str
    status: str
    policy: StelliumAnalysisPolicy
    context: StelliumContext
    coverage: StelliumCoverage
    evaluations: tuple[StelliumEvaluation, ...]
    houses: StelliumHouseReceipt | None
    groups: tuple[StelliumGroup, ...]

    def __post_init__(self) -> None:
        _require(
            self.schema_version == STELLIUM_SCHEMA_VERSION
            and bool(self.input_fingerprint),
            "invalid stellium analysis identity",
        )
        _require(
            self.status in ("complete", "partial", "not_evaluable"),
            "invalid analysis status",
        )
        _require(
            isinstance(self.policy, StelliumAnalysisPolicy)
            and isinstance(self.context, StelliumContext)
            and isinstance(self.coverage, StelliumCoverage),
            "invalid analysis receipts",
        )
        object.__setattr__(self, "evaluations", tuple(self.evaluations))
        object.__setattr__(self, "groups", tuple(self.groups))
        _require(
            tuple(e.criterion for e in self.evaluations) == _CRITERIA,
            "analysis must report each criterion's evaluation",
        )
        _require(
            all(
                (e.status != "not_requested") == (e.criterion in self.policy.criteria)
                for e in self.evaluations
            ),
            "criterion evaluation disagrees with policy",
        )
        requested = tuple(e for e in self.evaluations if e.status != "not_requested")
        expected_status = (
            "not_evaluable"
            if all(e.status == "not_evaluable" for e in requested)
            else "partial"
            if any(e.status != "evaluated" for e in requested)
            else "complete"
        )
        _require(
            self.status == expected_status, "analysis status disagrees with evaluations"
        )
        _require(
            len({g.core_members for g in self.groups}) == len(self.groups),
            "duplicate core group membership",
        )
        _require(
            all(
                g.core_count >= self.policy.min_planets
                and set(g.core_members) <= set(self.coverage.computed_core)
                for g in self.groups
            ),
            "group does not satisfy the resolved policy/coverage",
        )
        evaluable = {
            e.criterion
            for e in self.evaluations
            if e.status in ("evaluated", "partial")
        }
        _require(
            all(m.criterion in evaluable for g in self.groups for m in g.matches),
            "match admitted for an unevaluable criterion",
        )


def _core_arc(longitudes: tuple[float, ...]) -> tuple[float, float, float]:
    ordered = sorted(longitudes)
    # Sort ties by the next start longitude; body/input order cannot pick a branch.
    gaps = [
        (
            ordered[(i + 1) % len(ordered)]
            + (360 if i == len(ordered) - 1 else 0)
            - lon,
            ordered[(i + 1) % len(ordered)],
        )
        for i, lon in enumerate(ordered)
    ]
    _, start = min(gaps, key=lambda g: (-g[0], g[1]))
    end = max(ordered, key=lambda lon: (lon - start) % 360)
    # Measure from actual endpoints, avoiding 360-gap cancellation at an 8-degree boundary.
    return start, end, (end - start) % 360


def analyze_stelliums(
    positions: Mapping[str, float],
    *,
    policy: StelliumAnalysisPolicy | None = None,
    selection: StelliumSelection | None = None,
    context: StelliumContext | None = None,
    houses: StelliumHouseContext | None = None,
    house_unavailable_reason: str | None = None,
) -> StelliumAnalysis:
    """Analyze a supplied snapshot without calculating astronomy or interpreting it.

    Omitted selection requests all ten core planets, so omitted positions are
    reported as missing rather than silently redefining the roster. Explicit
    selection can lawfully analyze a smaller chosen sky. Unknown non-core
    identities may annotate only when the caller explicitly selects them.
    """
    policy = policy if policy is not None else StelliumAnalysisPolicy()
    selection = selection if selection is not None else StelliumSelection()
    context = context if context is not None else StelliumContext()
    _require(
        isinstance(policy, StelliumAnalysisPolicy)
        and isinstance(selection, StelliumSelection)
        and isinstance(context, StelliumContext),
        "invalid stellium policy, selection or context vessel",
    )
    _require(
        isinstance(positions, Mapping) and len(positions) <= _MAX_POSITIONS,
        "positions must be a mapping of at most 256 objects",
    )
    _require(
        house_unavailable_reason is None
        or (
            isinstance(house_unavailable_reason, str)
            and bool(house_unavailable_reason.strip())
            and len(house_unavailable_reason) <= 512
        ),
        "house unavailable reason must be a non-empty bounded string",
    )
    normalized: dict[str, float] = {}
    for raw_name, longitude in positions.items():
        name = _identity(raw_name)
        _require(name not in normalized, "duplicate canonical body in positions")
        normalized[name] = _number(longitude, f"longitude for {name}") % 360.0
    if houses is not None:
        _require(
            isinstance(houses, StelliumHouseContext), "invalid stellium house context"
        )
        houses.__post_init__()  # The supplied HouseCusps vessel may be mutable.
        _require(
            houses.longitude_frame == context.zodiac,
            "house and position longitude frame mismatch",
        )
        _require(
            house_unavailable_reason is None,
            "available houses cannot carry an unavailable reason",
        )
        if houses.houses.boundary_geometry is not None:
            offset = houses.houses.boundary_geometry.zodiac_offset_deg
            _require(
                math.isclose(
                    offset, context.zodiac_offset_degrees, rel_tol=0, abs_tol=1e-9
                ),
                "house geometry and position zodiac offsets disagree",
            )

    core = tuple(n for n in selection.core if n in normalized)
    associates = tuple(n for n in selection.associated if n in normalized)
    coverage = StelliumCoverage(
        selection.core,
        core,
        tuple(n for n in selection.core if n not in normalized),
        tuple(n for n in selection.associated if n not in normalized),
        tuple(
            sorted(set(normalized) - set(selection.core) - set(selection.associated))
        ),
    )
    incomplete = bool(coverage.missing_core or coverage.missing_associated)
    evaluations = tuple(
        StelliumEvaluation(c, "not_requested")
        if c not in policy.criteria
        else StelliumEvaluation(
            c,
            "not_evaluable",
            house_unavailable_reason or "No valid house context supplied",
        )
        if c == "house" and houses is None
        else StelliumEvaluation(c, "partial", "Some selected positions are missing")
        if incomplete
        else StelliumEvaluation(c, "evaluated")
        for c in _CRITERIA
    )
    house_receipt = (
        None
        if houses is None
        else StelliumHouseReceipt(
            houses.houses.system,
            houses.houses.effective_system,
            houses.houses.fallback,
            houses.houses.fallback_reason,
            houses.longitude_frame,
        )
    )
    position_houses = (
        {}
        if houses is None
        else {
            n: assign_house(normalized[n], houses.houses).house
            for n in (*core, *associates)
        }
    )
    grouped: dict[tuple[str, ...], list[StelliumMatch]] = {}
    group_ids: dict[tuple[str, ...], str] = {}

    def admit(
        members: tuple[str, ...],
        criterion: str,
        *,
        sign_index: int | None = None,
        house: int | None = None,
        arc: StelliumArc | None = None,
    ) -> None:
        group_id = _digest(
            [STELLIUM_SCHEMA_VERSION, asdict(policy), asdict(context), members]
        )
        group_ids[members] = group_id
        selected_associates = tuple(
            StelliumAssociation(n, normalized[n])
            for n in associates
            if (
                int(normalized[n] // 30) == sign_index
                if criterion == "sign"
                else position_houses[n] == house
                if criterion == "house"
                else (normalized[n] - arc.start) % 360 <= arc.span
            )
        )
        match_id = _digest(
            [
                group_id,
                criterion,
                sign_index,
                house,
                asdict(arc) if arc is not None else None,
                asdict(house_receipt) if criterion == "house" else None,
            ]
        )
        grouped.setdefault(members, []).append(
            StelliumMatch(
                match_id,
                criterion,
                sign_index,
                SIGNS[sign_index] if sign_index is not None else None,
                house,
                arc,
                selected_associates,
            )
        )

    for criterion in ("sign", "house"):
        if criterion not in policy.criteria or (
            criterion == "house" and houses is None
        ):
            continue
        buckets: dict[int, list[str]] = {}
        for name in core:
            key = (
                int(normalized[name] // 30)
                if criterion == "sign"
                else position_houses[name]
            )
            buckets.setdefault(key, []).append(name)
        for key, members in sorted(buckets.items()):
            if len(members) >= policy.min_planets:
                admit(
                    tuple(members),
                    criterion,
                    **({"sign_index": key} if criterion == "sign" else {"house": key}),
                )
    if "tight" in policy.criteria:
        maximal: list[frozenset[str]] = []
        for size in range(len(core), policy.min_planets - 1, -1):
            for members in combinations(core, size):
                member_set = frozenset(members)
                if any(member_set < existing for existing in maximal):
                    continue
                start, end, span = _core_arc(tuple(normalized[n] for n in members))
                if span <= policy.max_span_degrees:
                    maximal.append(member_set)
                    admit(
                        members,
                        "tight",
                        arc=StelliumArc(start, end, span, span > 0 and end < start),
                    )
    groups = tuple(
        StelliumGroup(
            group_ids[members],
            members,
            len(members),
            tuple(sorted(ms, key=lambda m: _CRITERIA.index(m.criterion))),
        )
        for members, ms in sorted(
            grouped.items(),
            key=lambda item: (
                -len(item[0]),
                tuple(STELLIUM_CORE.index(n) for n in item[0]),
            ),
        )
    )
    requested = tuple(e for e in evaluations if e.status != "not_requested")
    status = (
        "not_evaluable"
        if all(e.status == "not_evaluable" for e in requested)
        else "partial"
        if any(e.status != "evaluated" for e in requested)
        else "complete"
    )
    fingerprint = _digest(
        [
            STELLIUM_SCHEMA_VERSION,
            sorted(normalized.items()),
            asdict(policy),
            asdict(selection),
            asdict(context),
            asdict(houses) if houses is not None else None,
            house_unavailable_reason,
        ]
    )
    return StelliumAnalysis(
        STELLIUM_SCHEMA_VERSION,
        fingerprint,
        status,
        policy,
        context,
        coverage,
        evaluations,
        house_receipt,
        groups,
    )


__all__ = [
    "STELLIUM_SCHEMA_VERSION",
    "STELLIUM_CORE",
    "StelliumAnalysisPolicy",
    "StelliumContext",
    "StelliumSelection",
    "StelliumHouseContext",
    "StelliumArc",
    "StelliumAssociation",
    "StelliumMatch",
    "StelliumGroup",
    "StelliumEvaluation",
    "StelliumCoverage",
    "StelliumHouseReceipt",
    "StelliumAnalysis",
    "analyze_stelliums",
]
