"""
Moira — Jaimini Extended Engine (rasi drishti, arudhas, argala,
karakamsa, Chara Dasha)
=======================================================================

Archetype: Engine

Purpose
-------
The Jaimini techniques beyond karakas.  Jaimini is lineage-riven; every
technique here names its lineage explicitly (Law of Policy Explicitness),
and where the schools genuinely diverge the variant is a policy switch or
a separately named product — never a silent choice.

Techniques and lineages
-----------------------
1. **Rasi drishti** (Upadesa Sutras 1.1.2-4): movable signs aspect the
   fixed signs except the adjacent; fixed aspect movable except the
   adjacent; dual signs aspect each other.  Symmetric.  The one Jaimini
   doctrine common to all lineages — no policy flag.
2. **Arudha padas** (JUS 1.1.30-32): count house→lord, then the same
   count from the lord (always zodiacal).  Exception (Rath/JHora
   lineage, default): a pada landing in the 1st or 7th from its house
   takes the 10th therefrom; the Suryanarain-Rao/Raman lineage reads the
   sutras as illustrations (no exception) — policy
   ``arudha_exception='none'``.  Sc/Aq lordship: classical Mars/Saturn
   (default) or Jaimini co-lords with the PVR §15.5.1 stronger-co-lord
   chain (requires node longitudes) — policy ``arudha_lords``.
3. **Argala** (JUS 1.1.5-10, Rath/PVR reading): primary from the 2nd,
   4th, 11th; secondary from the 5th; virodha pairs 2↔12, 4↔10, 11↔3,
   5↔9; obstruction fails when obstructors are fewer (``na nyuna
   vibalasca`` — count-based here; strength grading is Shadbala's
   domain); two or more malefics in the 3rd cause argala instead of
   virodha; all reckoning anti-zodiacal from a Ketu-occupied sign
   (``viparitam ketoh``).
4. **Karakamsa** (lineage-riven, both products named): the Atmakaraka's
   navamsa sign — read as a lagna in D9 (Rath/PVR/JHora, "svamsa"
   school) or projected onto the rasi chart (K.N. Rao).  The engine
   returns the sign with both applications named; it never collapses
   them.
5. **Chara Dasha** — K.N. Rao's formulation (Neelakantha karika):
   savya = {Ar,Ta,Ge,Li,Sc,Sg}; sequence of 12 contiguous signs from
   the lagna, direction by the 9th-from-lagna's group; length = count
   from dasha sign to its lord (zodiacal for savya signs,
   anti-zodiacal for apasavya) minus one, lord-in-sign = 12; NO
   exaltation/debilitation adjustment (Rao explicitly); Sc/Aq co-lord
   rules with Rao's tie-break (companions → dual>fixed>movable →
   higher degree); antardashas = 12 equal parts in sequence direction
   starting from the sign after the dasha sign (dasha sign last).
   First cycle only — Rao's second-cycle rule could not be verified
   from his book text and is deferred rather than guessed.

Sources
-------
Suryanarain Rao/Raman JUS translation; B.V. Raman "Studies in Jaimini
Astrology" (Arts. 41-42, 78-88); Sanjay Rath "Narayana Dasa" +
srath.com; K.N. Rao (Journal of Astrology); PVR Narasimha Rao "Vedic
Astrology: An Integrated Approach" §§9.2, 10.3-10.7, 15.5; Rangacharya
lineage material.  Sutra numbers cited by named edition (the editions
drift by 1-2 sutras).
"""

from dataclasses import dataclass

__all__ = [
    "JaiminiExtendedPolicy",
    "rasi_aspects",
    "rasi_drishti_of",
    "ArudhaPada",
    "ArudhaResult",
    "arudha_padas",
    "ArgalaHouse",
    "ArgalaResult",
    "argala",
    "Karakamsa",
    "karakamsa",
    "CharaDashaPeriod",
    "CharaDashaResult",
    "chara_dasha",
]

_SEVEN_PLANETS: tuple[str, ...] = (
    'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
)

_RASI_LORDS: tuple[str, ...] = (
    'Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury',
    'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter',
)

# Jaimini co-lords (Rath/PVR lineage) for Scorpio and Aquarius.
_CO_LORDS: dict[int, tuple[str, str]] = {
    7: ('Mars', 'Ketu'),
    10: ('Saturn', 'Rahu'),
}

# Savya ("odd-footed") signs per K.N. Rao's trine-quarter grouping:
# zodiac quarters 1 and 3 — Aries..Gemini and Libra..Sagittarius.
_SAVYA_SIGNS: frozenset[int] = frozenset({0, 1, 2, 6, 7, 8})

_YEAR_DAYS = 365.25


@dataclass(frozen=True, slots=True)
class JaiminiExtendedPolicy:
    """
    Lineage switches (each recorded on the results it governs).

    arudha_exception : str
        ``'rath_tenth'`` (default; pada in 1st/7th from its house takes
        the 10th therefrom — Rath/PVR/JHora) or ``'none'``
        (Suryanarain-Rao/Raman reading: the sutras are illustrations).
    arudha_lords : str
        ``'classical_seven'`` (default; Mars owns Scorpio, Saturn owns
        Aquarius) or ``'jaimini_co_lords'`` (stronger of Mars/Ketu,
        Saturn/Rahu per the PVR §15.5.1 chain; requires node longitudes).
    """

    arudha_exception: str = 'rath_tenth'
    arudha_lords: str = 'classical_seven'

    def __post_init__(self) -> None:
        if self.arudha_exception not in ('rath_tenth', 'none'):
            raise ValueError(
                f"arudha_exception must be 'rath_tenth' or 'none', "
                f"got {self.arudha_exception!r}"
            )
        if self.arudha_lords not in ('classical_seven', 'jaimini_co_lords'):
            raise ValueError(
                f"arudha_lords must be 'classical_seven' or "
                f"'jaimini_co_lords', got {self.arudha_lords!r}"
            )


def _sign(lon: float) -> int:
    return int(lon % 360.0 // 30)


# ---------------------------------------------------------------------------
# 1. Rasi drishti (JUS 1.1.2-4) — common to all lineages
# ---------------------------------------------------------------------------

def rasi_aspects(sign_a: int, sign_b: int) -> bool:
    """
    Whether *sign_a* casts rasi drishti on *sign_b* (and, by symmetry,
    vice versa).

    Movable signs aspect the three fixed signs except the adjacent one;
    fixed signs aspect the three movable signs except the adjacent one;
    dual signs aspect the other dual signs (JUS 1.1.2-4; Raman Arts.
    41-42; Rath; PVR — all lineages agree).
    """
    a, b = sign_a % 12, sign_b % 12
    if a == b:
        return False
    mode_a, mode_b = a % 3, b % 3
    if mode_a == 0 and mode_b == 1:          # movable -> fixed
        return b != (a + 1) % 12             # except the next sign
    if mode_a == 1 and mode_b == 0:          # fixed -> movable
        return b != (a - 1) % 12             # except the previous sign
    if mode_a == 2 and mode_b == 2:          # dual <-> dual
        return True
    return False


def rasi_drishti_of(sign: int) -> frozenset[int]:
    """The set of signs receiving rasi drishti from *sign*."""
    return frozenset(b for b in range(12) if rasi_aspects(sign, b))


# ---------------------------------------------------------------------------
# 2. Arudha padas (JUS 1.1.30-32)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ArudhaPada:
    """
    One house's arudha pada.

    ``label`` is A1..A12 with AL = A1 and UL = A12; ``exception_applied``
    marks the Rath-lineage 10th-therefrom correction.
    """

    house: int
    label: str
    house_sign: int
    lord: str
    lord_sign: int
    computed_sign: int
    pada_sign: int
    exception_applied: bool


@dataclass(frozen=True, slots=True)
class ArudhaResult:
    """All twelve arudha padas plus the lineage that produced them."""

    lagna_sign: int
    padas: dict[int, ArudhaPada]
    arudha_lagna_sign: int      # A1
    upapada_lagna_sign: int     # A12 (UL)
    lineage: str


def _stronger_co_lord(
    sign: int,
    sidereal_longitudes: dict[str, float],
    node_longitudes: dict[str, float],
) -> tuple[str, float]:
    """
    PVR §15.5.1 stronger-co-lord chain for Scorpio/Aquarius, returning
    (lord, its longitude).  Rules applied in order, stopping at the first
    decision; nodes' in-sign advancement is measured from the sign's end.
    """
    primary, node = _CO_LORDS[sign]
    all_lons = dict(sidereal_longitudes)
    all_lons.update(node_longitudes)
    p_lon = all_lons.get(primary)
    n_lon = all_lons.get(node)
    if n_lon is None:
        return primary, p_lon
    p_sign, n_sign = _sign(p_lon), _sign(n_lon)

    # (0) A co-lord in the sign itself: take the other.
    if p_sign == sign and n_sign != sign:
        return node, n_lon
    if n_sign == sign and p_sign != sign:
        return primary, p_lon

    def companions(s: int, excluding: str) -> int:
        return sum(
            1 for p in _SEVEN_PLANETS
            if p != excluding and p in sidereal_longitudes
            and _sign(sidereal_longitudes[p]) == s
        )

    # (1) Joined by more planets.
    cp, cn = companions(p_sign, primary), companions(n_sign, node)
    if cp != cn:
        return (primary, p_lon) if cp > cn else (node, n_lon)

    # (2) Conjoined or rasi-aspected by more of {Jupiter, Mercury,
    #     dispositor}.
    def influence(s: int, planet_name: str) -> int:
        watchers = {'Jupiter', 'Mercury', _RASI_LORDS[s]}
        count = 0
        for w in watchers:
            if w == planet_name or w not in sidereal_longitudes:
                continue
            w_sign = _sign(sidereal_longitudes[w])
            if w_sign == s or rasi_aspects(w_sign, s):
                count += 1
        return count

    ip, in_ = influence(p_sign, primary), influence(n_sign, node)
    if ip != in_:
        return (primary, p_lon) if ip > in_ else (node, n_lon)

    # (3) Exaltation beats non-exaltation (nodes: Rahu exalted Taurus(1),
    #     Ketu Scorpio(7) — the common Rath-school assignment).
    from .vedic_dignities import EXALTATION_SIGN
    node_exalt = {'Rahu': 1, 'Ketu': 7}
    p_ex = p_sign == EXALTATION_SIGN.get(primary)
    n_ex = n_sign == node_exalt.get(node)
    if p_ex != n_ex:
        return (primary, p_lon) if p_ex else (node, n_lon)

    # (4) Sign type of the occupied sign: dual > fixed > movable.
    rank = {2: 3, 1: 2, 0: 1}
    rp, rn = rank[p_sign % 3], rank[n_sign % 3]
    if rp != rn:
        return (primary, p_lon) if rp > rn else (node, n_lon)

    # (5) Greater in-sign advancement (nodes measured from the sign end).
    p_adv = p_lon % 30.0
    n_adv = 30.0 - (n_lon % 30.0)
    return (primary, p_lon) if p_adv >= n_adv else (node, n_lon)


def arudha_padas(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    policy: JaiminiExtendedPolicy | None = None,
    node_longitudes: dict[str, float] | None = None,
) -> ArudhaResult:
    """
    Compute A1-A12 (AL = A1, UL = A12) per JUS 1.1.30: count from the
    house to its lord, then the same count onward from the lord (always
    zodiacal); exception per the policy lineage.
    """
    policy = policy or JaiminiExtendedPolicy()
    lagna_sign = _sign(lagna_sidereal_lon)
    if (policy.arudha_lords == 'jaimini_co_lords'
            and not node_longitudes):
        raise ValueError(
            "arudha_lords='jaimini_co_lords' requires node_longitudes "
            "(Rahu/Ketu)"
        )

    padas: dict[int, ArudhaPada] = {}
    for house in range(1, 13):
        house_sign = (lagna_sign + house - 1) % 12
        if (policy.arudha_lords == 'jaimini_co_lords'
                and house_sign in _CO_LORDS):
            lord, lord_lon = _stronger_co_lord(
                house_sign, sidereal_longitudes, node_longitudes,
            )
        else:
            lord = _RASI_LORDS[house_sign]
            lord_lon = sidereal_longitudes[lord]
        lord_sign = _sign(lord_lon)
        count = (lord_sign - house_sign) % 12          # 0-based steps
        computed = (lord_sign + count) % 12
        offset_from_house = (computed - house_sign) % 12
        exception = (
            policy.arudha_exception == 'rath_tenth'
            and offset_from_house in (0, 6)
        )
        pada = (computed + 9) % 12 if exception else computed
        label = 'AL' if house == 1 else ('UL' if house == 12 else f'A{house}')
        padas[house] = ArudhaPada(
            house=house,
            label=label,
            house_sign=house_sign,
            lord=lord,
            lord_sign=lord_sign,
            computed_sign=computed,
            pada_sign=pada,
            exception_applied=exception,
        )

    lineage = (
        f"exception={policy.arudha_exception} "
        f"(Rath/JHora 10th-therefrom or Raman none); "
        f"lords={policy.arudha_lords}"
    )
    return ArudhaResult(
        lagna_sign=lagna_sign,
        padas=padas,
        arudha_lagna_sign=padas[1].pada_sign,
        upapada_lagna_sign=padas[12].pada_sign,
        lineage=lineage,
    )


# ---------------------------------------------------------------------------
# 3. Argala (JUS 1.1.5-10, Rath/PVR reading)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ArgalaHouse:
    """
    Argala evaluation for one reference sign.

    Each entry maps the intervening relative position (2, 4, 11 primary;
    5 secondary) to the planets casting argala and their obstructors
    (12, 10, 3, 9 respectively).  ``reversed_by_ketu`` marks the
    ``viparitam ketoh`` anti-zodiacal reckoning.
    """

    reference_sign: int
    reversed_by_ketu: bool
    argalas: dict[int, tuple[str, ...]]
    obstructors: dict[int, tuple[str, ...]]
    unobstructed: dict[int, bool]
    malefic_third_argala: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArgalaResult:
    """Argala for all twelve signs from the lagna frame."""

    lagna_sign: int
    houses: dict[int, ArgalaHouse]
    lineage: str


_ARGALA_PAIRS: dict[int, int] = {2: 12, 4: 10, 11: 3, 5: 9}


def argala(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    node_longitudes: dict[str, float] | None = None,
) -> ArgalaResult:
    """
    Evaluate argala/virodha for every sign (as houses from the lagna).

    Primary argala from the 2nd/4th/11th, secondary from the 5th; the
    12th/10th/3rd/9th obstruct respectively; obstruction fails when the
    obstructors are fewer than the causers (count reading of ``na nyuna
    vibalasca`` — strength grading belongs to Shadbala); two or more
    malefics in the 3rd cause argala instead of virodha; a Ketu-occupied
    reference sign reverses the reckoning (JUS 1.1.8/1.1.10).
    """
    from .yogas import benefic_malefic_classification

    lagna_sign = _sign(lagna_sidereal_lon)
    classification = benefic_malefic_classification(sidereal_longitudes)
    occupants: dict[int, list[str]] = {}
    for p in _SEVEN_PLANETS:
        if p in sidereal_longitudes:
            occupants.setdefault(_sign(sidereal_longitudes[p]), []).append(p)
    ketu_sign = (
        _sign(node_longitudes['Ketu'])
        if node_longitudes and 'Ketu' in node_longitudes else None
    )

    houses: dict[int, ArgalaHouse] = {}
    for house in range(1, 13):
        ref = (lagna_sign + house - 1) % 12
        rev = ketu_sign is not None and ref == ketu_sign
        direction = -1 if rev else 1

        def sign_at(offset: int) -> int:
            return (ref + direction * (offset - 1)) % 12

        argalas: dict[int, tuple[str, ...]] = {}
        obstructors: dict[int, tuple[str, ...]] = {}
        unobstructed: dict[int, bool] = {}
        for pos, opp in _ARGALA_PAIRS.items():
            causers = tuple(occupants.get(sign_at(pos), ()))
            blockers = tuple(occupants.get(sign_at(opp), ()))
            argalas[pos] = causers
            obstructors[pos] = blockers
            unobstructed[pos] = bool(causers) and len(blockers) < len(causers)

        third = tuple(occupants.get(sign_at(3), ()))
        malefic_third = tuple(
            p for p in third if classification.get(p) == 'malefic'
        )
        houses[house] = ArgalaHouse(
            reference_sign=ref,
            reversed_by_ketu=rev,
            argalas=argalas,
            obstructors=obstructors,
            unobstructed=unobstructed,
            malefic_third_argala=(
                malefic_third if len(malefic_third) >= 2 else ()
            ),
        )

    return ArgalaResult(
        lagna_sign=lagna_sign,
        houses=houses,
        lineage=(
            "Rath/PVR reading: primary 2/4/11, secondary 5; virodha "
            "2:12, 4:10, 11:3, 5:9; >=2 malefics in the 3rd cause "
            "argala; Ketu reverses reckoning"
        ),
    )


# ---------------------------------------------------------------------------
# 4. Karakamsa (both lineage products, named)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Karakamsa:
    """
    The Atmakaraka's navamsa sign, with both lineage applications named
    (never collapsed): read in D9 (Rath/PVR/JHora) or projected onto the
    rasi chart (K.N. Rao).  ``svamsa_sign`` (the navamsa lagna) is the
    Rath school's companion object; None when no lagna longitude is
    supplied.
    """

    atmakaraka: str
    karakamsa_sign: int
    d9_reading: str
    d1_reading: str
    svamsa_sign: int | None


def karakamsa(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float | None = None,
    scheme: int = 7,
) -> Karakamsa:
    """
    Compute the karakamsa: the Atmakaraka's navamsa sign.

    The AK comes from ``moira.jaimini`` (7- or 8-karaka scheme); the
    navamsa sign from ``moira.varga``.  Both lineage readings are named
    on the result.
    """
    from .jaimini import atmakaraka as _atmakaraka
    from .varga import varga_sign_index

    ak = _atmakaraka(sidereal_longitudes, scheme=scheme)
    kk_sign = varga_sign_index(sidereal_longitudes[ak], 9)
    svamsa = (
        varga_sign_index(lagna_sidereal_lon, 9)
        if lagna_sidereal_lon is not None else None
    )
    return Karakamsa(
        atmakaraka=ak,
        karakamsa_sign=kk_sign,
        d9_reading=(
            "Rath/PVR/JHora: treat this sign as lagna within the navamsa "
            "chart (svamsa school)"
        ),
        d1_reading=(
            "K.N. Rao: apply this sign as a lagna on the rasi chart"
        ),
        svamsa_sign=svamsa,
    )


# ---------------------------------------------------------------------------
# 5. Chara Dasha — K.N. Rao formulation (Neelakantha karika)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CharaDashaPeriod:
    """One Chara mahadasha with its twelve antardashas."""

    sign: int
    years: int
    start_jd: float
    end_jd: float
    lord: str
    lord_note: str
    antardasha_signs: tuple[int, ...]
    antardasha_starts: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class CharaDashaResult:
    """
    First-cycle Chara Dasha (12 mahadashas from the lagna sign).

    Rao's second-cycle rule could not be verified against his book text
    and is deferred, not guessed (recorded here for honesty).
    """

    lagna_sign: int
    direction: int              # +1 zodiacal, -1 anti-zodiacal
    birth_jd: float
    periods: tuple[CharaDashaPeriod, ...]
    lineage: str


def _chara_sign_years(
    sign: int,
    sidereal_longitudes: dict[str, float],
    node_longitudes: dict[str, float] | None,
) -> tuple[int, str, str]:
    """(years, lord, note) for one dasha sign per K.N. Rao's rules."""
    count_dir = 1 if sign in _SAVYA_SIGNS else -1

    def count_to(lord_sign: int) -> int:
        steps = (count_dir * (lord_sign - sign)) % 12
        return steps + 1          # inclusive count, 1..12

    if sign in _CO_LORDS and node_longitudes:
        primary, node = _CO_LORDS[sign]
        lons = dict(sidereal_longitudes)
        lons.update(node_longitudes)
        p_sign = _sign(lons[primary])
        n_sign = _sign(lons[node])
        in_sign = [x for x, s in ((primary, p_sign), (node, n_sign))
                   if s == sign]
        if len(in_sign) == 2:
            return 12, f"{primary}+{node}", "both co-lords in the sign -> 12y"
        if len(in_sign) == 1:
            other = node if in_sign[0] == primary else primary
            other_sign = n_sign if in_sign[0] == primary else p_sign
            years = count_to(other_sign) - 1
            return (years if years > 0 else 12, other,
                    f"{in_sign[0]} in the sign -> count to {other}")
        # Neither in the sign: the stronger (companions -> dual>fixed>
        # movable -> higher degree — Rao's ordering).
        def companions(s: int, excluding: str) -> int:
            return sum(
                1 for p in _SEVEN_PLANETS
                if p != excluding and p in sidereal_longitudes
                and _sign(sidereal_longitudes[p]) == s
            )
        cp, cn = companions(p_sign, primary), companions(n_sign, node)
        if cp != cn:
            lord = primary if cp > cn else node
        else:
            rank = {2: 3, 1: 2, 0: 1}
            rp, rn = rank[p_sign % 3], rank[n_sign % 3]
            if rp != rn:
                lord = primary if rp > rn else node
            else:
                lord = primary if (lons[primary] % 30.0) >= (
                    lons[node] % 30.0) else node
        lord_sign = _sign(lons[lord])
        years = count_to(lord_sign) - 1
        return (years if years > 0 else 12, lord,
                "stronger co-lord (Rao tie-break)")

    lord = _RASI_LORDS[sign]
    lord_sign = _sign(sidereal_longitudes[lord])
    if lord_sign == sign:
        return 12, lord, "lord in its own sign -> 12y"
    years = count_to(lord_sign) - 1
    return years, lord, f"count {'zodiacal' if count_dir == 1 else 'anti-zodiacal'} to {lord}"


def chara_dasha(
    sidereal_longitudes: dict[str, float],
    lagna_sidereal_lon: float,
    birth_jd: float,
    node_longitudes: dict[str, float] | None = None,
) -> CharaDashaResult:
    """
    First-cycle Chara Dasha per K.N. Rao (Neelakantha karika lineage).

    Sequence: 12 contiguous signs from the lagna; direction by the
    9th-from-lagna's savya/apasavya group (the verified Rao/Raman rule —
    NOT the common "savya lagnas run direct" misstatement).  Length:
    count from the dasha sign to its lord minus one (12 when the lord
    is in its own sign); no exaltation/debilitation adjustment.
    Antardashas: 12 equal parts, sequence direction, starting from the
    sign after the dasha sign so the dasha sign operates last.
    Sc/Aq use both lords when ``node_longitudes`` is supplied, else the
    classical Mars/Saturn.
    """
    lagna_sign = _sign(lagna_sidereal_lon)
    ninth_sign = (lagna_sign + 8) % 12
    direction = 1 if ninth_sign in _SAVYA_SIGNS else -1

    sequence = [(lagna_sign + direction * i) % 12 for i in range(12)]
    periods: list[CharaDashaPeriod] = []
    cursor = birth_jd
    for sign in sequence:
        years, lord, note = _chara_sign_years(
            sign, sidereal_longitudes, node_longitudes,
        )
        span = years * _YEAR_DAYS
        ad_signs = tuple(
            (sign + direction * (i + 1)) % 12 for i in range(12)
        )
        ad_len = span / 12.0
        ad_starts = tuple(cursor + i * ad_len for i in range(12))
        periods.append(CharaDashaPeriod(
            sign=sign,
            years=years,
            start_jd=cursor,
            end_jd=cursor + span,
            lord=lord,
            lord_note=note,
            antardasha_signs=ad_signs,
            antardasha_starts=ad_starts,
        ))
        cursor += span

    return CharaDashaResult(
        lagna_sign=lagna_sign,
        direction=direction,
        birth_jd=birth_jd,
        periods=tuple(periods),
        lineage=(
            "K.N. Rao (Neelakantha karika): 9th-from-lagna direction "
            "rule; no exaltation/debilitation adjustment; antardashas "
            "start after the dasha sign (dasha sign last). First cycle "
            "only — Rao's second-cycle rule is unverified and deferred."
        ),
    )
