"""Rangacharya's three bounded Chara recipes: source years and optional Moira clock.

Authority: 2007 manual, printed 65-70; witness and conflicts in the VED-013
catalogue. No node co-lords, subperiods, later cycles, or astronomical IO.
"""

from dataclasses import dataclass, field
from typing import Literal

from ._jaimini_profile_inputs import (
    CLASSICAL,
    CharaProjection,
    JaiminiChart,
    admit_chart,
    chart_signs,
    finite_number,
    strict_int,
)
from ._jaimini_profile_results import result_invariants
from .jaimini_extended import _RASI_LORDS, _SAVYA_SIGNS
from .jaimini_profile_policy import CHARA_IDS, VERSION, JaiminiProfile, admit_profile
from .vedic_dignities import EXALTATION_SIGN

__all__ = [
    "CharaArithmeticRow",
    "CharaProfileInterval",
    "CharaProfileSchedule",
    "CharaArithmeticResult",
    "evaluate_chara_profile",
]


@dataclass(frozen=True, slots=True)
class CharaArithmeticRow:
    """One source-arithmetic row, including any zero years and its derivation."""

    ordinal: int
    sign: int
    lord: str
    lord_sign: int
    count_direction: int
    inclusive_count: int
    base_years: int
    exception: Literal["none", "own_sign_twelve", "opposite_sign_ten"]
    dignity_adjustment: int
    years: int
    start_year: int
    end_year: int
    rule_id: str

    def __post_init__(self):
        for name in ("ordinal", "sign", "lord_sign"):
            strict_int(getattr(self, name), 0, 11, name)
        strict_int(self.count_direction, -1, 1, "count_direction")
        if self.count_direction == 0 or self.lord not in CLASSICAL:
            raise ValueError("invalid duration direction or lord")
        strict_int(self.inclusive_count, 1, 12, "inclusive_count")
        strict_int(self.base_years, 0, 12, "base_years")
        strict_int(self.dignity_adjustment, -1, 1, "dignity_adjustment")
        strict_int(self.years, 0, 12, "years")
        strict_int(self.start_year, 0, 144, "start_year")
        strict_int(self.end_year, 0, 144, "end_year")
        if self.exception not in ("none", "own_sign_twelve", "opposite_sign_ten"):
            raise ValueError("unknown duration exception")
        if (
            self.years != self.base_years + self.dignity_adjustment
            or self.end_year != self.start_year + self.years
        ):
            raise ValueError("inconsistent duration arithmetic")


@dataclass(frozen=True, slots=True)
class CharaProfileInterval:
    """Positive half-open interval referring back to one arithmetic row."""

    row_ordinal: int
    start_jd: float
    end_jd: float

    def __post_init__(self):
        strict_int(self.row_ordinal, 0, 11, "row_ordinal")
        finite_number(self.start_jd, "start_jd")
        finite_number(self.end_jd, "end_jd")
        if not self.start_jd < self.end_jd:
            raise ValueError("epoch cannot represent positive ordered Chara intervals")


@dataclass(frozen=True, slots=True)
class CharaProfileSchedule:
    """Separate calendar projection; zero rows are explicitly unscheduled."""

    status: Literal["not_requested", "projected"]
    projection: CharaProjection | None
    intervals: tuple[CharaProfileInterval, ...]
    not_scheduled_zero_duration: tuple[int, ...]

    def __post_init__(self):
        if (
            type(self.intervals) is not tuple
            or type(self.not_scheduled_zero_duration) is not tuple
        ):
            raise ValueError("schedule evidence must be immutable")
        if self.status == "not_requested":
            if (
                self.projection is not None
                or self.intervals
                or self.not_scheduled_zero_duration
            ):
                raise ValueError("unrequested schedule has no calendar evidence")
        elif self.status == "projected":
            if type(self.projection) is not CharaProjection:
                raise ValueError("projected schedule requires an explicit projection")
            self.projection.__post_init__()
            for interval in self.intervals:
                if type(interval) is not CharaProfileInterval:
                    raise ValueError("invalid schedule interval")
                interval.__post_init__()
            for n in self.not_scheduled_zero_duration:
                strict_int(n, 0, 11, "zero row")
        else:
            raise ValueError("unknown schedule status")


@dataclass(frozen=True, slots=True)
class CharaArithmeticResult:
    """Immutable one-cycle source arithmetic with a separately identified schedule."""

    chart: JaiminiChart
    profile: JaiminiProfile
    seed_sign: int
    sequence_direction: int
    rows: tuple[CharaArithmeticRow, ...]
    total_years: int
    schedule: CharaProfileSchedule
    catalogue_version: str = field(init=False, default=VERSION)
    cycle_count: int = field(init=False, default=1)
    subperiod_scope: str = field(init=False, default="not_admitted")
    participant_pool: tuple[str, ...] = field(init=False, default=CLASSICAL)

    def __post_init__(self):
        if self.chart != admit_chart(self.chart, CLASSICAL):
            raise ValueError("result chart must be the immutable admitted snapshot")
        if (
            self.catalogue_version != VERSION
            or type(self.cycle_count) is not int
            or self.cycle_count != 1
            or self.subperiod_scope != "not_admitted"
            or self.participant_pool != CLASSICAL
        ):
            raise ValueError("invalid Chara computation metadata")
        if type(self.profile) is not JaiminiProfile or self.profile != admit_profile(
            self.profile.profile_id, "chara"
        ):
            raise ValueError("invalid Chara profile receipt")
        strict_int(self.seed_sign, 0, 11, "seed_sign")
        strict_int(self.sequence_direction, -1, 1, "sequence_direction")
        if (
            self.sequence_direction == 0
            or type(self.rows) is not tuple
            or len(self.rows) != 12
        ):
            raise ValueError("one direction and twelve arithmetic rows required")
        cursor = 0
        signs, lagna = chart_signs(self.chart)
        recipe = CHARA_IDS.index(self.profile.profile_id)
        seed, direction, sequence = _sequence(recipe, lagna)
        if (self.seed_sign, self.sequence_direction) != (seed, direction):
            raise ValueError("Chara seed or direction disagrees with profile and Lagna")
        for i, row in enumerate(self.rows):
            if type(row) is not CharaArithmeticRow:
                raise ValueError("invalid arithmetic row")
            row.__post_init__()
            if (
                row.ordinal != i
                or row.start_year != cursor
                or row.rule_id != self.profile.rule_ids[0]
            ):
                raise ValueError("invalid row order, cumulative years or source rule")
            if row.lord != _RASI_LORDS[row.sign] or row.lord_sign != signs[row.lord]:
                raise ValueError("duration lord evidence disagrees with chart")
            if row.sign != sequence[i]:
                raise ValueError("Chara sequence disagrees with selected profile")
            if (
                row.count_direction,
                row.inclusive_count,
                row.base_years,
                row.exception,
                row.dignity_adjustment,
            ) != _duration(recipe, row.sign, row.lord_sign):
                raise ValueError("Chara duration derivation disagrees with selected profile")
            cursor = row.end_year
        strict_int(self.total_years, 0, 144, "total_years")
        if (
            len({r.sign for r in self.rows}) != 12
            or self.rows[0].sign != self.seed_sign
            or cursor != self.total_years
        ):
            raise ValueError("inconsistent Chara sequence or total")
        if type(self.schedule) is not CharaProfileSchedule:
            raise ValueError("invalid schedule")
        self.schedule.__post_init__()
        if self.schedule.status == "projected":
            expected = tuple(r.ordinal for r in self.rows if r.years)
            if tuple(i.row_ordinal for i in self.schedule.intervals) != expected:
                raise ValueError("positive rows must each have exactly one interval")
            if self.schedule.not_scheduled_zero_duration != tuple(
                r.ordinal for r in self.rows if not r.years
            ):
                raise ValueError("missing zero-duration evidence")
            epoch = self.schedule.projection.epoch_jd
            for interval in self.schedule.intervals:
                row = self.rows[interval.row_ordinal]
                if (
                    interval.start_jd != epoch + row.start_year * 365.25
                    or interval.end_jd != epoch + row.end_year * 365.25
                ):
                    raise ValueError(
                        "calendar projection disagrees with source arithmetic"
                    )


def _sequence(recipe, lagna):
    """Derive the selected manual's seed, direction and complete sign sequence."""
    parity = 1 if lagna % 2 == 0 else -1
    seed = (lagna + 3 * parity) % 12 if recipe == 2 else lagna
    direction = (
        (1 if (lagna + 8) % 12 in _SAVYA_SIGNS else -1) if recipe == 0 else parity
    )
    if recipe == 0 or seed % 3 == 0:
        offsets = tuple(range(12))
    elif seed % 3 == 1:
        offsets = tuple(i * 5 for i in range(12))
    else:
        offsets = (0, 4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11)
    sequence = tuple((seed + direction * i) % 12 for i in offsets)
    return seed, direction, sequence


def _duration(recipe, sign, lord_sign):
    """Derive count, exception and dignity evidence from one admitted recipe."""
    if recipe == 0:
        count_dir = 1 if sign in _SAVYA_SIGNS else -1
        count = (count_dir * (lord_sign - sign)) % 12 + 1
    else:
        parity_sign = lord_sign if recipe == 1 else sign
        count_dir = 1 if parity_sign % 2 == 0 else -1
        count = (count_dir * (sign - lord_sign)) % 12 + 1
    exception, adjustment = "none", 0
    if lord_sign == sign:
        base, exception = 12, "own_sign_twelve"
    elif recipe == 2 and (lord_sign - sign) % 12 == 6:
        base, exception = 10, "opposite_sign_ten"
    else:
        base = count if recipe == 1 else count - 1
        if recipe == 0:
            exalt = EXALTATION_SIGN[_RASI_LORDS[sign]]
            adjustment = (
                1
                if lord_sign == exalt
                else -1
                if lord_sign == (exalt + 6) % 12
                else 0
            )
    return count_dir, count, base, exception, adjustment


def _arithmetic_rows(signs, sequence, recipe, rule_id):
    """Construct the twelve rows from the admitted recipe's duration derivation."""
    cursor, rows = 0, []
    for ordinal, sign in enumerate(sequence):
        lord = _RASI_LORDS[sign]
        lord_sign = signs[lord]
        count_dir, count, base, exception, adjustment = _duration(
            recipe, sign, lord_sign
        )
        years = base + adjustment
        rows.append(
            CharaArithmeticRow(
                ordinal,
                sign,
                lord,
                lord_sign,
                count_dir,
                count,
                base,
                exception,
                adjustment,
                years,
                cursor,
                cursor + years,
                rule_id,
            )
        )
        cursor += years
    return tuple(rows), cursor


def evaluate_chara_profile(
    chart: JaiminiChart, *, profile_id: str, projection: CharaProjection | None = None
) -> CharaArithmeticResult:
    """Evaluate one explicit manual recipe; sign precision never invents degrees."""
    profile = admit_profile(profile_id, "chara")
    chart = admit_chart(chart, CLASSICAL)
    if projection is not None:
        if type(projection) is not CharaProjection:
            raise ValueError("projection must be a CharaProjection")
        projection = CharaProjection(projection.epoch_jd, projection.projection_id)
    with result_invariants("Chara"):
        signs, lagna = chart_signs(chart)
        recipe = CHARA_IDS.index(profile_id)
        seed, direction, sequence = _sequence(recipe, lagna)
        rows, total = _arithmetic_rows(signs, sequence, recipe, profile.rule_ids[0])
        # Validate arithmetic before using it to admit a caller's calendar epoch.
        arithmetic = CharaArithmeticResult(
            chart, profile, seed, direction, rows, total,
            CharaProfileSchedule("not_requested", None, (), ()),
        )
    if projection is None:
        return arithmetic
    endpoints = tuple(
        (
            r.ordinal,
            projection.epoch_jd + r.start_year * 365.25,
            projection.epoch_jd + r.end_year * 365.25,
        )
        for r in rows
        if r.years
    )
    # Representability is an input-domain restriction, not an internal failure.
    for _, start, end in endpoints:
        finite_number(start, "projected epoch start")
        finite_number(end, "projected epoch end")
        if not start < end:
            raise ValueError("epoch cannot represent positive ordered Chara intervals")
    with result_invariants("Chara"):
        intervals = tuple(CharaProfileInterval(*e) for e in endpoints)
        schedule = CharaProfileSchedule(
            "projected",
            projection,
            intervals,
            tuple(r.ordinal for r in rows if not r.years),
        )
        return CharaArithmeticResult(
            chart, profile, seed, direction, rows, total, schedule
        )
