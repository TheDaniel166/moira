"""Natal D1 Nārāyaṇa Daśā using Rath's tables and explicit strength evidence."""
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Literal

from ._dasha_intervals import validate_interval
from .daily_panchanga import _finite_number
from .dasha_systems import _resolve_year_days
from .jaimini_extended import rasi_aspects
from .vedic_dignities import EXALTATION_SIGN, MULATRIKONA_SIGN, OWN_SIGNS, _SIGN_RULER

__all__ = ["NarayanaDecision", "NarayanaPeriod", "NarayanaDashaResult", "narayana_dasha", "active_narayana"]

_PROFILE_ID = "rath_book_resolved_strength"
_SOURCE_REFERENCE = "Sanjay Rath, Narayana Dasa, pp. 34–55, Tables 17, 20 and 25"
_CO_LORDS = {7: ("Mars", "Ketu"), 10: ("Saturn", "Rahu")}
_PLANETS = frozenset(OWN_SIGNS) | {"Rahu", "Ketu"}
_EXALTED = EXALTATION_SIGN | {"Rahu": 2, "Ketu": 8}
_DOMICILES = OWN_SIGNS | {"Rahu": [10], "Ketu": [7]}
_OFFICES = MULATRIKONA_SIGN | {"Rahu": 5, "Ketu": 11}


@dataclass(frozen=True, slots=True)
class NarayanaDecision:
    """Evidence used to decide the stronger of two opposite D1 signs."""

    reference_sign: int
    opposite_sign: int
    winner: int | None
    rule: str


@dataclass(frozen=True, slots=True)
class NarayanaPeriod:
    """An exact source-year period with optional half-open UT1 projection."""

    sign_index: int
    cycle: int
    lord: str | None
    source_years_numerator: int
    source_years_denominator: int
    source_start_years: float
    source_end_years: float
    start_jd_ut1: float | None
    end_jd_ut1: float | None
    antardasha_decision: NarayanaDecision | None = None
    antardasha_direction: str | None = None
    antardashas: tuple["NarayanaPeriod", ...] = ()


@dataclass(frozen=True, slots=True)
class NarayanaDashaResult:
    """Two complementary cycles or a finite account of unresolved input evidence."""

    lagna_sign_index: int
    starting_sign_index: int | None
    starting_decision: NarayanaDecision
    direction: str | None
    exception: str | None
    major_order: tuple[int, ...]
    resolved_co_lords: dict[int, str | None]
    co_lord_rules: dict[int, str]
    periods: tuple[NarayanaPeriod, ...]
    unresolved: tuple[str, ...]
    year_basis: str | None
    birth_jd_ut1: float | None
    profile_id: Literal["rath_book_resolved_strength"] = field(init=False, default=_PROFILE_ID)
    source_reference: str = field(init=False, default=_SOURCE_REFERENCE)


def _sign(value):
    if type(value) is not int or not 0 <= value < 12:
        raise ValueError("sign indices must be integers in [0, 11]")
    return value


def _degree(sign, name):
    if sign == _EXALTED[name]:
        return 4
    if sign == _OFFICES[name]:
        return 3
    if sign in _DOMICILES[name]:
        return 2
    return 0 if sign == (_EXALTED[name] + 6) % 12 else 1


def _vimsapada(sign):
    return (sign // 3) % 2 == 0


def _duration(sign, lord_sign, lord):
    if sign == lord_sign:
        return 12
    direction = 1 if _vimsapada(sign) else -1
    dignity = int(lord_sign == _EXALTED[lord]) - int(lord_sign == (_EXALTED[lord] + 6) % 12)
    return min(12, (direction * (lord_sign - sign)) % 12 + dignity)


def _direction_exception(sign, signs, degrees):
    saturn, ketu = signs["Saturn"] == sign, signs["Ketu"] == sign
    if saturn and ketu:
        # Table 20 measures Ketu from the end of its sign.
        s, k = degrees["Saturn"], 30 - degrees["Ketu"]
        if s == k:
            return "saturn_ketu_tie"
        return "saturn" if s > k else "ketu"
    return "saturn" if saturn else "ketu" if ketu else "ordinary"


def _major_order(seed, exception):
    """Reconstruct the general, Saturn, and Ketu sign orders in Tables 10–12."""
    direction = 1 if _vimsapada((seed + 8) % 12) else -1
    mode = seed % 3
    if exception == "saturn":
        direction, mode = 1, 0
    elif exception == "ketu":
        direction *= -1
    if mode == 2:
        offsets = (9 * quadrant + 4 * trine for quadrant in range(4) for trine in range(3))
    else:
        stride = 5 if mode == 1 else 1
        offsets = (stride * i for i in range(12))
    return tuple((seed + direction * value) % 12 for value in offsets), direction


def _opposite_strength(sign, occupants, signs, lords, supplied):
    opposite = (sign + 6) % 12
    if sign in supplied:
        return NarayanaDecision(sign, opposite, supplied[sign], "caller_resolved_strength")

    def support(s):
        lord = lords[s]
        if lord is None:
            return None
        return sum(signs[p] == s or rasi_aspects(signs[p], s) for p in ("Mercury", "Jupiter", lord))

    def dignity(s):
        return tuple(sorted((_degree(s, p) for p in occupants[s]), reverse=True))

    for name, factor in (
        ("occupant_count", lambda s: len(occupants[s])),
        ("rasi_aspect_and_conjunction", support), ("occupant_dignity", dignity),
    ):
        a, b = factor(sign), factor(opposite)
        if a is None or b is None:
            break
        if a != b:
            return NarayanaDecision(sign, opposite, sign if a > b else opposite, name)
    return NarayanaDecision(sign, opposite, None, "unresolved_strength")


def _co_lord_decisions(signs, occupants, supplied):
    lords, reasons = {}, {}
    for sign, (classical, node) in _CO_LORDS.items():
        a, b = signs[classical], signs[node]
        if sign in supplied:
            winner, reason = supplied[sign], "caller_resolved_co_lord"
        elif a == sign and b == sign:
            winner, reason = classical, "both_in_own_sign"
        elif a == sign or b == sign:
            winner, reason = (node if a == sign else classical), "other_than_own_sign"
        elif len(occupants[a]) != len(occupants[b]):
            winner, reason = (classical if len(occupants[a]) > len(occupants[b]) else node), "occupant_count"
        elif a == b and _duration(sign, a, classical) == _duration(sign, b, node):
            winner, reason = classical, "co_lords_same_sign_and_duration"
        else:
            winner, reason = None, "unresolved_co_lord_strength"
        lords[sign], reasons[sign] = winner, reason
    return lords, reasons


def _period(sign, cycle, lord, elapsed, length, project, decision=None, direction=None, children=()):
    end = elapsed + length
    first, last = (project(elapsed), project(end)) if length else (None, None)
    if first is not None:
        validate_interval(first, last, None, None)
    return NarayanaPeriod(
        sign, cycle, lord, length.numerator, length.denominator, float(elapsed), float(end),
        first, last, decision, direction, children,
    )


def narayana_dasha(
    lagna_sidereal_longitude: float, sidereal_longitudes: dict[str, float], *,
    resolved_strength: dict[int, int] | None = None, resolved_co_lords: dict[int, str] | None = None,
    birth_jd_ut1: float | None = None, year_basis: str | None = None,
) -> NarayanaDashaResult:
    """Calculate Rath major and subperiods with inspectable rulership decisions.

    Caller-supplied winners are available for pairs and co-lords whose later
    strength rules conflict across the source's worked cases. A winner for
    one of the opposite signs applies to the pair in both directions.
    """
    def longitude(name, value):
        _finite_number(name, value)
        if not 0 <= value < 360:
            raise ValueError(f"{name} must be a sidereal longitude in [0, 360)")
        return float(value)

    lagna = int(longitude("Lagna", lagna_sidereal_longitude) // 30)
    if set(sidereal_longitudes) != _PLANETS:
        raise ValueError("Narayana requires the seven visible planets and Rahu and Ketu")
    values = {name: longitude(name, value) for name, value in sidereal_longitudes.items()}
    signs = {name: int(value // 30) for name, value in values.items()}
    degrees = {name: value % 30 for name, value in values.items()}
    occupants = tuple(tuple(p for p, index in signs.items() if index == sign) for sign in range(12))

    supplied = {}
    for sign, winner in (resolved_strength or {}).items():
        opposite = (_sign(sign) + 6) % 12
        if _sign(winner) not in (sign, opposite) or supplied.get(sign, winner) != winner:
            raise ValueError("resolved strength winner must agree for the opposite pair")
        supplied[sign] = supplied[opposite] = winner
    supplied_lords = {} if resolved_co_lords is None else resolved_co_lords
    for sign, lord in supplied_lords.items():
        if lord not in _CO_LORDS.get(_sign(sign), ()):
            raise ValueError("resolved co-lord must be one of the two lords for Scorpio or Aquarius")
        a, b = _CO_LORDS[sign]
        if (signs[a] == sign) != (signs[b] == sign) and signs[lord] == sign:
            raise ValueError("the co-lord placed outside its own sign supplies the duration")

    if (birth_jd_ut1 is None) != (year_basis is None):
        raise ValueError("birth_jd_ut1 and year_basis must be supplied together")
    days = None
    if birth_jd_ut1 is not None:
        _finite_number("birth_jd_ut1", birth_jd_ut1)
        if not -10_000_000 <= birth_jd_ut1 <= 10_000_000:
            raise ValueError("birth_jd_ut1 is out of bounds")
        days = Fraction(str(_resolve_year_days(year_basis)))

    def project(time):
        return None if days is None else float(Fraction(birth_jd_ut1) + time * days)

    co_lords, lord_rules = _co_lord_decisions(signs, occupants, supplied_lords)
    lords = _SIGN_RULER | co_lords
    starting = _opposite_strength(lagna, occupants, signs, lords, supplied)
    seed = starting.winner
    exception = _direction_exception(seed, signs, degrees) if seed is not None else None
    order, direction = (), None
    if seed is not None and exception != "saturn_ketu_tie":
        order, sign = _major_order(seed, exception)
        direction = "forward" if sign == 1 else "reverse"

    unresolved = [f"co_lord_{s}_unresolved" for s, p in co_lords.items() if p is None]
    if not order:
        unresolved.append("starting_sign_unresolved" if seed is None else "saturn_ketu_tie")
    periods = []
    if order and not unresolved:
        antardashas = {}
        for sign in order:
            decision = _opposite_strength(sign, occupants, signs, lords, supplied)
            switch = _direction_exception(sign, signs, degrees)
            if decision.winner is None or switch == "saturn_ketu_tie":
                antardashas[sign] = (decision, (), None)
                unresolved.append(f"antardasha_{sign}_unresolved")
                continue
            sub_seed = signs[lords[decision.winner]]
            step = 1 if sub_seed % 2 == 0 else -1
            step = 1 if switch == "saturn" else -step if switch == "ketu" else step
            antardashas[sign] = (decision, tuple((sub_seed + step * j) % 12 for j in range(12)),
                                "forward" if step == 1 else "reverse")

        elapsed = Fraction(0)
        for cycle in (1, 2):
            for sign in order:
                lord = lords[sign]
                first = _duration(sign, signs[lord], lord)
                length = Fraction(first if cycle == 1 else 12 - first)
                decision, sub_order, sub_dir = antardashas[sign]
                share = length / 12
                children = tuple(_period(sub, cycle, None, elapsed + share * i, share, project)
                                 for i, sub in enumerate(sub_order)) if length else ()
                periods.append(_period(sign, cycle, lord, elapsed, length, project, decision, sub_dir, children))
                elapsed += length
    return NarayanaDashaResult(lagna, seed, starting, direction, exception, order, co_lords,
                              lord_rules, tuple(periods), tuple(unresolved), year_basis, birth_jd_ut1)


def active_narayana(result: NarayanaDashaResult, query_jd_ut1: float) -> tuple[NarayanaPeriod, ...]:
    """Return the active major and available subperiod on a projected UT1 axis."""
    _finite_number("query_jd_ut1", query_jd_ut1)
    if result.birth_jd_ut1 is None:
        raise ValueError("active Narayana requires a projected schedule")
    for major in result.periods:
        if major.start_jd_ut1 is not None and major.start_jd_ut1 <= query_jd_ut1 < major.end_jd_ut1:
            return (major,) + tuple(p for p in major.antardashas if p.start_jd_ut1 <= query_jd_ut1 < p.end_jd_ut1)
    return ()
