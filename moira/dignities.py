"""
Dignity Engine — moira/dignities.py

Archetype: Engine
Purpose: Computes essential and accidental planetary dignities for the Classic
         7 planets, including domicile, exaltation, detriment, fall, peregrine,
         house placement, motion, solar proximity (cazimi/combust/sunbeams),
         mutual reception, hayz, and the Almuten Figuris.

Boundary declaration:
    Owns: dignity tables (DOMICILE, EXALTATION, DETRIMENT, FALL), scoring
          constants, hayz/sect logic, mutual reception detection, phasis
          detection, Almuten Figuris computation, and the PlanetaryDignity
          and DignitiesService types.
    Delegates: sign arithmetic to moira.constants.SIGNS; longevity dignity
               scoring to moira.longevity.dignity_score_at (lazy import);
               planetary positions for phasis to moira.planets.planet_at
               (lazy import).

Import-time side effects: None

External dependency assumptions:
    - moira.constants.SIGNS is an ordered list of 12 sign name strings.
    - moira.longevity.dignity_score_at(planet, lon, is_day) is importable
      at call time (lazy import in almuten_figuris).

Public surface / exports:
    PlanetaryDignity      — result dataclass for one planet's dignity state
    DignitiesService      — service class for computing dignities from chart data
    DOMICILE / EXALTATION / DETRIMENT / FALL — essential dignity tables
    SECT / PREFERRED_HEMISPHERE / PREFERRED_GENDER — hayz/sect tables
    is_in_sect()          — sect membership test
    is_in_hayz()          — hayz test (all three sect conditions)
    calculate_dignities() — module-level convenience wrapper
    sect_light()          — determine chart sect light (Sun or Moon)
    is_day_chart()        — boolean day/night test
    almuten_figuris()     — planet with most essential dignities at key points
    mutual_receptions()   — all mutual receptions between Classic 7
    find_phasis()         — phasis (solar beam crossing) events for a planet
"""

from dataclasses import dataclass, field

from .constants import SIGNS


# ---------------------------------------------------------------------------
# Classic 7 planets (essential dignity applies to these only)
# ---------------------------------------------------------------------------

CLASSIC_7: set[str] = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}

# ---------------------------------------------------------------------------
# Essential dignity tables (classic Hellenistic / traditional)
# ---------------------------------------------------------------------------

DOMICILE: dict[str, list[str]] = {
    "Sun":     ["Leo"],
    "Moon":    ["Cancer"],
    "Mercury": ["Gemini", "Virgo"],
    "Venus":   ["Taurus", "Libra"],
    "Mars":    ["Aries", "Scorpio"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Saturn":  ["Capricorn", "Aquarius"],
}

EXALTATION: dict[str, list[str]] = {
    "Sun":     ["Aries"],
    "Moon":    ["Taurus"],
    "Mercury": ["Virgo"],
    "Venus":   ["Pisces"],
    "Mars":    ["Capricorn"],
    "Jupiter": ["Cancer"],
    "Saturn":  ["Libra"],
}

DETRIMENT: dict[str, list[str]] = {
    "Sun":     ["Aquarius"],
    "Moon":    ["Capricorn"],
    "Mercury": ["Sagittarius", "Pisces"],
    "Venus":   ["Scorpio", "Aries"],
    "Mars":    ["Libra", "Taurus"],
    "Jupiter": ["Gemini", "Virgo"],
    "Saturn":  ["Cancer", "Leo"],
}

FALL: dict[str, list[str]] = {
    "Sun":     ["Libra"],
    "Moon":    ["Scorpio"],
    "Mercury": ["Pisces"],
    "Venus":   ["Virgo"],
    "Mars":    ["Cancer"],
    "Jupiter": ["Capricorn"],
    "Saturn":  ["Aries"],
}

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

SCORE_DOMICILE   =  5;  SCORE_EXALTATION =  4
SCORE_DETRIMENT  = -5;  SCORE_FALL       = -4
SCORE_PEREGRINE  =  0

SCORE_ANGULAR    =  4;  SCORE_SUCCEDENT  =  2;  SCORE_CADENT   = -2
SCORE_DIRECT     =  2;  SCORE_RETROGRADE = -5
SCORE_CAZIMI     =  5   # within 17′ of Sun
SCORE_COMBUST    = -5   # within 8°
SCORE_SUNBEAMS   = -4   # 8°–17°
SCORE_MR_DOMICILE   = 5
SCORE_MR_EXALTATION = 4

ANGULAR_HOUSES   = {1, 4, 7, 10}
SUCCEDENT_HOUSES = {2, 5, 8, 11}
CADENT_HOUSES    = {3, 6, 9, 12}

# Traditional planet order for sorting
_PLANET_ORDER = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

# ---------------------------------------------------------------------------
# Hayz / Sect tables
# ---------------------------------------------------------------------------

# Primary sect membership: 'diurnal', 'nocturnal', or 'sect_light' (Mercury)
SECT: dict[str, str] = {
    "Sun":     "diurnal",
    "Jupiter": "diurnal",
    "Saturn":  "diurnal",
    "Moon":    "nocturnal",
    "Venus":   "nocturnal",
    "Mars":    "nocturnal",
    "Mercury": "sect_light",  # changes with Sun: diurnal if it rises/sets before Sun
}

# Preferred hemisphere: 'above' (houses 7–12) or 'below' (houses 1–6)
PREFERRED_HEMISPHERE: dict[str, str] = {
    "Sun":     "above",
    "Jupiter": "above",
    "Saturn":  "above",
    "Moon":    "below",
    "Venus":   "below",
    "Mars":    "above",   # Mars prefers above horizon in day chart; simplified
}

# Masculine signs (fire + air): Aries, Gemini, Leo, Libra, Sagittarius, Aquarius
MASCULINE_SIGNS: set[str] = {
    "Aries", "Gemini", "Leo", "Libra", "Sagittarius", "Aquarius"
}
FEMININE_SIGNS: set[str] = {
    "Taurus", "Cancer", "Virgo", "Scorpio", "Capricorn", "Pisces"
}

# Preferred sign gender (masculine or feminine)
PREFERRED_GENDER: dict[str, str] = {
    "Sun":     "masculine",
    "Jupiter": "masculine",
    "Saturn":  "masculine",
    "Moon":    "feminine",
    "Venus":   "feminine",
    "Mars":    "masculine",
    "Mercury": "either",   # Mercury works in either gender
}


# ---------------------------------------------------------------------------
# Hayz / Sect standalone functions
# ---------------------------------------------------------------------------

def is_in_sect(
    planet: str,
    is_day_chart: bool,
    mercury_rises_before_sun: bool = True,
) -> bool:
    """
    Return True if the planet is in its preferred sect.

    Diurnal planets (Sun, Jupiter, Saturn) are in sect during a day chart.
    Nocturnal planets (Moon, Venus, Mars) are in sect during a night chart.
    Mercury switches: diurnal when it rises or sets before the Sun (Cazimi
    or morning star), nocturnal otherwise.

    Parameters
    ----------
    planet                  : planet name (Classic 7)
    is_day_chart            : True when the Sun is above the horizon (H7–H12)
    mercury_rises_before_sun: True if Mercury is a morning star / heliacal rising
    """
    sect = SECT.get(planet)
    if sect is None:
        return False
    if sect == "diurnal":
        return is_day_chart
    if sect == "nocturnal":
        return not is_day_chart
    # Mercury ("sect_light"): diurnal when rising before Sun, else nocturnal
    mercury_sect = "diurnal" if mercury_rises_before_sun else "nocturnal"
    return mercury_sect == ("diurnal" if is_day_chart else "nocturnal")


def is_in_hayz(
    planet: str,
    sign: str,
    house: int,
    is_day_chart: bool,
    mercury_rises_before_sun: bool = True,
) -> bool:
    """
    Return True if the planet is in hayz (fully satisfying all sect conditions).

    Hayz requires all three conditions to be met simultaneously:
      1. Planet is in its preferred sect (diurnal planet in day chart, or
         nocturnal planet in night chart; Mercury follows heliacal phase).
      2. Planet is in its preferred hemisphere (above horizon = houses 7–12;
         below horizon = houses 1–6).
      3. Planet is in a sign of its preferred gender (masculine = fire/air;
         feminine = earth/water).

    Hayz is traditionally considered the highest form of accidental strength.

    Parameters
    ----------
    planet                  : planet name (Classic 7 only)
    sign                    : current zodiac sign name
    house                   : house number 1–12
    is_day_chart            : True if Sun is above the horizon (H7–H12)
    mercury_rises_before_sun: for Mercury — True if it is a morning star
    """
    if planet not in SECT:
        return False

    # Condition 1: correct sect
    if not is_in_sect(planet, is_day_chart, mercury_rises_before_sun):
        return False

    # Condition 2: preferred hemisphere
    preferred_hemi = PREFERRED_HEMISPHERE.get(planet)
    if preferred_hemi == "above":
        # Above horizon = houses 7 through 12
        in_preferred_hemi = (7 <= house <= 12)
    elif preferred_hemi == "below":
        # Below horizon = houses 1 through 6
        in_preferred_hemi = (1 <= house <= 6)
    else:
        in_preferred_hemi = True  # unknown planet — do not penalise

    if not in_preferred_hemi:
        return False

    # Condition 3: preferred sign gender
    preferred_gender = PREFERRED_GENDER.get(planet)
    if preferred_gender == "masculine":
        in_preferred_gender = sign in MASCULINE_SIGNS
    elif preferred_gender == "feminine":
        in_preferred_gender = sign in FEMININE_SIGNS
    else:
        # Mercury ("either") is content in any sign gender
        in_preferred_gender = True

    return in_preferred_gender


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PlanetaryDignity:
    """
    RITE: The Crowned Planet — the complete dignity portrait of a single
          planet in a chart, from its essential throne to every accidental
          honour or affliction it carries.

    THEOREM: Immutable record of a planet's essential dignity, accidental
             dignities, and composite score, computed from its sign, house,
             motion, solar proximity, and mutual receptions.

    RITE OF PURPOSE:
        PlanetaryDignity is the result vessel of DignitiesService.  It
        consolidates every dignity judgment for one planet into a single
        object so that callers can read the essential dignity label, the
        list of accidental conditions, and the total score without
        re-running any computation.  Without this vessel, dignity results
        would be scattered across multiple parallel lists.

    LAW OF OPERATION:
        Responsibilities:
            - Store planet, sign, degree, house, essential_dignity,
              essential_score, accidental_dignities, accidental_score,
              total_score, and is_retrograde.
            - Render a compact tabular repr.
        Non-responsibilities:
            - Does not compute dignities; that is DignitiesService's role.
            - Does not validate that essential_dignity is a known label.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - None beyond Python builtins.
        Structural invariants:
            - total_score == essential_score + accidental_score.
            - essential_dignity is one of: Domicile, Exaltation, Detriment,
              Fall, Peregrine.

    Canon: William Lilly, Christian Astrology (1647), Book I

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.dignities.PlanetaryDignity",
        "risk": "low",
        "api": {"frozen": ["planet", "sign", "degree", "house", "essential_dignity", "essential_score", "accidental_dignities", "accidental_score", "total_score", "is_retrograde"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    planet:              str
    sign:                str
    degree:              float
    house:               int
    essential_dignity:   str          # "Domicile" | "Exaltation" | "Detriment" | "Fall" | "Peregrine"
    essential_score:     int
    accidental_dignities: list[str]  = field(default_factory=list)
    accidental_score:    int          = 0
    total_score:         int          = 0
    is_retrograde:       bool         = False

    def __repr__(self) -> str:
        acc = ", ".join(self.accidental_dignities) if self.accidental_dignities else "—"
        return (f"{self.planet:<9} {self.sign:<13} H{self.house:2d}  "
                f"{self.essential_dignity:<10} score={self.total_score:+d}  "
                f"[{acc}]")


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class DignitiesService:
    """
    RITE: The Herald of Honours — the Engine that surveys every planet's
          position in the chart and pronounces its essential throne and
          accidental dignities according to classical tradition.

    THEOREM: Governs the computation of essential and accidental dignities
             for all Classic 7 planets found in a chart, returning a sorted
             list of PlanetaryDignity records.

    RITE OF PURPOSE:
        DignitiesService is the computational core of the Dignity Engine.
        It applies the full classical dignity system — essential tables,
        house placement, motion, solar proximity, mutual reception, and
        hayz — to produce a complete dignity portrait of the chart.
        Without this Engine, the dignity tables would be inert data with
        no path to a scored result.

    LAW OF OPERATION:
        Responsibilities:
            - Accept planet_positions and house_positions as plain dicts.
            - Resolve sign, house, essential dignity, and all accidental
              conditions for each Classic 7 planet present.
            - Return a list of PlanetaryDignity sorted in traditional
              planet order (Sun through Saturn).
        Non-responsibilities:
            - Does not compute planetary positions; those are supplied by
              the caller.
            - Does not support outer planets (Uranus, Neptune, Pluto) for
              essential dignities.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.constants.SIGNS for sign name lookup.
        Failure behavior:
            - Missing planets in planet_positions are silently skipped.
            - Malformed house_positions entries default to 0.0.

    Canon: William Lilly, Christian Astrology (1647), Book I;
           Vettius Valens, Anthology (hayz)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.dignities.DignitiesService",
        "risk": "medium",
        "api": {"frozen": ["calculate_dignities"], "internal": ["_get_essential_dignity", "_get_accidental_dignities", "_find_mutual_receptions", "_build_house_cusps", "_get_house"]},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "silent_default"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def calculate_dignities(
        self,
        planet_positions: list[dict],
        house_positions: list[dict],
    ) -> list[PlanetaryDignity]:
        """
        Calculate dignities for all Classic 7 planets found in the chart.

        Parameters
        ----------
        planet_positions : list of dicts with keys:
            - name: str
            - degree: float (tropical ecliptic longitude 0–360)
            - is_retrograde: bool (optional, default False)
        house_positions : list of dicts with keys:
            - number: int (1–12)
            - degree: float (cusp longitude)

        Returns
        -------
        List of PlanetaryDignity, sorted in traditional planet order
        """
        house_cusps = self._build_house_cusps(house_positions)

        planet_lons:  dict[str, float] = {}
        planet_signs: dict[str, str]   = {}
        planet_retro: dict[str, bool]  = {}

        for pos in planet_positions:
            name   = pos.get("name", "").strip().title()
            degree = float(pos.get("degree", 0.0))
            retro  = bool(pos.get("is_retrograde", False))
            planet_lons[name]  = degree
            planet_signs[name] = SIGNS[int(degree // 30) % 12]
            planet_retro[name] = retro

        sun_lon = planet_lons.get("Sun", 0.0)
        mutual_receptions = self._find_mutual_receptions(planet_signs)

        # Determine if this is a day chart: Sun above horizon = houses 7–12
        sun_house = self._get_house(sun_lon, house_cusps) if house_cusps else 1
        is_day_chart = sun_house >= 7

        # Determine Mercury's phase: is it a morning star (rises before Sun)?
        # Use a simple heuristic: Mercury is a morning star when it is behind the Sun
        # (i.e., its longitude is less than the Sun's by up to 90°).
        mercury_lon = planet_lons.get("Mercury", sun_lon)
        mercury_diff = (mercury_lon - sun_lon + 360.0) % 360.0
        mercury_rises_before_sun = mercury_diff > 180.0  # morning star = behind Sun

        results: list[PlanetaryDignity] = []

        for planet in CLASSIC_7:
            if planet not in planet_lons:
                continue

            degree = planet_lons[planet]
            sign   = planet_signs[planet]
            retro  = planet_retro.get(planet, False)
            house  = self._get_house(degree, house_cusps)

            essential, ess_score = self._get_essential_dignity(planet, sign)

            acc_list, acc_score = self._get_accidental_dignities(
                planet=planet,
                house=house,
                is_retrograde=retro,
                planet_lon=degree,
                sun_lon=sun_lon,
                mutual_receptions=mutual_receptions,
                sign=sign,
                is_day_chart=is_day_chart,
                mercury_rises_before_sun=mercury_rises_before_sun,
            )

            results.append(PlanetaryDignity(
                planet=planet,
                sign=sign,
                degree=degree,
                house=house,
                essential_dignity=essential,
                essential_score=ess_score,
                accidental_dignities=acc_list,
                accidental_score=acc_score,
                total_score=ess_score + acc_score,
                is_retrograde=retro,
            ))

        results.sort(key=lambda d: _PLANET_ORDER.index(d.planet)
                     if d.planet in _PLANET_ORDER else 99)
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_essential_dignity(planet: str, sign: str) -> tuple[str, int]:
        if sign in DOMICILE.get(planet, []):    return ("Domicile",   SCORE_DOMICILE)
        if sign in EXALTATION.get(planet, []):  return ("Exaltation", SCORE_EXALTATION)
        if sign in DETRIMENT.get(planet, []):   return ("Detriment",  SCORE_DETRIMENT)
        if sign in FALL.get(planet, []):        return ("Fall",       SCORE_FALL)
        return ("Peregrine", SCORE_PEREGRINE)

    @staticmethod
    def _get_accidental_dignities(
        planet: str,
        house: int,
        is_retrograde: bool,
        planet_lon: float,
        sun_lon: float,
        mutual_receptions: dict[str, list[tuple[str, str]]],
        sign: str = "",
        is_day_chart: bool = True,
        mercury_rises_before_sun: bool = True,
    ) -> tuple[list[str], int]:
        dignities: list[str] = []
        score = 0

        if house in ANGULAR_HOUSES:
            dignities.append(f"Angular (H{house})"); score += SCORE_ANGULAR
        elif house in SUCCEDENT_HOUSES:
            dignities.append(f"Succedent (H{house})"); score += SCORE_SUCCEDENT
        elif house in CADENT_HOUSES:
            dignities.append(f"Cadent (H{house})"); score += SCORE_CADENT

        if is_retrograde:
            dignities.append("Retrograde"); score += SCORE_RETROGRADE
        else:
            dignities.append("Direct"); score += SCORE_DIRECT

        if planet not in ("Sun", "Moon"):
            dist = abs((planet_lon % 360) - (sun_lon % 360))
            dist = min(dist, 360 - dist)
            if dist <= 0.283:
                dignities.append("Cazimi"); score += SCORE_CAZIMI
            elif dist <= 8.0:
                dignities.append("Combust"); score += SCORE_COMBUST
            elif dist <= 17.0:
                dignities.append("Under Sunbeams"); score += SCORE_SUNBEAMS

        for other, rtype in mutual_receptions.get(planet, []):
            if rtype == "domicile":
                dignities.append(f"Mutual Reception ({other})"); score += SCORE_MR_DOMICILE
            elif rtype == "exaltation":
                dignities.append(f"Mutual Exalt. ({other})"); score += SCORE_MR_EXALTATION

        # Hayz: planet fulfils all three sect conditions simultaneously (+2)
        if sign and is_in_hayz(planet, sign, house, is_day_chart, mercury_rises_before_sun):
            dignities.append("In Hayz")
            score += 2

        return dignities, score

    @staticmethod
    def _find_mutual_receptions(
        planet_signs: dict[str, str]
    ) -> dict[str, list[tuple[str, str]]]:
        receptions: dict[str, list[tuple[str, str]]] = {}
        planets = [p for p in planet_signs if p in CLASSIC_7]

        for i, pa in enumerate(planets):
            sign_a = planet_signs[pa]
            for pb in planets[i + 1:]:
                sign_b = planet_signs[pb]
                if sign_a in DOMICILE.get(pb, []) and sign_b in DOMICILE.get(pa, []):
                    receptions.setdefault(pa, []).append((pb, "domicile"))
                    receptions.setdefault(pb, []).append((pa, "domicile"))
                    continue
                if sign_a in EXALTATION.get(pb, []) and sign_b in EXALTATION.get(pa, []):
                    receptions.setdefault(pa, []).append((pb, "exaltation"))
                    receptions.setdefault(pb, []).append((pa, "exaltation"))
        return receptions

    @staticmethod
    def _build_house_cusps(house_positions: list[dict]) -> list[float]:
        cusps = [0.0] * 12
        for pos in house_positions:
            n = pos.get("number", 0)
            if 1 <= n <= 12:
                cusps[n - 1] = float(pos.get("degree", 0.0))
        return cusps

    @staticmethod
    def _get_house(degree: float, cusps: list[float]) -> int:
        degree = degree % 360
        for i in range(12):
            start = cusps[i]
            end   = cusps[(i + 1) % 12]
            if start <= end:
                if start <= degree < end:
                    return i + 1
            else:
                if degree >= start or degree < end:
                    return i + 1
        return 1


# ---------------------------------------------------------------------------
# Module-level convenience wrapper
# ---------------------------------------------------------------------------

_service = DignitiesService()


def calculate_dignities(
    planet_positions: list[dict],
    house_positions: list[dict],
) -> list[PlanetaryDignity]:
    """
    Calculate essential and accidental dignities.

    Parameters
    ----------
    planet_positions : list of {'name': str, 'degree': float, 'is_retrograde': bool}
    house_positions  : list of {'number': int, 'degree': float}
    """
    return _service.calculate_dignities(planet_positions, house_positions)


# ---------------------------------------------------------------------------
# Sect Light
# ---------------------------------------------------------------------------

def sect_light(
    sun_longitude: float,
    asc_longitude: float,
) -> str:
    """
    Determine the sect light of the chart.

    In a diurnal (day) chart, the Sun is above the horizon (houses 7–12),
    and the Sun is the sect light.
    In a nocturnal (night) chart, the Moon is the sect light.

    Parameters
    ----------
    sun_longitude : Sun's ecliptic longitude
    asc_longitude : Ascendant longitude

    Returns
    -------
    "Sun" (day chart) or "Moon" (night chart)
    """
    # In zodiac-order house reckoning, the Sun is above the horizon when it
    # falls in houses 7–12, which corresponds to the arc from Descendant to
    # Ascendant: diff >= 180.
    above = (sun_longitude - asc_longitude) % 360.0 >= 180.0
    return "Sun" if above else "Moon"


def is_day_chart(sun_longitude: float, asc_longitude: float) -> bool:
    """Return True if this is a diurnal (day) chart."""
    return sect_light(sun_longitude, asc_longitude) == "Sun"


# ---------------------------------------------------------------------------
# Almuten Figuris
# ---------------------------------------------------------------------------

def almuten_figuris(
    planet_positions: dict[str, float],
    asc_longitude: float,
    is_day: bool,
) -> str:
    """
    Find the Almuten Figuris — the planet with the most essential dignities
    across the key chart points (Sun, Moon, Ascendant).

    For each of the Classic 7 planets, sum the dignity score it holds at
    the Sun's degree, Moon's degree, and ASC degree.
    The planet with the highest total score is the Almuten Figuris.

    Parameters
    ----------
    planet_positions : dict of body → longitude (must include "Sun", "Moon")
    asc_longitude    : Ascendant longitude
    is_day           : True for day chart (affects triplicity)

    Returns
    -------
    Planet name (string)
    """
    from .longevity import dignity_score_at

    key_points = [
        planet_positions.get("Sun", 0.0),
        planet_positions.get("Moon", 0.0),
        asc_longitude,
    ]

    scores: dict[str, int] = {}
    for planet in CLASSIC_7:
        total = sum(dignity_score_at(planet, lon, is_day) for lon in key_points)
        scores[planet] = total

    return max(scores, key=lambda p: scores[p])


# ---------------------------------------------------------------------------
# Mutual Reception
# ---------------------------------------------------------------------------

def mutual_receptions(
    planet_positions: dict[str, float],
    by_exaltation: bool = False,
) -> list[tuple[str, str, str]]:
    """
    Find all mutual receptions between the Classic 7 planets.

    A mutual reception by domicile occurs when planet A is in a sign ruled
    by planet B AND planet B is in a sign ruled by planet A.
    E.g., Venus in Aries and Mars in Taurus (Mars rules Aries, Venus rules Taurus).

    Parameters
    ----------
    planet_positions : dict of body → tropical longitude (degrees)
    by_exaltation    : also check mutual receptions by exaltation (default False)

    Returns
    -------
    List of (planet_a, planet_b, reception_type) tuples.
    reception_type is "Domicile", "Exaltation", or "Mixed"
    (Mixed = one by domicile, one by exaltation).
    """
    from .constants import SIGNS

    def _sign_of(lon: float) -> str:
        idx = int(lon % 360.0 / 30.0)
        return SIGNS[min(idx, 11)]

    def _domicile_ruler(sign: str) -> list[str]:
        return [p for p, signs in DOMICILE.items() if sign in signs]

    def _exalt_ruler(sign: str) -> list[str]:
        return [p for p, signs in EXALTATION.items() if sign in signs]

    planets = [p for p in planet_positions if p in CLASSIC_7]
    results: list[tuple[str, str, str]] = []
    seen: set[frozenset] = set()

    for i, pa in enumerate(planets):
        for pb in planets[i + 1:]:
            pair = frozenset([pa, pb])
            if pair in seen:
                continue

            sign_a = _sign_of(planet_positions[pa])
            sign_b = _sign_of(planet_positions[pb])

            dom_a = pa in _domicile_ruler(sign_b)   # pa rules sign_b
            dom_b = pb in _domicile_ruler(sign_a)   # pb rules sign_a

            if dom_a and dom_b:
                results.append((pa, pb, "Domicile"))
                seen.add(pair)
                continue

            if by_exaltation:
                ex_a = pa in _exalt_ruler(sign_b)
                ex_b = pb in _exalt_ruler(sign_a)

                if ex_a and ex_b:
                    results.append((pa, pb, "Exaltation"))
                    seen.add(pair)
                elif (dom_a and ex_b) or (ex_a and dom_b):
                    results.append((pa, pb, "Mixed"))
                    seen.add(pair)

    return results


# ---------------------------------------------------------------------------
# Phasis
# ---------------------------------------------------------------------------

def find_phasis(
    body: str,
    jd_start: float,
    jd_end: float,
    reader=None,
    beam_orb: float = 15.0,
    step_days: float = 1.0,
) -> list[dict]:
    """
    Find phasis events for a planet between jd_start and jd_end.

    A "phasis" occurs when a planet crosses the ±beam_orb threshold relative
    to the Sun — transitioning from invisible to visible (emerging) or
    visible to invisible (submerging).

    Parameters
    ----------
    body       : planet name (not Sun or Moon)
    jd_start   : search start JD
    jd_end     : search end JD
    reader     : SpkReader instance (optional; default reader used if None)
    beam_orb   : solar beam orb in degrees (traditional = 15°; combust = 8°)
    step_days  : step size for scanning

    Returns
    -------
    List of dicts: {"jd": float, "event": "Emerging"|"Submerging",
                    "elongation": float}
    """
    from .planets import planet_at
    from .spk_reader import get_reader as _get_reader
    if reader is None:
        reader = _get_reader()

    events = []
    jd = jd_start
    prev_in_beams: bool | None = None

    while jd <= jd_end:
        p = planet_at(body, jd, reader=reader)
        s = planet_at("Sun", jd, reader=reader)
        elong = abs((p.longitude - s.longitude + 180.0) % 360.0 - 180.0)
        in_beams = elong < beam_orb

        if prev_in_beams is not None and in_beams != prev_in_beams:
            # Refine crossing to within 0.5 days via bisection
            t0, t1 = jd - step_days, jd
            for _ in range(10):
                tm = (t0 + t1) / 2
                pm = planet_at(body, tm, reader=reader)
                sm = planet_at("Sun", tm, reader=reader)
                em = abs((pm.longitude - sm.longitude + 180.0) % 360.0 - 180.0)
                if (em < beam_orb) == prev_in_beams:
                    t0 = tm
                else:
                    t1 = tm
            refined_jd = (t0 + t1) / 2
            pm = planet_at(body, refined_jd, reader=reader)
            sm = planet_at("Sun", refined_jd, reader=reader)
            em = abs((pm.longitude - sm.longitude + 180.0) % 360.0 - 180.0)
            event_type = "Emerging" if prev_in_beams else "Submerging"
            events.append({"jd": refined_jd, "event": event_type, "elongation": em})

        prev_in_beams = in_beams
        jd += step_days

    return events
