"""Source-defined yoga formation, distinct from strength or life outcomes.

The finite catalogue owns admission and interpretation. This engine assembles
AND clauses into source-specific alternative branches, retaining every witness.
Natal whole-sign houses and directed full graha aspects reuse the yoga owner;
D9 uses moira.varga's exact partition. No ephemeris, global cache, or I/O.
"""

from dataclasses import dataclass
from collections.abc import Mapping
from types import MappingProxyType

from ._yoga_inputs import PLANETS, longitudes, number
from .varga import navamsa
from .vedic_dignities import OWN_SIGNS, DEBILITATION_SIGN, EXALTATION_SIGN
from .yogas import _RASI_LORDS, _sign_aspects
from .yoga_extension_policy import (
    YogaExtensionPolicy,
    YogaExtensionRule,
    _selected_rules,
    list_yoga_extension_rules,
)

__all__ = [
    "YogaExtensionPosition",
    "YogaExtensionClause",
    "YogaExtensionBranch",
    "YogaExtensionQualification",
    "YogaExtensionResult",
    "YogaExtensionChartResult",
    "evaluate_yoga_extensions",
]


def _tuple(value, cls, name):
    if type(value) is not tuple or any(type(v) is not cls for v in value):
        raise ValueError(f"{name} must be an immutable tuple of {cls.__name__}")


def _index(value, name, low=0, high=11):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")


@dataclass(frozen=True, slots=True)
class YogaExtensionPosition:
    """A classical body's supplied longitude and observed D1/D9 chart placement."""
    planet: str
    sidereal_longitude: float
    d1_sign_index: int
    d1_house: int
    d9_sign_index: int | None

    def __post_init__(self):
        if self.planet not in PLANETS:
            raise ValueError("unknown classical planet")
        number(self.sidereal_longitude, "sidereal_longitude", canonical=True)
        _index(self.d1_sign_index, "d1_sign_index")
        _index(self.d1_house, "d1_house", 1, 12)
        if self.d1_sign_index != int(self.sidereal_longitude // 30):
            raise ValueError("D1 sign does not match longitude")
        if self.d9_sign_index is not None:
            _index(self.d9_sign_index, "d9_sign_index")


@dataclass(frozen=True, slots=True)
class YogaExtensionClause:
    """One typed observation; state is checked against its declared predicate."""

    clause_id: str
    predicate: str
    state: str
    planet: str
    role: str
    frame: str
    sign_index: int
    house: int | None = None
    reference: str | None = None
    related_planet: str | None = None
    related_role: str | None = None
    related_frame: str | None = None
    related_sign_index: int | None = None
    expected_signs: tuple[int, ...] = ()
    expected_houses: tuple[int, ...] = ()

    def __post_init__(self):
        if any(
            type(v) is not str or not v for v in (self.clause_id, self.role)
        ) or self.frame not in ("D1", "D9"):
            raise ValueError("clause identity, role and frame required")
        if self.planet not in (*PLANETS, "Lagna"):
            raise ValueError("unknown clause planet")
        _index(self.sign_index, "sign_index")
        for values, low, high in (
            (self.expected_signs, 0, 11),
            (self.expected_houses, 1, 12),
        ):
            _tuple(values, int, "expected values")
            if len(set(values)) != len(values):
                raise ValueError("duplicate expected value")
            for v in values:
                _index(v, "expected value", low, high)
        if self.house is not None:
            _index(self.house, "house", 1, 12)
            if self.frame != "D1" or self.reference != "D1_Lagna":
                raise ValueError("houses require the natal Lagna reference")
        if self.predicate == "in_signs":
            if not self.expected_signs:
                raise ValueError("sign predicate requires expected signs")
            ok = self.sign_index in self.expected_signs
        elif self.predicate == "in_houses":
            if self.house is None or not self.expected_houses:
                raise ValueError(
                    "house predicate requires observed and expected houses"
                )
            ok = self.house in self.expected_houses
        elif self.predicate in ("conjunction", "aspect", "opposition", "navamsa_lord"):
            if (
                self.related_planet not in PLANETS
                or type(self.related_role) is not str
                or not self.related_role
            ):
                raise ValueError("relation requires a classical target and role")
            _index(self.related_sign_index, "related_sign_index")
            if self.predicate == "navamsa_lord":
                if self.frame != "D1" or self.related_frame != "D9":
                    raise ValueError("Navamsa lord identity joins D1 and D9")
                ok = self.planet == _RASI_LORDS[self.related_sign_index]
            else:
                if self.frame != "D1" or self.related_frame != "D1":
                    raise ValueError("formation relations use the natal D1 frame")
                distinct = self.planet != self.related_planet
                if self.predicate == "conjunction":
                    ok = distinct and self.sign_index == self.related_sign_index
                elif self.predicate == "aspect":
                    ok = distinct and _sign_aspects(
                        self.planet, self.sign_index, self.related_sign_index
                    )
                else:
                    ok = (
                        distinct
                        and (self.related_sign_index - self.sign_index) % 12 == 6
                    )
        else:
            raise ValueError("unknown clause predicate")
        if self.state != ("satisfied" if ok else "not_satisfied"):
            raise ValueError("clause state contradicts its observation")


@dataclass(frozen=True, slots=True)
class YogaExtensionBranch:
    """Immutable conjunction of clauses with a derived ALL state."""
    branch_id: str
    clauses: tuple[YogaExtensionClause, ...]

    def __post_init__(self):
        _tuple(self.clauses, YogaExtensionClause, "clauses")
        if type(self.branch_id) is not str or not self.branch_id or not self.clauses:
            raise ValueError("branch must have an identity and nonempty clauses")
        if len({c.clause_id for c in self.clauses}) != len(self.clauses):
            raise ValueError("duplicate clause identity")

    @property
    def aggregation(self) -> str:
        return "all"

    @property
    def state(self) -> str:
        return (
            "satisfied"
            if all(c.state == "satisfied" for c in self.clauses)
            else "not_satisfied"
        )


@dataclass(frozen=True, slots=True)
class YogaExtensionQualification:
    """Attributed interpretive context deliberately left unevaluated."""
    source_id: str
    passage: str
    context: str
    assessment: str = "not_evaluated"

    def __post_init__(self):
        if (
            any(
                type(v) is not str or not v
                for v in (self.source_id, self.passage, self.context)
            )
            or self.assessment != "not_evaluated"
        ):
            raise ValueError(
                "qualification must identify its unevaluated source context"
            )


@dataclass(frozen=True, slots=True)
class YogaExtensionResult:
    """A canonical source rule and its ANY branch witnesses and qualifications."""
    rule: YogaExtensionRule
    branches: tuple[YogaExtensionBranch, ...]

    def __post_init__(self):
        if (
            type(self.rule) is not YogaExtensionRule
            or self.rule not in list_yoga_extension_rules().rules
            or self.rule.admission != "admitted"
        ):
            raise ValueError("result requires a canonical admitted rule")
        _tuple(self.branches, YogaExtensionBranch, "branches")
        if len({b.branch_id for b in self.branches}) != len(self.branches):
            raise ValueError("duplicate branch identity")
        if not self.branches and self.rule.family != "navamsa":
            raise ValueError(
                "only no-debilitated-body Navamsa cases are not applicable"
            )

    @property
    def aggregation(self) -> str:
        return "any"

    @property
    def formation_state(self) -> str:
        if not self.branches:
            return "not_applicable"
        return (
            "formed"
            if any(b.state == "satisfied" for b in self.branches)
            else "not_formed"
        )

    @property
    def cancellation_assessment(self) -> str:
        return "not_specified_by_selected_passage"

    @property
    def qualifications(self) -> tuple[YogaExtensionQualification, ...]:
        s = self.rule.source.source_id
        if self.rule.family == "dhana":
            return (
                YogaExtensionQualification(
                    s,
                    "41.17",
                    "planetary strength and favorable/unfavorable disposition",
                ),
                YogaExtensionQualification(s, "41.16", "dasha realization"),
            )
        if self.rule.rule_id == "bphs.39.33-34":
            return (
                YogaExtensionQualification(
                    s, "39.34", "royal-lineage premise for the historical outcome"
                ),
            )
        return (
            YogaExtensionQualification(
                s,
                self.rule.passage,
                "historical outcome; formation is not realized status",
            ),
        )


@dataclass(frozen=True, slots=True)
class YogaExtensionChartResult:
    """Selected source proofs, chart observations, policy and derived rule counts."""
    policy: YogaExtensionPolicy
    lagna_sidereal_longitude: float
    lagna_sign_index: int
    positions: tuple[YogaExtensionPosition, ...]
    results: tuple[YogaExtensionResult, ...]

    def __post_init__(self):
        if type(self.policy) is not YogaExtensionPolicy:
            raise ValueError("canonical YogaExtensionPolicy required")
        if YogaExtensionPolicy(self.policy.profile_ids) != self.policy:
            raise ValueError("policy must be canonical")
        number(self.lagna_sidereal_longitude, "lagna", canonical=True)
        _index(self.lagna_sign_index, "lagna_sign_index")
        if self.lagna_sign_index != int(self.lagna_sidereal_longitude // 30):
            raise ValueError("Lagna sign mismatch")
        _tuple(self.positions, YogaExtensionPosition, "positions")
        if tuple(p.planet for p in self.positions) != PLANETS:
            raise ValueError(
                "positions must contain all seven bodies in canonical order"
            )
        need_d9 = any(
            p.requires_navamsa
            for p in list_yoga_extension_rules().profiles
            if p.profile_id in self.policy.profile_ids
        )
        for p in self.positions:
            p.__post_init__()
            if (
                p.d1_house != (p.d1_sign_index - self.lagna_sign_index) % 12 + 1
                or (p.d9_sign_index is not None) != need_d9
            ):
                raise ValueError("position frame/availability contradicts chart policy")
        _tuple(self.results, YogaExtensionResult, "results")
        if tuple(r.rule for r in self.results) != _selected_rules(self.policy):
            raise ValueError(
                "results must exactly cover the selected rules in canonical order"
            )
        positions = {p.planet: p for p in self.positions}
        for result in self.results:
            result.__post_init__()
            for branch in result.branches:
                branch.__post_init__()
                for c in branch.clauses:
                    c.__post_init__()
                    observed = (
                        self.lagna_sign_index
                        if c.planet == "Lagna"
                        else (
                            positions[c.planet].d1_sign_index
                            if c.frame == "D1"
                            else positions[c.planet].d9_sign_index
                        )
                    )
                    if c.sign_index != observed or (
                        c.house is not None
                        and c.house != (c.sign_index - self.lagna_sign_index) % 12 + 1
                    ):
                        raise ValueError("clause disagrees with the chart context")
                    if c.related_planet is not None:
                        related = positions[c.related_planet]
                        if c.related_sign_index != (
                            related.d1_sign_index
                            if c.related_frame == "D1"
                            else related.d9_sign_index
                        ):
                            raise ValueError(
                                "related clause disagrees with the chart context"
                            )

    @property
    def evaluated_count(self) -> int:
        return len(self.results)

    @property
    def formed_count(self) -> int:
        return sum(r.formation_state == "formed" for r in self.results)

    @property
    def not_formed_count(self) -> int:
        return sum(r.formation_state == "not_formed" for r in self.results)

    @property
    def not_applicable_count(self) -> int:
        return sum(r.formation_state == "not_applicable" for r in self.results)


@dataclass(frozen=True, slots=True, init=False)
class _Context:
    """One call's private derived chart; shared by all selected rules."""

    lagna: int
    signs: Mapping[str, int]
    houses: Mapping[str, int]
    lords: Mapping[int, str]
    d9: Mapping[str, int]
    debilitated: tuple[str, ...]

    def __init__(self, lons, lagna, d9):
        object.__setattr__(self, "lagna", int(lagna // 30))
        object.__setattr__(
            self, "signs", MappingProxyType({p: int(lons[p] // 30) for p in PLANETS})
        )
        object.__setattr__(
            self,
            "houses",
            MappingProxyType(
                {p: (s - self.lagna) % 12 + 1 for p, s in self.signs.items()}
            ),
        )
        object.__setattr__(
            self,
            "lords",
            MappingProxyType(
                {h: _RASI_LORDS[(self.lagna + h - 1) % 12] for h in range(1, 13)}
            ),
        )
        object.__setattr__(
            self,
            "d9",
            MappingProxyType(
                {p: int(navamsa(lons[p]).varga_longitude // 30) for p in PLANETS}
                if d9
                else {}
            ),
        )
        object.__setattr__(
            self,
            "debilitated",
            tuple(p for p in PLANETS if self.signs[p] == DEBILITATION_SIGN[p]),
        )

    def sign(self, id, p, allowed, role, frame="D1"):
        sign = (
            self.lagna
            if p == "Lagna"
            else (self.signs if frame == "D1" else self.d9)[p]
        )
        return YogaExtensionClause(
            id,
            "in_signs",
            "satisfied" if sign in allowed else "not_satisfied",
            p,
            role,
            frame,
            sign,
            expected_signs=tuple(allowed),
        )

    def house(self, id, p, allowed, role):
        h = self.houses[p]
        return YogaExtensionClause(
            id,
            "in_houses",
            "satisfied" if h in allowed else "not_satisfied",
            p,
            role,
            "D1",
            self.signs[p],
            h,
            "D1_Lagna",
            expected_houses=tuple(allowed),
        )

    def relation(self, id, kind, a, b, role_a, role_b):
        sb = self.d9[b] if kind == "navamsa_lord" else self.signs[b]
        if kind == "navamsa_lord":
            ok = a == _RASI_LORDS[sb]
        elif kind == "aspect":
            ok = a != b and _sign_aspects(a, self.signs[a], sb)
        elif kind == "opposition":
            ok = a != b and (sb - self.signs[a]) % 12 == 6
        else:
            ok = a != b and self.signs[a] == sb
        return YogaExtensionClause(
            id,
            kind,
            "satisfied" if ok else "not_satisfied",
            a,
            role_a,
            "D1",
            self.signs[a],
            related_planet=b,
            related_role=role_b,
            related_frame="D9" if kind == "navamsa_lord" else "D1",
            related_sign_index=sb,
        )


def _branch(id, *clauses):
    return YogaExtensionBranch(id, tuple(clauses))


def _navamsa(rule, c):
    if rule.rule_id == "raman.252":
        clauses = tuple(
            cl
            for p in c.debilitated
            for cl in (
                c.sign(
                    p + ".debilitated", p, (DEBILITATION_SIGN[p],), "debilitated_body"
                ),
                c.sign(
                    p + ".exalted_d9",
                    p,
                    (EXALTATION_SIGN[p],),
                    "debilitated_body",
                    "D9",
                ),
            )
        )
        return (_branch("all_debilitated_bodies", *clauses),) if clauses else ()
    branches = []
    for p in c.debilitated:
        lord = _RASI_LORDS[c.d9[p]]
        shared = (
            c.sign("debilitated", p, (DEBILITATION_SIGN[p],), "debilitated_body"),
            c.relation(
                "navamsa_lord",
                "navamsa_lord",
                lord,
                p,
                "navamsa_lord",
                "debilitated_body",
            ),
            c.house("lord_house", lord, (1, 4, 5, 7, 9, 10), "navamsa_lord"),
        )
        branches.append(
            _branch(
                p + ".movable_lagna",
                *shared,
                c.sign("movable_lagna", "Lagna", (0, 3, 6, 9), "natal_lagna"),
            )
        )
        branches.append(
            _branch(
                p + ".movable_lagna_lord_d9",
                *shared,
                c.sign(
                    "movable_lagna_lord_d9",
                    c.lords[1],
                    (0, 3, 6, 9),
                    "D1_lagna_lord",
                    "D9",
                ),
            )
        )
    return tuple(branches)


# Source tables: BPHS/Santhanam 41.2-8 and 41.9-15 respectively. Every
# named supporter is obligatory; conjunction/aspect choices belong to each.
_H5 = (
    ("Venus", ("Mars",)),
    ("Mercury", ("Moon", "Mars", "Jupiter")),
    ("Sun", ("Saturn", "Moon", "Jupiter")),
    ("Saturn", ("Sun", "Moon")),
    ("Jupiter", ("Mercury",)),
    ("Mars", ("Venus",)),
    ("Moon", ("Saturn",)),
)
_H1 = (
    ("Sun", ("Mars", "Jupiter")),
    ("Moon", ("Mercury", "Jupiter")),
    ("Mars", ("Mercury", "Venus", "Saturn")),
    ("Mercury", ("Saturn", "Jupiter")),
    ("Jupiter", ("Mercury", "Mars")),
    ("Venus", ("Saturn", "Mercury")),
    ("Saturn", ("Mars", "Jupiter")),
)


def _wealth(rule, c):
    from itertools import product

    verse = int(rule.passage.split(".")[1])
    p, supporters = _H5[verse - 2] if verse <= 8 else _H1[verse - 9]
    shared = (
        c.sign("own_sign", p, tuple(sorted(OWN_SIGNS[p])), "resident"),
        c.house("resident_house", p, (5 if verse <= 8 else 1,), "resident"),
    )
    if verse <= 8:
        return (
            _branch(
                "all_occupants",
                *shared,
                *(c.house(q + ".house", q, (11,), "H11_occupant") for q in supporters),
            ),
        )
    # Distribute ALL (join OR aspect) into finite AND branches (at most 8),
    # retaining every named support and direction, without generic sambandha.
    return tuple(
        _branch(
            ".".join(kinds),
            *shared,
            *(
                c.relation(q + ".support", kind, q, p, "supporter", "resident")
                for q, kind in zip(supporters, kinds)
            ),
        )
        for kinds in product(("conjunction", "aspect"), repeat=len(supporters))
    )


def _raja(rule, c):
    lords = c.lords
    v = rule.passage.split(".")[1]
    if v == "33-34":
        return (
            _branch(
                "mutual_aspect",
                c.relation("L5_to_L9", "aspect", lords[5], lords[9], "L5", "L9"),
                c.relation("L9_to_L5", "aspect", lords[9], lords[5], "L9", "L5"),
            ),
            _branch(
                "conjunction",
                c.relation("joined", "conjunction", lords[5], lords[9], "L5", "L9"),
            ),
            _branch(
                "opposition",
                c.relation("opposite", "opposition", lords[5], lords[9], "L5", "L9"),
            ),
        )
    if v == "36":
        return (
            _branch(
                "all_roles_in_ninth",
                *(
                    c.house("L" + str(h), lords[h], (9,), "L" + str(h))
                    for h in (5, 10, 4, 1)
                ),
            ),
        )
    if v == "37":
        return tuple(
            _branch(
                f"L{a}_L{b}",
                c.relation(
                    "joined", "conjunction", lords[a], lords[b], f"L{a}", f"L{b}"
                ),
            )
            for a in (4, 10)
            for b in (5, 9)
        )
    if v == "38":
        return tuple(
            _branch(
                f"L5_L{h}",
                c.house("L5_house", lords[5], (1, 4, 10), "L5"),
                c.relation("joined", "conjunction", lords[5], lords[h], "L5", f"L{h}"),
            )
            for h in (9, 1)
        )
    return tuple(
        _branch(
            role,
            c.sign(
                "Jupiter_own",
                "Jupiter",
                tuple(sorted(OWN_SIGNS["Jupiter"])),
                "resident",
            ),
            c.house("Jupiter_ninth", "Jupiter", (9,), "resident"),
            c.relation("joined", "conjunction", "Jupiter", p, "resident", role),
        )
        for p, role in (("Venus", "Venus"), (lords[5], "L5"))
    )


def evaluate_yoga_extensions(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    *,
    profile_ids: tuple[str, ...],
) -> YogaExtensionChartResult:
    """Evaluate explicitly selected source profiles from canonical sidereal D1 degrees.

    Missing chart data is an error. A lack of debilitated planets makes only
    the Navamsa rules not applicable. Strength/dasha/outcomes remain qualified.
    """
    policy = YogaExtensionPolicy(profile_ids)
    lons = longitudes(sidereal_longitudes, canonical=True)
    lagna = number(lagna_sidereal_lon, "lagna_sidereal_lon", canonical=True)
    rules = _selected_rules(policy)
    c = _Context(lons, lagna, any(r.family == "navamsa" for r in rules))
    results = tuple(
        YogaExtensionResult(
            r,
            (
                _navamsa
                if r.family == "navamsa"
                else _wealth
                if r.family == "dhana"
                else _raja
            )(r, c),
        )
        for r in rules
    )
    positions = tuple(
        YogaExtensionPosition(p, float(lons[p]), c.signs[p], c.houses[p], c.d9.get(p))
        for p in PLANETS
    )
    return YogaExtensionChartResult(policy, float(lagna), c.lagna, positions, results)
