"""Source-bound topic evidence for KP Vimshottari period lords."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .dasha import VIMSHOTTARI_LEVEL_NAMES, VIMSHOTTARI_YEAR_BASIS, current_dasha
from .julian import jd_from_datetime, utc_to_ut1
from .kp import (
    KPChart, KPLongitude, KPNodeMode, KPProfileId, KPSignificator, KPSignificators,
    _GRAHAS, _kp_utc_datetime, _rank_significators, kp_chart_for_datetime, kp_longitude, kp_significators,
)
from .planets import planet_at
from .spk_reader import KernelReader, get_reader, use_reader_override

__all__ = [
    "KPPeriodPlanetHouses", "KPPeriodHouseMatches", "KPPeriodHouseEvidence",
    "KPPeriodReading", "KPPeriodInterpretation", "KPPeriodWindow", "KPPeriodInterpretationMoment",
    "kp_period_interpretation", "kp_period_interpretation_for_datetime",
]

KPPeriodSubject = Literal["education", "marriage", "service"]
KPPeriodAssessment = Literal["supportive", "adverse", "mixed", "unresolved", "no_topic_indication"]
_SOURCE_REFERENCE = "Krishnamurti Reader III pp. 68–70; Bhatt, Nakshatra Chintamani pp. 22–27, 30, 35–37"
_MAX_LEVELS = 4
_SUBJECT_HOUSES = {
    "education": ((4, 9, 11), (3, 8)),
    "marriage": ((2, 7, 11), (1, 6, 10)),
    "service": ((2, 6, 10), (1, 5, 9)),
}


@dataclass(frozen=True, slots=True)
class KPPeriodPlanetHouses:
    """A natal graha's house occupancy and cusp-sign ownership."""

    planet: str
    occupied_house: int
    owned_houses: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class KPPeriodHouseMatches:
    """The two sets of matching houses for a selected topic."""

    supporting: tuple[int, ...]
    opposing: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class KPPeriodHouseEvidence:
    """A sub lord's direct significator evidence for one topic house."""

    house: int
    significator: KPSignificator


@dataclass(frozen=True, slots=True)
class KPPeriodReading:
    """Star subject matter and sub evidence for one level of the period."""

    level: int
    level_name: str
    period_lord: KPPeriodPlanetHouses
    star_lord: KPPeriodPlanetHouses
    sub_lord: KPPeriodPlanetHouses
    star_matches: KPPeriodHouseMatches
    sub_matches: KPPeriodHouseMatches
    sub_evidence: tuple[KPPeriodHouseEvidence, ...]
    assessment: KPPeriodAssessment


@dataclass(frozen=True, slots=True)
class KPPeriodInterpretation:
    """A sourced house criterion and its evidence for each supplied lord."""

    profile_id: KPProfileId
    method: Literal["bhatt_direct_house_evidence"]
    source_reference: str
    subject: KPPeriodSubject
    supporting_houses: tuple[int, ...]
    opposing_houses: tuple[int, ...]
    readings: tuple[KPPeriodReading, ...]


@dataclass(frozen=True, slots=True)
class KPPeriodWindow:
    """The original half-open canonical Vimshottari interval, in UT1."""

    level: int
    level_name: str
    planet: str
    start_jd_ut1: float
    end_jd_ut1: float
    full_start_jd_ut1: float | None
    full_end_jd_ut1: float | None


@dataclass(frozen=True, slots=True)
class KPPeriodInterpretationMoment:
    """An active Vimshottari line annotated with its natal KP evidence."""

    chart: KPChart
    current_dt_utc: datetime
    current_jd_ut1: float
    year_basis: str
    active_periods: tuple[KPPeriodWindow, ...]
    interpretation: KPPeriodInterpretation | None


def _period_assessment(
    star_matches: KPPeriodHouseMatches, sub_matches: KPPeriodHouseMatches,
) -> KPPeriodAssessment:
    if not (star_matches.supporting or star_matches.opposing):
        return "no_topic_indication"
    if ((star_matches.supporting and star_matches.opposing)
            or (sub_matches.supporting and sub_matches.opposing)):
        return "mixed"
    if sub_matches.opposing:
        return "adverse"
    if star_matches.supporting and sub_matches.supporting:
        return "supportive"
    return "unresolved"


def _interpret_periods(
    planets: Mapping[str, KPLongitude], house_ranks: KPSignificators,
    period_lords: Sequence[str], subject: KPPeriodSubject,
) -> KPPeriodInterpretation:
    supporting, opposing = _SUBJECT_HOUSES[subject]
    topic_houses = set(supporting + opposing)
    placements = {
        point.planet: KPPeriodPlanetHouses(
            point.planet, point.occupied_house,
            tuple(house.house for house in house_ranks.houses if house.cusp_lord == point.planet),
        )
        for point in house_ranks.placements
    }

    def matches(houses: set[int]) -> KPPeriodHouseMatches:
        return KPPeriodHouseMatches(
            tuple(house for house in supporting if house in houses),
            tuple(house for house in opposing if house in houses),
        )

    readings = []
    for level, lord in enumerate(period_lords, 1):
        chain = planets[lord]
        star = placements[chain.star.lord]
        sub = placements[chain.sub.lord]
        star_matches = matches({star.occupied_house, *star.owned_houses})
        sub_evidence = tuple(
            KPPeriodHouseEvidence(house.house, candidate)
            for house in house_ranks.houses if house.house in topic_houses
            for candidate in house.significators if candidate.planet == sub.planet
        )
        sub_matches = matches({link.house for link in sub_evidence})
        readings.append(KPPeriodReading(
            level, VIMSHOTTARI_LEVEL_NAMES[level], placements[lord], star, sub,
            star_matches, sub_matches, sub_evidence, _period_assessment(star_matches, sub_matches),
        ))
    return KPPeriodInterpretation(
        house_ranks.profile_id, "bhatt_direct_house_evidence", _SOURCE_REFERENCE,
        subject, supporting, opposing, tuple(readings),
    )


def kp_period_interpretation(
    *, planet_longitudes: Mapping[str, float], cusp_longitudes: Sequence[float],
    period_lords: Sequence[str], subject: KPPeriodSubject,
    profile_id: KPProfileId = "krishnamurti_moira_placidus",
) -> KPPeriodInterpretation:
    """Interpret a supplied Mahadasha-to-Sookshma line for a named natal topic."""

    if subject not in _SUBJECT_HOUSES:
        raise ValueError("subject must be 'education', 'marriage', or 'service'")
    if not 1 <= len(period_lords) <= _MAX_LEVELS or any(lord not in _GRAHAS for lord in period_lords):
        raise ValueError("period_lords must contain one to four Vimshottari lords, starting at Mahadasha")
    house_ranks = kp_significators(
        planet_longitudes=planet_longitudes, cusp_longitudes=cusp_longitudes, profile_id=profile_id,
    )
    chains = {name: kp_longitude(planet_longitudes[name], profile_id=profile_id) for name in dict.fromkeys(period_lords)}
    return _interpret_periods(chains, house_ranks, period_lords, subject)


def kp_period_interpretation_for_datetime(
    natal_dt: datetime, current_dt: datetime, latitude: float, longitude: float, *,
    node_mode: KPNodeMode, subject: KPPeriodSubject, levels: int = 3, year_basis: str | None = None,
    profile_id: KPProfileId = "krishnamurti_moira_placidus", reader: KernelReader | None = None,
) -> KPPeriodInterpretationMoment:
    """Annotate canonical active Vimshottari periods through the natal KP chart."""

    if subject not in _SUBJECT_HOUSES:
        raise ValueError("subject must be 'education', 'marriage', or 'service'")
    if type(levels) is not int or not 1 <= levels <= _MAX_LEVELS:
        raise ValueError("levels must be an integer in [1, 4]")
    if year_basis is not None and year_basis not in VIMSHOTTARI_YEAR_BASIS:
        raise ValueError("year_basis must be a supported Vimshottari doctrine key")
    current_utc = _kp_utc_datetime(current_dt)
    natal_utc = _kp_utc_datetime(natal_dt)
    if current_utc < natal_utc:
        raise ValueError("current_dt must not be earlier than natal_dt")
    current_jd_ut1 = utc_to_ut1(jd_from_datetime(current_utc))

    chart = kp_chart_for_datetime(
        natal_dt, latitude, longitude, node_mode=node_mode, profile_id=profile_id, reader=reader,
    )
    bound = get_reader() if reader is None else reader
    with use_reader_override(bound):
        tropical_moon = planet_at("Moon", chart.jd_ut1, reader=bound, jd_tt=chart.jd_tt).longitude
        active = current_dasha(
            tropical_moon, chart.jd_ut1, current_jd_ut1, ayanamsa_system=chart.profile.ayanamsa_system,
            year_basis=year_basis, levels=levels,
        )
    windows = tuple(
        KPPeriodWindow(
            period.level, period.level_name, period.planet, period.start_jd, period.end_jd,
            period.full_start_jd, period.full_end_jd,
        )
        for period in active
    )
    interpretation = None
    if chart.cusp_status == "available":
        house_ranks = _rank_significators(chart.planets, chart.cusps, profile_id)
        interpretation = _interpret_periods(chart.planets, house_ranks, [p.planet for p in active], subject)
    return KPPeriodInterpretationMoment(
        chart, current_utc, current_jd_ut1, active[0].year_basis, windows, interpretation,
    )
