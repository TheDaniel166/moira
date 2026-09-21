"""
Moira -- primary_directions/distributor.py
Distributor (Particeps) & Partner (Participator / Socius) Chronology Subsystem.

Boundary
--------
Owns the chronological distribution of primary direction arcs through the
terms/bounds of the zodiac. Traditional predictive methodology (Ptolemy Tetrabiblos
III.10, Dorotheus, Valens, Lilly) directs the significator (most notably the Ascendant)
through the bounds. The ruler of the bound occupied by the directed significator is
the Distributor (Particeps); any planet casting a primary aspect to the significator
during that bound's arc interval is the Partner / Participator (Socius).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from ..constants import SIGNS
from ..egyptian_bounds import (
    EgyptianBoundsDoctrine,
    EgyptianBoundsPolicy,
    egyptian_bound_of,
    EGYPTIAN_BOUNDS,
    PTOLEMAIC_BOUNDS,
    CHALDEAN_DAY_BOUNDS,
    CHALDEAN_NIGHT_BOUNDS,
)
from .targets import (
    PrimaryDirectionBoundTarget,
    resolve_primary_direction_bound_targets,
)
from .converse import PrimaryDirectionMotion

__all__ = [
    "DistributorPeriod",
    "resolve_distributor_chronology",
]


@dataclass(frozen=True, slots=True)
class DistributorPeriod:
    """
    Vessel: A chronological term/bound distribution period for a directed significator.

    Attributes:
        significator: The directed significator (e.g. "ASC", "MC", "Sun").
        ruler: Planet ruling this bound segment (Mercury, Venus, Mars, Jupiter, Saturn).
        sign: Zodiac sign of this bound.
        bound_start_deg: Starting ecliptic degree of the bound within the sign [0, 30).
        bound_end_deg: Ending ecliptic degree of the bound within the sign (0, 30].
        entry_arc_deg: Directional arc at which the significator enters this bound.
        exit_arc_deg: Directional arc at which the significator exits this bound.
        participators: Aspectual primary directions perfecting within [entry_arc, exit_arc].
        entry_age: Optional chronological age at entry (in tropical years).
        exit_age: Optional chronological age at exit (in tropical years).
        entry_date_utc: Optional ISO 8601 UTC date string at entry.
        exit_date_utc: Optional ISO 8601 UTC date string at exit.
    """
    significator: str
    ruler: str
    sign: str
    bound_start_deg: float
    bound_end_deg: float
    entry_arc_deg: float
    exit_arc_deg: float
    participators: tuple[object, ...] = ()
    entry_age: float | None = None
    exit_age: float | None = None
    entry_date_utc: str | None = None
    exit_date_utc: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.significator, str) or not self.significator.strip():
            raise ValueError("DistributorPeriod requires a non-empty significator")
        if not isinstance(self.ruler, str) or not self.ruler.strip():
            raise ValueError("DistributorPeriod requires a non-empty ruler")
        if self.sign not in SIGNS:
            raise ValueError(f"Unknown zodiac sign: {self.sign}")
        if not (0.0 <= self.bound_start_deg < self.bound_end_deg <= 30.0):
            raise ValueError(f"Invalid bound degrees: {self.bound_start_deg}..{self.bound_end_deg}")
        if self.entry_arc_deg < 0.0:
            raise ValueError(f"entry_arc_deg must be non-negative, got {self.entry_arc_deg}")
        if self.exit_arc_deg < self.entry_arc_deg:
            raise ValueError(
                f"exit_arc_deg ({self.exit_arc_deg}) cannot precede entry_arc_deg ({self.entry_arc_deg})"
            )
        try:
            participators = tuple(self.participators)
        except TypeError as exc:
            raise ValueError("participators must be iterable") from exc
        object.__setattr__(self, "participators", participators)


def _table_for_doctrine(doctrine: EgyptianBoundsDoctrine) -> dict[str, list[tuple[str, float, float]]]:
    if doctrine is EgyptianBoundsDoctrine.PTOLEMAIC:
        return PTOLEMAIC_BOUNDS
    if doctrine is EgyptianBoundsDoctrine.CHALDEAN_DAY:
        return CHALDEAN_DAY_BOUNDS
    if doctrine is EgyptianBoundsDoctrine.CHALDEAN_NIGHT:
        return CHALDEAN_NIGHT_BOUNDS
    return EGYPTIAN_BOUNDS


_SIGN_LOOKUP: dict[str, str] = {
    # Full names
    "Aries": "Aries", "Taurus": "Taurus", "Gemini": "Gemini", "Cancer": "Cancer",
    "Leo": "Leo", "Virgo": "Virgo", "Libra": "Libra", "Scorpio": "Scorpio",
    "Sagittarius": "Sagittarius", "Capricorn": "Capricorn", "Aquarius": "Aquarius", "Pisces": "Pisces",
    # Standard abbreviations
    "Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini", "Can": "Cancer", "Cnc": "Cancer",
    "Leo": "Leo", "Vir": "Virgo", "Lib": "Libra", "Sco": "Scorpio", "Scp": "Scorpio",
    "Sag": "Sagittarius", "Sgr": "Sagittarius",
    "Cap": "Capricorn", "Aqu": "Aquarius", "Aqr": "Aquarius", "Pis": "Pisces", "Psc": "Pisces",
}
for _k, _v in list(_SIGN_LOOKUP.items()):
    _SIGN_LOOKUP[_k.lower()] = _v


def _parse_bound_promissor(name: str) -> tuple[str, str, float] | None:
    """
    Parse a bound promissor name of the form:
    'Term of Jupiter (00°00\' Ari)' -> ('Jupiter', 'Aries', 0.0)
    Supports diverse abbreviations ('Sgr', 'Cap', 'Psc', etc.) and degree formats.
    """
    if not name.startswith("Term of ") or "(" not in name or ")" not in name:
        return None
    try:
        prefix, rest = name.split("(", 1)
        ruler = prefix[len("Term of "):].strip()
        inside = rest.rstrip(")").strip()
        if "°" not in inside:
            return None
        deg_str, sign_part = inside.split("°", 1)
        deg = float(deg_str.strip())
        if "'" in sign_part:
            min_str, sign_part = sign_part.split("'", 1)
            min_str = min_str.strip()
            if min_str:
                deg += float(min_str) / 60.0
        sign_token = sign_part.strip()
        sign = _SIGN_LOOKUP.get(sign_token) or _SIGN_LOOKUP.get(sign_token.lower())
        if sign is None and len(sign_token) >= 3:
            sign = _SIGN_LOOKUP.get(sign_token[:3].title()) or _SIGN_LOOKUP.get(sign_token[:3].lower())
        if sign is None:
            return None
        return ruler, sign, deg
    except Exception:
        return None


def resolve_distributor_chronology(
    significator: str,
    natal_longitude: float,
    bound_arcs: Iterable[object],
    participating_arcs: Iterable[object] = (),
    *,
    doctrine: EgyptianBoundsDoctrine = EgyptianBoundsDoctrine.EGYPTIAN,
    motion: PrimaryDirectionMotion = PrimaryDirectionMotion.DIRECT,
    max_arc: float = 90.0,
) -> tuple[DistributorPeriod, ...]:
    """
    Resolve the chronological sequence of Distributor periods and their participating aspects.

    Args:
        significator: Target significator name (e.g. "ASC").
        natal_longitude: Ecliptic longitude of the significator at birth [0, 360).
        bound_arcs: Primary direction arcs directed to bound boundaries.
        participating_arcs: Aspectual primary direction arcs directed to the significator.
        doctrine: Egyptian, Ptolemaic, or Chaldean bounds table.
        motion: Direction motion (DIRECT or CONVERSE).
        max_arc: Maximum directional arc to consider.

    Returns:
        Ordered tuple of DistributorPeriod vessels spanning [0.0, max_arc].
    """
    if not isinstance(significator, str) or not significator.strip():
        raise ValueError("resolve_distributor_chronology requires a non-empty significator")
    if not (0.0 <= natal_longitude < 360.0):
        raise ValueError(f"natal_longitude must be in [0, 360), got {natal_longitude}")
    if max_arc <= 0.0:
        raise ValueError(f"max_arc must be positive, got {max_arc}")

    table = _table_for_doctrine(doctrine)

    # 1. Initial natal bound
    initial_truth = egyptian_bound_of(
        natal_longitude,
        policy=EgyptianBoundsPolicy(doctrine=doctrine),
    )
    current_ruler = initial_truth.segment.ruler
    current_sign = initial_truth.segment.sign
    current_start_deg = initial_truth.segment.start_degree
    current_end_deg = initial_truth.segment.end_degree
    current_entry_arc = 0.0

    # 2. Filter and sort bound arcs
    valid_bound_arcs: list[tuple[float, str, str, float, float]] = []
    for arc in bound_arcs:
        arc_sig = getattr(arc, "significator", None)
        arc_prom = getattr(arc, "promissor", None)
        arc_val = getattr(arc, "arc", None)
        arc_motion = getattr(arc, "motion", None)
        if arc_sig != significator or arc_prom is None or arc_val is None:
            continue
        if arc_motion is not None and arc_motion is not motion:
            continue
        if not (0.0 < arc_val <= max_arc):
            continue

        parsed = _parse_bound_promissor(arc_prom)
        if parsed is None:
            continue
        ruler, sign, deg = parsed
        # Find the segment in table[sign] that begins at deg
        segments = table[sign]
        seg_match = next((seg for seg in segments if abs(seg[1] - deg) < 1e-4), None)
        if seg_match is None:
            continue
        seg_ruler, seg_start, seg_end = seg_match
        valid_bound_arcs.append((float(arc_val), seg_ruler, sign, float(seg_start), float(seg_end)))

    # Sort strictly by arc value ascending
    valid_bound_arcs.sort(key=lambda item: item[0])

    # 3. Assemble chronological periods
    periods: list[DistributorPeriod] = []
    for next_arc, next_ruler, next_sign, next_start, next_end in valid_bound_arcs:
        if next_arc <= current_entry_arc + 1e-6:
            # Skip redundant boundary contacts at identical arc
            continue
        periods.append(
            DistributorPeriod(
                significator=significator,
                ruler=current_ruler,
                sign=current_sign,
                bound_start_deg=current_start_deg,
                bound_end_deg=current_end_deg,
                entry_arc_deg=current_entry_arc,
                exit_arc_deg=next_arc,
            )
        )
        current_ruler = next_ruler
        current_sign = next_sign
        current_start_deg = next_start
        current_end_deg = next_end
        current_entry_arc = next_arc

    # Final terminal period extending to max_arc
    if current_entry_arc < max_arc:
        periods.append(
            DistributorPeriod(
                significator=significator,
                ruler=current_ruler,
                sign=current_sign,
                bound_start_deg=current_start_deg,
                bound_end_deg=current_end_deg,
                entry_arc_deg=current_entry_arc,
                exit_arc_deg=max_arc,
            )
        )

    # 4. Attach participating aspects
    part_list = list(participating_arcs)
    final_periods: list[DistributorPeriod] = []
    num_periods = len(periods)
    for idx, period in enumerate(periods):
        is_last = idx == num_periods - 1
        matched_participators = []
        for arc in part_list:
            arc_sig = getattr(arc, "significator", None)
            arc_val = getattr(arc, "arc", None)
            arc_motion = getattr(arc, "motion", None)
            if arc_sig != significator or arc_val is None:
                continue
            if arc_motion is not None and arc_motion is not motion:
                continue
            arc_val_f = float(arc_val)
            if is_last:
                in_window = period.entry_arc_deg <= arc_val_f <= period.exit_arc_deg
            else:
                in_window = period.entry_arc_deg <= arc_val_f < period.exit_arc_deg
            if in_window:
                matched_participators.append(arc)

        # Sort participators by arc
        matched_participators.sort(key=lambda a: getattr(a, "arc", 0.0))
        final_periods.append(
            DistributorPeriod(
                significator=period.significator,
                ruler=period.ruler,
                sign=period.sign,
                bound_start_deg=period.bound_start_deg,
                bound_end_deg=period.bound_end_deg,
                entry_arc_deg=period.entry_arc_deg,
                exit_arc_deg=period.exit_arc_deg,
                participators=tuple(matched_participators),
            )
        )

    return tuple(final_periods)
