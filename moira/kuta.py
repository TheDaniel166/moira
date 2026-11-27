"""Source-specific Ashtakoota and Porutham from two sidereal Moon positions."""
from bisect import bisect_right
from dataclasses import dataclass
from typing import Literal

from .daily_panchanga import _finite_number
from .sidereal import NAKSHATRA_NAMES
from .vedic_dignities import _SIGN_RULER

__all__ = ["KutaProfile", "KutaMoon", "KutaFactor", "KutaMatch", "kuta_profiles", "kuta_match"]

KutaProfileId = Literal["charak_ashtakoota", "iyer_porutham_1917"]
FactorStatus = Literal["agreement", "neutral", "disagreement", "cancelled", "unresolved", "scored"]


@dataclass(frozen=True, slots=True)
class KutaProfile:
    """Source and score contract for one matching method."""

    profile_id: KutaProfileId
    source_reference: str
    maximum_points: int | None
    minimum_agreements: int | None


@dataclass(frozen=True, slots=True)
class KutaMoon:
    """A Moon expressed in one caller-selected sidereal frame."""

    longitude: float
    sign_index: int
    nakshatra: str
    nakshatra_index: int
    pada: int


@dataclass(frozen=True, slots=True)
class KutaFactor:
    """A factor with its base result, applied result and rule references."""

    name: str
    bride_category: str
    groom_category: str
    raw_status: FactorStatus
    applied_status: FactorStatus
    rule: str
    exception: str | None = None
    raw_points: float | None = None
    applied_points: float | None = None
    maximum_points: int | None = None


@dataclass(frozen=True, slots=True)
class KutaMatch:
    """The selected source's Moon-only matching result."""

    profile: KutaProfile
    bride: KutaMoon
    groom: KutaMoon
    factors: tuple[KutaFactor, ...]
    total_points: float | None
    confirmed_agreements: int | None


_CHARAK = KutaProfile("charak_ashtakoota", "Charak, Elements of Vedic Astrology, XXVII, pp. 452–462", 36, None)
_IYER = KutaProfile("iyer_porutham_1917", "Iyer, Kalaprakasika (1917), XIII, pp. 68–76", None, 5)

_PADA_STARTS = tuple(i * 10 / 3 for i in range(108))

_VARNA = ("Brahmin", "Kshatriya", "Vaishya", "Shudra")
_VARNA_BY_SIGN = (1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0)
_VASHYA = ("Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta")
_VASHYA_BY_SIGN = (0, 0, 1, 2, 3, 1, 1, 4, 1, 0, 1, 2)
# All matrices are oriented as printed: bride rows, groom columns.
_VASHYA_POINTS = (
    (2, 1, 1, 0.5, 1),
    (1, 2, 0.5, 0, 1),
    (1, 0.5, 2, 1, 1),
    (0, 0, 0, 2, 0),
    (1, 1, 1, 0, 2),
)
_ANIMALS = ("Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat", "Cow",
            "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion")
_YONI = (0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 7, 1)
_YONI_POINTS = (
    (4, 2, 3, 2, 2, 3, 3, 2, 0, 1, 3, 2, 2, 1),
    (2, 4, 3, 2, 2, 3, 2, 3, 3, 1, 3, 2, 2, 0),
    (3, 3, 4, 2, 2, 3, 2, 3, 3, 1, 3, 0, 2, 1),
    (2, 2, 2, 4, 2, 1, 1, 2, 2, 2, 2, 1, 0, 2),
    (2, 2, 2, 2, 4, 1, 1, 2, 2, 2, 0, 2, 2, 2),
    (3, 3, 3, 1, 1, 4, 0, 3, 3, 2, 3, 2, 2, 2),
    (3, 2, 2, 1, 1, 0, 4, 3, 3, 2, 3, 2, 1, 2),
    (2, 3, 3, 2, 2, 3, 3, 4, 3, 0, 3, 2, 2, 1),
    (0, 3, 3, 2, 2, 3, 3, 3, 4, 1, 3, 2, 2, 1),
    (1, 1, 1, 2, 2, 2, 2, 0, 1, 4, 1, 2, 2, 3),
    (3, 3, 3, 2, 0, 3, 3, 3, 3, 1, 4, 2, 2, 1),
    (2, 2, 0, 1, 2, 2, 2, 2, 2, 2, 2, 4, 2, 2),
    (2, 2, 2, 0, 2, 2, 1, 2, 2, 2, 2, 2, 4, 2),
    (1, 0, 1, 2, 2, 2, 2, 1, 1, 3, 1, 2, 2, 4),
)
_LORDS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
_MAITRI_POINTS = (
    (5, 5, 5, 4, 5, 0, 0),
    (5, 5, 4, 1, 4, 0.5, 0.5),
    (5, 4, 5, 0.5, 5, 3, 0.5),
    (4, 1, 0.5, 5, 0.5, 5, 4),
    (5, 4, 5, 0.5, 5, 0.5, 3),
    (0, 0.5, 3, 5, 0.5, 5, 5),
    (0, 0.5, 0.5, 4, 3, 5, 5),
)
_GANA = ("Deva", "Manushya", "Rakshasa")
_GANA_BY_STAR = (0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1, 1, 0)
_GANA_POINTS = ((6, 5, 1), (6, 6, 0), (0, 0, 6))
_NADI = ("Adya", "Madhya", "Antya")
_NADI_BY_STAR = (0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2)

_IYER_FRIENDS = {
    "Sun": {"Jupiter"},
    "Moon": {"Mercury", "Jupiter"},
    "Mars": {"Mercury", "Venus"},
    "Mercury": {"Moon", "Mars", "Jupiter", "Venus", "Saturn"},
    "Jupiter": {"Sun", "Moon", "Mercury", "Venus", "Saturn"},
    "Venus": {"Mars", "Mercury", "Jupiter", "Saturn"},
    "Saturn": {"Sun", "Moon", "Mars", "Mercury", "Venus"},
}
_IYER_VASYA = ((4, 7), (3, 4), (5,), (7, 8), (6,), (2, 11), (9,), (3, 5), (11,), (0, 10), (0,), (9,))
_RAJJU = ("Padha", "Ooroo", "Nabhi", "Kanta", "Siro")
_RAJJU_BY_STAR = (0, 1, 2, 3, 4, 3, 2, 1, 0, 0, 1, 2, 3, 4, 3, 2, 1, 0, 0, 1, 2, 3, 4, 3, 2, 1, 0)
_VEDHA_GROUPS = ((0, 17), (1, 16), (2, 15), (3, 14), (5, 21), (6, 20), (7, 19),
                 (8, 18), (9, 26), (10, 25), (11, 24), (12, 23), (4, 13, 22))
_IYER_YONI_ENEMIES = {(2, 11), (1, 10), (0, 8), (7, 9), (5, 6), (3, 6), (3, 12), (4, 10)}
_IYER_DINA_FAVOURABLE = {(5, 11), (10, 16), (6, 12)}
_IYER_DINA_ADVERSE = {(2, 8), (8, 14), (13, 19), (16, 22), (1, 22), (2, 23), (17, 23), (4, 11), (12, 18)}
_IYER_DINA_SAME_GOOD = {3, 5, 9, 12, 15, 21, 25, 26}
_IYER_DINA_SAME_NEUTRAL = {0, 2, 4, 6, 7, 10, 11, 13, 16, 19, 20}
_IYER_DINA_SAME_SIGN = {(1, 2), (22, 23), (7, 8)}
_IYER_DINA_NEXT = {0, 2, 4, 9, 12, 14, 19, 23}
_IYER_RASI_SIXTH = {(0, 5), (8, 1), (6, 11), (10, 3), (4, 9), (2, 7)}


def kuta_profiles() -> tuple[KutaProfile, ...]:
    """List the independently maintained matching profiles."""

    return _CHARAK, _IYER


def _moon(name: str, longitude: float) -> KutaMoon:
    _finite_number(name, longitude)
    if not 0 <= longitude < 360:
        raise ValueError(f"{name} must be a sidereal longitude in [0, 360)")
    quarter = bisect_right(_PADA_STARTS, longitude) - 1
    star, pada = divmod(quarter, 4)
    return KutaMoon(longitude, int(longitude // 30), NAKSHATRA_NAMES[star], star, pada + 1)


def _count(start: int, end: int, size: int) -> int:
    return (end - start) % size + 1


def _vashya(moon: KutaMoon) -> int:
    second_half = moon.longitude >= moon.sign_index * 30 + 15
    if moon.sign_index == 8 and second_half:
        return 0
    if moon.sign_index == 9 and second_half:
        return 2
    return _VASHYA_BY_SIGN[moon.sign_index]


def _yoni(moon: KutaMoon, *, charak: bool) -> int:
    if charak and 996000 / 3600 <= moon.longitude < 1011200 / 3600:
        return 12
    if not charak and moon.nakshatra_index == 20:
        return 7
    return _YONI[moon.nakshatra_index]


def _score(name, bride, groom, points, maximum, table, exception=None, status: FactorStatus = "scored"):
    return KutaFactor(name, str(bride), str(groom), "scored", status, f"Charak XXVII-{table}",
                      exception, float(points), float(points), maximum)


def _ashtakoota(bride: KutaMoon, groom: KutaMoon) -> tuple[KutaFactor, ...]:
    b, g = bride.nakshatra_index, groom.nakshatra_index
    bs, gs = bride.sign_index, groom.sign_index
    bv, gv = _VARNA_BY_SIGN[bs], _VARNA_BY_SIGN[gs]
    bx, gx = _vashya(bride), _vashya(groom)
    bt, gt = _count(b, g, 27), _count(g, b, 27)
    bad_tara = {3, 5, 7}
    tara = 1.5 * sum(distance % 9 not in bad_tara for distance in (bt, gt))
    by, gy = _yoni(bride, charak=True), _yoni(groom, charak=True)
    bl, gl = _LORDS.index(_SIGN_RULER[bs]), _LORDS.index(_SIGN_RULER[gs])
    bg, gg = _GANA_BY_STAR[b], _GANA_BY_STAR[g]
    bn, gn = _NADI_BY_STAR[b], _NADI_BY_STAR[g]
    sign_distance = _count(bs, gs, 12)
    bhakoota = 0 if sign_distance in {2, 5, 6, 8, 9, 12} else 7
    bhakoota_note = None
    if (sign_distance == 6 and bs % 2 == 1) or (sign_distance == 8 and gs % 2 == 1):
        bhakoota_note = "Charak p. 459(a): mitigated 6/8 from the even sign"
    elif sign_distance == 1 and b != g:
        bhakoota_note = "Charak p. 459(c): shared sign with different stars"
    elif sign_distance in {2, 12} and _MAITRI_POINTS[bl][gl] == 5:
        bhakoota_note = "Charak p. 459(d): friendly or common sign lords mitigate 2/12"
    nadi_note = None
    if bn == gn and (bs == gs) != (b == g):
        nadi_note = ("Charak p. 460(a): same sign, different stars" if bs == gs else
                     "Charak p. 460(b): same star, different signs")
    return (
        _score("varna", _VARNA[bv], _VARNA[gv], gv <= bv, 1, 1),
        _score("vashya", _VASHYA[bx], _VASHYA[gx], _VASHYA_POINTS[bx][gx], 2, 2),
        _score("tara", bt, gt, tara, 3, 3),
        _score("yoni", _ANIMALS[by], _ANIMALS[gy], _YONI_POINTS[by][gy], 4, 4),
        _score("graha_maitri", _LORDS[bl], _LORDS[gl], _MAITRI_POINTS[bl][gl], 5, 5),
        _score("gana", _GANA[bg], _GANA[gg], _GANA_POINTS[bg][gg], 6, 6),
        _score("bhakoota", bs + 1, gs + 1, bhakoota, 7, 7, bhakoota_note),
        _score("nadi", _NADI[bn], _NADI[gn], 8 if bn != gn else 0, 8, 8,
               nadi_note, "cancelled" if nadi_note else "scored"),
    )


def _dina(bride: KutaMoon, groom: KutaMoon, count: int) -> tuple[FactorStatus, FactorStatus, str | None]:
    b, g = bride.nakshatra_index, groom.nakshatra_index
    pair = (b, g)
    first_cycle = count <= 9
    adverse_pada = {12: 1, 14: 4, 16: 3}
    if count in {3, 5, 7, 22, 27} or _count(g, b, 27) == 22 or adverse_pada.get(count) == groom.pada:
        raw: FactorStatus = "disagreement"
    elif first_cycle and count not in {2, 4, 6, 8}:
        raw = "neutral"
    else:
        raw = "agreement"
    if set(pair) == {7, 13}:
        return raw, "unresolved", "Iyer p. 70: the named Chitra–Pushya pair reverses the stated count"
    if pair in _IYER_DINA_FAVOURABLE:
        return raw, "agreement", "Iyer p. 70: named directional seventh-star exception"
    if tuple(sorted(pair)) in _IYER_DINA_ADVERSE:
        return raw, "disagreement", "Iyer p. 70: named adverse pair"
    if b == g:
        if bride.sign_index != groom.sign_index:
            return raw, "unresolved", "Iyer pp. 71–72: conflicting directions for a shared star spanning two signs"
        status: FactorStatus = "disagreement"
        if b in _IYER_DINA_SAME_GOOD:
            status = "agreement"
        elif b in _IYER_DINA_SAME_NEUTRAL:
            status = "neutral"
        return raw, status, "Iyer p. 71: common birth star"
    if count == 27 and bride.sign_index == groom.sign_index:
        return raw, "neutral", "Iyer p. 69: same-sign mitigation of the 27th star"
    if count == 2 and b in _IYER_DINA_NEXT:
        return raw, "agreement", "Iyer p. 71: expressly permitted next star"
    if bride.sign_index == groom.sign_index and tuple(sorted(pair)) not in _IYER_DINA_SAME_SIGN and g > b:
        return raw, "disagreement", "Iyer p. 71: groom's star must precede in a shared sign"
    return raw, raw, None


def _gana(bride: KutaMoon, groom: KutaMoon) -> tuple[str, str, FactorStatus, str | None]:
    b, g = bride.nakshatra_index, groom.nakshatra_index
    bg, gg = _GANA_BY_STAR[b], _GANA_BY_STAR[g]
    unlisted = {11, 19, 20, 24}
    if b in unlisted or g in unlisted:
        return (_GANA[bg] if b not in unlisted else "unlisted",
                _GANA[gg] if g not in unlisted else "unlisted",
                "unresolved", "Iyer p. 72: star absent from the printed Manushya list")
    status: FactorStatus = "agreement" if bg == gg else "neutral" if max(bg, gg) == 1 else "disagreement"
    note = None
    if status == "disagreement" and _count(g, b, 27) > 14:
        note = "Iyer p. 72: Rakshasa mismatch mitigated beyond the 14th star"
    return _GANA[bg], _GANA[gg], status, note


def _porutham(bride: KutaMoon, groom: KutaMoon) -> tuple[KutaFactor, ...]:
    b, g = bride.nakshatra_index, groom.nakshatra_index
    bs, gs = bride.sign_index, groom.sign_index
    bl, gl = _SIGN_RULER[bs], _SIGN_RULER[gs]
    count = _count(b, g, 27)
    distance = _count(bs, gs, 12)
    same_lord = bl == gl
    mutual_friends = gl in _IYER_FRIENDS[bl] and bl in _IYER_FRIENDS[gl]
    potentially_cancelled = same_lord or mutual_friends or distance == 7

    def factor(name, bride_value, groom_value, raw: FactorStatus, pages, *,
               applied: FactorStatus | None = None, exception=None, mutual_exception=False):
        status = raw if applied is None else applied
        if mutual_exception and status == "disagreement" and potentially_cancelled:
            status = "unresolved"
            cancellation = "Iyer p. 76: cancellation clause joins three incompatible conditions"
            exception = f"{exception}. {cancellation}" if exception else cancellation
        return KutaFactor(name, str(bride_value), str(groom_value), raw, status, f"Iyer XIII pp. {pages}", exception)

    def agreement(condition: bool) -> FactorStatus:
        return "agreement" if condition else "disagreement"

    dina_raw, dina_applied, dina_note = _dina(bride, groom, count)
    bg, gg, gana, gana_note = _gana(bride, groom)
    by, gy = _yoni(bride, charak=False), _yoni(groom, charak=False)
    if tuple(sorted((by, gy))) in _IYER_YONI_ENEMIES:
        yoni: FactorStatus = "disagreement"
    else:
        yoni = "agreement" if by == gy else "neutral"
    rasi: FactorStatus = "unresolved" if distance == 1 else agreement(distance >= 7)
    rasi_note = "Iyer pp. 73–74: no same-sign Rasi ruling" if distance == 1 else None
    if (distance == 2 and gs % 2 == 1) or (distance == 6 and (bs, gs) in _IYER_RASI_SIXTH):
        rasi_note = "Iyer p. 74: explicit sign-pair exception"
    rasya: FactorStatus = "agreement" if same_lord or mutual_friends else (
        "neutral" if gl in _IYER_FRIENDS[bl] or bl in _IYER_FRIENDS[gl] else "disagreement"
    )
    br, gr = _RAJJU_BY_STAR[b], _RAJJU_BY_STAR[g]
    vedha = b != g and any(b in group and g in group for group in _VEDHA_GROUPS)
    return (
        factor("dina", count, _count(g, b, 27), dina_raw, "69–72", applied=dina_applied, exception=dina_note),
        factor("gana", bg, gg, gana, "72", exception=gana_note, mutual_exception=True),
        factor("mahendra", bride.nakshatra, count, agreement(count % 3 == 1 and count >= 4), "72"),
        factor("stree_deergha", bride.nakshatra, count, agreement(count > 13), "72"),
        factor("yoni", _ANIMALS[by], _ANIMALS[gy], yoni, "73"),
        factor("rasi", bs + 1, gs + 1, rasi, "73–74", applied="agreement" if rasi_note and distance != 1 else None,
               exception=rasi_note, mutual_exception=True),
        factor("rasyadhipathi", bl, gl, rasya, "74–75"),
        factor("vasya", bs + 1, gs + 1, agreement(gs in _IYER_VASYA[bs] or bs in _IYER_VASYA[gs]), "75"),
        factor("rajju", _RAJJU[br], _RAJJU[gr], agreement(br != gr), "75", mutual_exception=True),
        factor("vedha", bride.nakshatra, groom.nakshatra, agreement(not vedha), "76", mutual_exception=True),
    )


def kuta_match(*, profile_id: KutaProfileId, bride_moon: float, groom_moon: float) -> KutaMatch:
    """Evaluate the requested tradition from two Moons in the same sidereal frame."""

    bride, groom = _moon("bride_moon", bride_moon), _moon("groom_moon", groom_moon)
    if profile_id == _CHARAK.profile_id:
        factors = _ashtakoota(bride, groom)
        return KutaMatch(_CHARAK, bride, groom, factors, sum(f.applied_points or 0.0 for f in factors), None)
    if profile_id == _IYER.profile_id:
        factors = _porutham(bride, groom)
        return KutaMatch(_IYER, bride, groom, factors, None,
                         sum(f.applied_status == "agreement" for f in factors))
    raise ValueError(f"Unknown Kuta profile: {profile_id!r}")
