"""
Hellenistic office hunt: the predominator (prorogator, aphetes) by Ptolemy's
Tetrabiblos III.10, and the house-master (oikodespotes), which stays
unselected.

Never imports Bonatti hyleg or longevity arithmetic.

Predominator doctrine — ``ptolemy_tetrabiblos_iii_10``
-------------------------------------------------------
Source: Ptolemy, *Tetrabiblos* III.10 "Of Length of Life", trans. F. E.
Robbins (Loeb 435, 1940), pp. 271-279, with III.2 (p. 233) for the five
forms of domination and I.18 for the triangles.

* Prorogative (aphetic) places (pp. 271-275): "the twelfth part of the zodiac
  surrounding the horoscope, from 5 deg above the actual horizon up to the
  25 deg that remains"; the part sextile dexter to these thirty degrees (Good
  Daemon); the part in quartile (mid-heaven); the part in trine (House of the
  God); the part opposite (Occident). Taken here as zodiacal thirty-degree
  arcs measured from the ecliptic Ascendant: offset d = (longitude − Asc) mod
  360 lies in [355, 25) orient, [295, 325) Good Daemon, [265, 295)
  mid-heaven, [235, 265) House of the God, [175, 205) Occident (half-open).
  Authority order (p. 273): mid-heaven, orient, Good Daemon, Occident, House
  of the God. Whatever may receive the prorogation must stand in one of
  them ("in which by all means the planet must be").
* Order (pp. 277-279). By day: the Sun if in a prorogative place; else the
  Moon; else "the planet that has most relations of domination to the sun,
  to the preceding conjunction, and to the horoscope ... when, of the five
  methods of domination that exist, it has three to one, or even more"; else
  the horoscope. By night: the Moon; else the Sun; else the planet with most
  relations to the Moon, the preceding full moon and the Lot of Fortune;
  else the horoscope if the preceding syzygy was a new moon, the Lot of
  Fortune if it was a full moon.
* "If both the luminaries ... should be in the prorogative places, we must
  take the one of the luminaries that is in the place of greatest
  authority" — with equal authority the sect order above stands.
* Lot of Fortune (p. 275): Asc + Moon − Sun "both by night and by day".
* The five forms of domination (III.2, p. 233): "trine, house, exaltation,
  term, and phase or aspect". Admitted as: domicile and exaltation of the
  place's sign; the triangle's governor by sect (I.18: fire Sun by day,
  Jupiter by night; earth Venus / Moon; air Saturn / Mercury; water Mars,
  with Venus by day and the Moon by night); Ptolemy's own terms
  (``PTOLEMAIC_BOUNDS``); and a Ptolemaic aspect by sign (sextile, quartile,
  trine, opposition; I.13). "Phase" on its own and co-presence in the sign
  are not counted.
* "We should prefer the ruling planet to both of the luminaries only when it
  both occupies a position of greater authority and bears a relation of
  domination to both the sects" (p. 279): when the ruler found by the ruler
  step stands in a place of greater authority than the chosen luminary, it
  is preferred if it holds at least one of the five forms toward the Sun and
  at least one toward the Moon. "Both the sects" is read as the two sect
  lights (Robbins n. 66 glosses "the proper sect" as diurnal in diurnal
  genitures and nocturnal in nocturnal). This is Moira's reading of an
  ambiguous phrase, named here.
* Ruler step: candidates are the five planets (the luminaries were already
  tried) standing in a prorogative place with at least three of the five
  forms toward at least one of the three places ("three to one"); the one
  with the most forms over the three places is taken.

Fails closed (``not_evaluable`` with a named reason) only where the text
leaves the outcome undetermined:

* ``ruler_step_tie`` — two or more candidates share the highest count.
* ``*_required`` — an input the reached step needs was not supplied (the
  preceding new moon, the preceding full moon, or which syzygy came last).

The preceding full moon is taken as caller-supplied. Ptolemy III.2 takes its
degree from the luminary that was above the earth at the full moon; the
caller supplies that degree.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ._strenum import StrEnum
from .constants import SIGNS
from .dignities import DOMICILE, EXALTATION
from .egyptian_bounds import EgyptianBoundsDoctrine, EgyptianBoundsPolicy, bound_ruler
from .hellenistic import HELLENISTIC_CLASSICAL_PLANETS


OFFICE_NOT_ADMITTED_REASON = "doctrine_not_admitted"
PREDOMINATOR_DOCTRINE_PTOLEMY = "ptolemy_tetrabiblos_iii_10"

__all__ = [
    "OFFICE_NOT_ADMITTED_REASON",
    "PREDOMINATOR_DOCTRINE_PTOLEMY",
    "HellenisticOfficeCandidate",
    "HellenisticOfficeHunt",
    "HellenisticOfficeStatus",
    "PrenatalSyzygyKind",
    "ProrogativePlace",
    "PtolemyDominationCount",
    "PtolemyPlaceTruth",
    "PtolemyPredominatorDetermination",
    "find_predominator_ptolemy",
    "hunt_hellenistic_offices",
]


class HellenisticOfficeStatus(StrEnum):
    """Outcome of the predominator determination."""

    SELECTED = "selected"
    NOT_EVALUABLE = "not_evaluable"


class PrenatalSyzygyKind(StrEnum):
    """Which syzygy came last before the birth."""

    NEW_MOON = "new_moon"
    FULL_MOON = "full_moon"


class ProrogativePlace(StrEnum):
    """Ptolemy's prorogative places, listed in order of authority."""

    MIDHEAVEN = "midheaven"
    ORIENT = "orient"
    GOOD_DAEMON = "good_daemon"
    OCCIDENT = "occident"
    HOUSE_OF_THE_GOD = "house_of_the_god"


_AUTHORITY: tuple[ProrogativePlace, ...] = tuple(ProrogativePlace)

# (start, end) of each place as an offset from the Ascendant, degrees of the
# zodiac in the order of signs; the orient arc wraps through 0.
_PLACE_ARCS: tuple[tuple[ProrogativePlace, float, float], ...] = (
    (ProrogativePlace.ORIENT, 355.0, 25.0),
    (ProrogativePlace.GOOD_DAEMON, 295.0, 325.0),
    (ProrogativePlace.MIDHEAVEN, 265.0, 295.0),
    (ProrogativePlace.HOUSE_OF_THE_GOD, 235.0, 265.0),
    (ProrogativePlace.OCCIDENT, 175.0, 205.0),
)

_FIVE_PLANETS: tuple[str, ...] = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")
_PTOLEMY_TERMS = EgyptianBoundsPolicy(EgyptianBoundsDoctrine.PTOLEMAIC)
_ASPECT_SIGN_DISTANCES = frozenset({2, 3, 4, 6, 8, 9, 10})


@dataclass(frozen=True, slots=True)
class HellenisticOfficeCandidate:
    """One named candidate with only geometric facts."""

    name: str
    kind: str
    longitude: float | None
    house: int | None
    is_sect_light: bool | None
    is_angular: bool | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PtolemyPlaceTruth:
    """Whether a body or point stands in one of Ptolemy's prorogative places."""

    name: str
    longitude: float
    offset_from_ascendant_deg: float
    place: ProrogativePlace | None


@dataclass(frozen=True, slots=True)
class PtolemyDominationCount:
    """One planet's forms of domination toward one reference place."""

    planet: str
    reference: str
    reference_longitude: float
    forms: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.forms)


@dataclass(frozen=True, slots=True)
class PtolemyPredominatorDetermination:
    """Predominator under Ptolemy III.10; ``predominator`` None when not evaluable."""

    doctrine: str
    status: HellenisticOfficeStatus
    predominator: str | None
    predominator_longitude: float | None
    selection_step: str | None
    is_day_chart: bool
    lot_of_fortune_longitude: float
    places: tuple[PtolemyPlaceTruth, ...]
    ruler_counts: tuple[PtolemyDominationCount, ...]
    ruler_candidates: tuple[str, ...]
    reason: str | None

    def __post_init__(self) -> None:
        if self.doctrine != PREDOMINATOR_DOCTRINE_PTOLEMY:
            raise ValueError("unknown predominator doctrine")
        if self.status is HellenisticOfficeStatus.SELECTED:
            if self.predominator is None or self.selection_step is None or self.reason is not None:
                raise ValueError("selected predominator needs a name and a step, and no reason")
        elif self.predominator is not None or not self.reason:
            raise ValueError("not_evaluable predominator needs a reason and no name")


def _offset(longitude: float, asc_longitude: float) -> float:
    return (longitude - asc_longitude) % 360.0


def _prorogative_place(longitude: float, asc_longitude: float) -> ProrogativePlace | None:
    d = _offset(longitude, asc_longitude)
    for place, start, end in _PLACE_ARCS:
        inside = (d >= start or d < end) if start > end else (start <= d < end)
        if inside:
            return place
    return None


def _triangle_governors(sign: str, is_day_chart: bool) -> frozenset[str]:
    element = SIGNS.index(sign) % 4  # 0 fire, 1 earth, 2 air, 3 water
    if element == 0:
        return frozenset({"Sun" if is_day_chart else "Jupiter"})
    if element == 1:
        return frozenset({"Venus" if is_day_chart else "Moon"})
    if element == 2:
        return frozenset({"Saturn" if is_day_chart else "Mercury"})
    return frozenset({"Mars", "Venus" if is_day_chart else "Moon"})


def _domination_forms(
    planet: str,
    planet_longitude: float,
    reference_longitude: float,
    is_day_chart: bool,
) -> tuple[str, ...]:
    ref_index = int((reference_longitude % 360.0) // 30.0)
    sign = SIGNS[ref_index]
    forms: list[str] = []
    if planet in _triangle_governors(sign, is_day_chart):
        forms.append("triangle")
    if sign in DOMICILE.get(planet, []):
        forms.append("house")
    if sign in EXALTATION.get(planet, []):
        forms.append("exaltation")
    if bound_ruler(reference_longitude, policy=_PTOLEMY_TERMS) == planet:
        forms.append("term")
    planet_index = int((planet_longitude % 360.0) // 30.0)
    if (planet_index - ref_index) % 12 in _ASPECT_SIGN_DISTANCES:
        forms.append("aspect")
    return tuple(forms)


def _authority_rank(place: ProrogativePlace) -> int:
    return _AUTHORITY.index(place)


def find_predominator_ptolemy(
    *,
    positions: dict[str, float],
    asc_longitude: float,
    is_day_chart: bool,
    prenatal_new_moon_longitude: float | None = None,
    prenatal_full_moon_longitude: float | None = None,
    latest_prenatal_syzygy: PrenatalSyzygyKind | str | None = None,
) -> PtolemyPredominatorDetermination:
    """
    Predominator (prorogator) by Ptolemy, *Tetrabiblos* III.10.

    ``positions`` must give all seven planets. The syzygy inputs are needed
    only when the procedure reaches the step that uses them; otherwise they
    may be omitted. See the module docstring for the admitted rules and the
    named reasons for ``not_evaluable``.
    """
    if not isinstance(is_day_chart, bool):
        raise TypeError("is_day_chart must be bool")
    if not isinstance(positions, dict):
        raise TypeError("positions must be a dict of body longitudes")
    missing = [name for name in HELLENISTIC_CLASSICAL_PLANETS if name not in positions]
    if missing:
        raise ValueError(f"positions missing: {', '.join(missing)}")
    for name, value in (
        *((n, positions[n]) for n in HELLENISTIC_CLASSICAL_PLANETS),
        ("asc_longitude", asc_longitude),
        ("prenatal_new_moon_longitude", prenatal_new_moon_longitude),
        ("prenatal_full_moon_longitude", prenatal_full_moon_longitude),
    ):
        if value is None and name.startswith("prenatal"):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"{name} must be a finite number")
    latest = None if latest_prenatal_syzygy is None else PrenatalSyzygyKind(latest_prenatal_syzygy)

    asc = float(asc_longitude) % 360.0
    lons = {name: float(positions[name]) % 360.0 for name in HELLENISTIC_CLASSICAL_PLANETS}
    fortune = (asc + lons["Moon"] - lons["Sun"]) % 360.0

    places = tuple(
        PtolemyPlaceTruth(
            name=name,
            longitude=lons[name],
            offset_from_ascendant_deg=_offset(lons[name], asc),
            place=_prorogative_place(lons[name], asc),
        )
        for name in HELLENISTIC_CLASSICAL_PLANETS
    )
    place_of = {truth.name: truth.place for truth in places}

    def result(
        *,
        predominator: str | None = None,
        longitude: float | None = None,
        step: str | None = None,
        reason: str | None = None,
        counts: tuple[PtolemyDominationCount, ...] = (),
        candidates: tuple[str, ...] = (),
    ) -> PtolemyPredominatorDetermination:
        return PtolemyPredominatorDetermination(
            doctrine=PREDOMINATOR_DOCTRINE_PTOLEMY,
            status=(
                HellenisticOfficeStatus.SELECTED
                if predominator is not None
                else HellenisticOfficeStatus.NOT_EVALUABLE
            ),
            predominator=predominator,
            predominator_longitude=longitude,
            selection_step=step,
            is_day_chart=is_day_chart,
            lot_of_fortune_longitude=fortune,
            places=places,
            ruler_counts=counts,
            ruler_candidates=candidates,
            reason=reason,
        )

    # References for the ruler step, by sect.
    if is_day_chart:
        syzygy_name, syzygy_lon = "preceding_new_moon", prenatal_new_moon_longitude
        references_head = (("Sun", lons["Sun"]),)
        references_tail = (("Ascendant", asc),)
    else:
        syzygy_name, syzygy_lon = "preceding_full_moon", prenatal_full_moon_longitude
        references_head = (("Moon", lons["Moon"]),)
        references_tail = (("Lot of Fortune", fortune),)

    def ruler_step() -> tuple[
        tuple[PtolemyDominationCount, ...], tuple[str, ...], str | None
    ]:
        """Counts, the qualifying candidates with the top total, and a missing-input reason."""
        if syzygy_lon is None:
            return (), (), f"prenatal_{syzygy_name.removeprefix('preceding_')}_longitude_required"
        references = (*references_head, (syzygy_name, float(syzygy_lon) % 360.0), *references_tail)
        counts: list[PtolemyDominationCount] = []
        totals: dict[str, int] = {}
        for planet in _FIVE_PLANETS:
            per_place = [
                PtolemyDominationCount(
                    planet=planet,
                    reference=ref_name,
                    reference_longitude=ref_lon,
                    forms=_domination_forms(planet, lons[planet], ref_lon, is_day_chart),
                )
                for ref_name, ref_lon in references
            ]
            counts.extend(per_place)
            if place_of[planet] is not None and max(c.count for c in per_place) >= 3:
                totals[planet] = sum(c.count for c in per_place)
        if not totals:
            return tuple(counts), (), None
        top = max(totals.values())
        return tuple(counts), tuple(p for p in _FIVE_PLANETS if totals.get(p) == top), None

    # Luminaries.
    sect_order = ("Sun", "Moon") if is_day_chart else ("Moon", "Sun")
    in_place = [name for name in sect_order if place_of[name] is not None]
    if in_place:
        if len(in_place) == 2 and _authority_rank(place_of[in_place[1]]) < _authority_rank(place_of[in_place[0]]):
            luminary, step = in_place[1], "luminary_in_place_of_greater_authority"
        elif len(in_place) == 2:
            luminary, step = in_place[0], "sect_light_both_luminaries_in_prorogative_places"
        elif in_place[0] == sect_order[0]:
            luminary, step = in_place[0], "sect_light_in_prorogative_place"
        else:
            luminary, step = in_place[0], "other_luminary_in_prorogative_place"
        luminary_rank = _authority_rank(place_of[luminary])
        outranking = [
            planet for planet in _FIVE_PLANETS
            if place_of[planet] is not None and _authority_rank(place_of[planet]) < luminary_rank
        ]
        if not outranking:
            return result(predominator=luminary, longitude=lons[luminary], step=step)
        counts, candidates, missing_reason = ruler_step()
        if missing_reason is not None:
            return result(reason=f"{missing_reason}_for_ruler_over_luminary_check")
        contenders = [planet for planet in candidates if planet in outranking]
        if len(candidates) > 1 and contenders:
            return result(reason="ruler_step_tie", counts=counts, candidates=candidates)
        if contenders:
            ruler = contenders[0]
            to_sun = _domination_forms(ruler, lons[ruler], lons["Sun"], is_day_chart)
            to_moon = _domination_forms(ruler, lons[ruler], lons["Moon"], is_day_chart)
            if to_sun and to_moon:
                return result(
                    predominator=ruler,
                    longitude=lons[ruler],
                    step="ruler_preferred_over_luminary",
                    counts=counts,
                    candidates=candidates,
                )
        return result(
            predominator=luminary,
            longitude=lons[luminary],
            step=step,
            counts=counts,
            candidates=candidates,
        )

    # Ruler by domination.
    counts, candidates, missing_reason = ruler_step()
    if missing_reason is not None:
        return result(reason=missing_reason)
    if len(candidates) > 1:
        return result(reason="ruler_step_tie", counts=counts, candidates=candidates)
    if len(candidates) == 1:
        ruler = candidates[0]
        return result(
            predominator=ruler,
            longitude=lons[ruler],
            step="ruler_by_domination",
            counts=counts,
            candidates=candidates,
        )

    # Final resort.
    if is_day_chart:
        return result(
            predominator="Ascendant", longitude=asc, step="horoscope_final",
            counts=counts, candidates=candidates,
        )
    if latest is None:
        return result(reason="latest_prenatal_syzygy_required", counts=counts, candidates=candidates)
    if latest is PrenatalSyzygyKind.NEW_MOON:
        return result(
            predominator="Ascendant", longitude=asc, step="horoscope_final_after_new_moon",
            counts=counts, candidates=candidates,
        )
    return result(
        predominator="Lot of Fortune", longitude=fortune, step="lot_of_fortune_final_after_full_moon",
        counts=counts, candidates=candidates,
    )


@dataclass(frozen=True, slots=True)
class HellenisticOfficeHunt:
    """Predominator by Ptolemy III.10; the house-master remains unselected."""

    status: HellenisticOfficeStatus
    predominator: str | None
    house_master: None
    candidates: tuple[HellenisticOfficeCandidate, ...]
    reason: str | None
    predominator_determination: PtolemyPredominatorDetermination | None
    house_master_reason: str = OFFICE_NOT_ADMITTED_REASON

    def __post_init__(self) -> None:
        if self.house_master is not None or self.house_master_reason != OFFICE_NOT_ADMITTED_REASON:
            raise ValueError("HellenisticOfficeHunt cannot select a house-master")
        determination = self.predominator_determination
        if determination is None:
            if self.status is not HellenisticOfficeStatus.NOT_EVALUABLE or self.predominator is not None or not self.reason:
                raise ValueError("without a determination the predominator is not_evaluable with a reason")
            return
        if (
            self.status is not determination.status
            or self.predominator != determination.predominator
            or self.reason != determination.reason
        ):
            raise ValueError("HellenisticOfficeHunt must mirror its predominator determination")


def _place_from_asc(longitude: float, asc_longitude: float) -> int:
    sign = int((longitude % 360.0) // 30.0)
    asc_sign = int((asc_longitude % 360.0) // 30.0)
    return ((sign - asc_sign) % 12) + 1


def hunt_hellenistic_offices(
    *,
    positions: dict[str, float],
    is_day_chart: bool,
    asc_longitude: float | None = None,
    lots: dict[str, float] | None = None,
    prenatal_new_moon_longitude: float | None = None,
    prenatal_full_moon_longitude: float | None = None,
    latest_prenatal_syzygy: PrenatalSyzygyKind | str | None = None,
) -> HellenisticOfficeHunt:
    """
    Office candidates, the predominator by Ptolemy III.10 (see
    ``find_predominator_ptolemy``), and no house-master.

    The predominator needs the Ascendant and all seven planets; without them
    it is ``not_evaluable`` with a named reason. Caller-supplied ``lots`` are
    listed as candidates only; Ptolemy's Lot of Fortune is computed.
    """

    if not isinstance(is_day_chart, bool):
        raise TypeError("is_day_chart must be bool")
    if not isinstance(positions, dict):
        raise TypeError("positions must be a dict of body longitudes")
    sect_light = "Sun" if is_day_chart else "Moon"
    candidates: list[HellenisticOfficeCandidate] = []

    def add(
        name: str,
        kind: str,
        longitude: float | None,
        *,
        missing_reason: str | None = None,
    ) -> None:
        house = None
        angular = None
        if longitude is not None:
            if not isfinite(longitude):
                raise ValueError(f"{name} longitude must be finite")
            longitude = longitude % 360.0
            if asc_longitude is not None:
                if not isfinite(asc_longitude):
                    raise ValueError("asc_longitude must be finite")
                house = _place_from_asc(longitude, asc_longitude)
                angular = house in {1, 4, 7, 10}
        candidates.append(
            HellenisticOfficeCandidate(
                name=name,
                kind=kind,
                longitude=longitude,
                house=house,
                is_sect_light=name == sect_light if kind == "luminary" else None,
                is_angular=angular,
                reason=missing_reason,
            )
        )

    for name in HELLENISTIC_CLASSICAL_PLANETS:
        if name in positions:
            add(name, "luminary" if name in {"Sun", "Moon"} else "planet", positions[name])
        else:
            add(name, "luminary" if name in {"Sun", "Moon"} else "planet", None, missing_reason="longitude_not_supplied")
    if lots:
        for name, longitude in lots.items():
            add(name, "lot", longitude)
    if asc_longitude is not None:
        add("Ascendant", "angle", asc_longitude)
    else:
        add(
            "Ascendant",
            "angle",
            None,
            missing_reason="asc_longitude_not_supplied",
        )

    missing_planets = [name for name in HELLENISTIC_CLASSICAL_PLANETS if name not in positions]
    if asc_longitude is None or missing_planets:
        reason = (
            "asc_longitude_required" if asc_longitude is None
            else "positions_required_for_all_seven_planets"
        )
        return HellenisticOfficeHunt(
            status=HellenisticOfficeStatus.NOT_EVALUABLE,
            predominator=None,
            house_master=None,
            candidates=tuple(candidates),
            reason=reason,
            predominator_determination=None,
        )

    determination = find_predominator_ptolemy(
        positions=positions,
        asc_longitude=asc_longitude,
        is_day_chart=is_day_chart,
        prenatal_new_moon_longitude=prenatal_new_moon_longitude,
        prenatal_full_moon_longitude=prenatal_full_moon_longitude,
        latest_prenatal_syzygy=latest_prenatal_syzygy,
    )
    return HellenisticOfficeHunt(
        status=determination.status,
        predominator=determination.predominator,
        house_master=None,
        candidates=tuple(candidates),
        reason=determination.reason,
        predominator_determination=determination,
    )
