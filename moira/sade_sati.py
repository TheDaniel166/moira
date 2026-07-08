"""
Moira — sade_sati.py

Purpose
-------
Sade Sati: Saturn's transit through the 12th, 1st, and 2nd whole-sign
houses from the natal Moon's sidereal rashi (janma rashi) — roughly seven
and a half years, in three phases:

    rising  — Saturn in the 12th from the Moon
    peak    — Saturn in the 1st (over the Moon)
    setting — Saturn in the 2nd

Also flags the two classical shorter Saturn afflictions relative to the
Moon: Ashtama Shani (Saturn in the 8th) and Kantaka Shani (Saturn in the
4th).  Doctrine note (explicit policy): Kantaka Shani has school variants
(some count kendras from the lagna); this module uses the common
Moon-based 4th-house reading and says so.

Governing object
----------------
Whole-sign house counting from the janma rashi in the sidereal zodiac.
Phase timing comes from Saturn's actual sidereal sign ingresses, found by
scanning and bisecting the kernel-computed apparent longitude — so
retrograde re-entries produce separate, honest windows rather than being
collapsed.

Boundary declaration
--------------------
Owns: Sade Sati status and window vessels, phase classification, and the
      Saturn sidereal sign-ingress search.
Delegates: Saturn positions to ``moira.planets.planet_at``; sidereal
      conversion to ``moira.sidereal.tropical_to_sidereal``.

Sources
-------
Standard Jyotish transit doctrine (Sade Sati / Ashtama Shani are
practitioner-canonical; see e.g. Raman's transit writings).  Timing is
Moira-derived from kernel ephemerides, not from tabulated almanacs.
"""

from dataclasses import dataclass

__all__ = [
    "SADE_SATI_PHASES",
    "SadeSatiStatus",
    "SadeSatiWindow",
    "SadeSatiResult",
    "sade_sati_status",
    "sade_sati_windows",
]

# House-from-Moon -> phase name for the three Sade Sati houses.
SADE_SATI_PHASES: dict[int, str] = {
    12: "rising",
    1:  "peak",
    2:  "setting",
}

_SCAN_STEP_DAYS = 5.0      # Saturn moves <= ~0.13°/day; 5 days ≈ 0.65° max
_BISECT_TOL_DAYS = 1e-3    # ~86 s ingress precision


@dataclass(frozen=True, slots=True)
class SadeSatiStatus:
    """
    Instantaneous Sade Sati state of Saturn relative to the natal Moon.

    Attributes
    ----------
    janma_rashi_index : int
        Natal Moon's sidereal sign index (0 = Aries).
    saturn_rashi_index : int
        Saturn's sidereal sign index.
    house_from_moon : int
        Whole-sign house of Saturn counted from the janma rashi (1-12).
    in_sade_sati : bool
        True when Saturn occupies the 12th, 1st, or 2nd from the Moon.
    phase : str or None
        ``'rising'`` | ``'peak'`` | ``'setting'`` when in Sade Sati,
        else ``None``.
    is_ashtama_shani : bool
        Saturn in the 8th from the Moon.
    is_kantaka_shani : bool
        Saturn in the 4th from the Moon (Moon-based variant; see module
        doctrine note).
    """

    janma_rashi_index:  int
    saturn_rashi_index: int
    house_from_moon:    int
    in_sade_sati:       bool
    phase:              str | None
    is_ashtama_shani:   bool
    is_kantaka_shani:   bool

    def __post_init__(self) -> None:
        if not (1 <= self.house_from_moon <= 12):
            raise ValueError(
                f"SadeSatiStatus.house_from_moon must be in [1, 12], "
                f"got {self.house_from_moon}"
            )
        if self.phase is not None and self.phase not in SADE_SATI_PHASES.values():
            raise ValueError(
                f"SadeSatiStatus.phase must be one of "
                f"{sorted(SADE_SATI_PHASES.values())} or None, got {self.phase!r}"
            )


@dataclass(frozen=True, slots=True)
class SadeSatiWindow:
    """
    One contiguous Sade Sati phase window.

    A phase may appear more than once when Saturn retrogrades back across
    a sign boundary — each excursion is its own window.

    Attributes
    ----------
    phase : str
        ``'rising'`` | ``'peak'`` | ``'setting'``.
    sign_index : int
        Saturn's sidereal sign during the window.
    start_jd / end_jd : float
        Window bounds (UT).
    start_is_ingress / end_is_egress : bool
        False when the bound is clamped by the scanned range rather than
        an actual sign crossing.
    """

    phase:            str
    sign_index:       int
    start_jd:         float
    end_jd:           float
    start_is_ingress: bool
    end_is_egress:    bool

    def __post_init__(self) -> None:
        if self.phase not in SADE_SATI_PHASES.values():
            raise ValueError(
                f"SadeSatiWindow.phase must be one of "
                f"{sorted(SADE_SATI_PHASES.values())}, got {self.phase!r}"
            )
        if not (self.start_jd < self.end_jd):
            raise ValueError(
                f"SadeSatiWindow requires start_jd < end_jd, "
                f"got {self.start_jd} >= {self.end_jd}"
            )


@dataclass(frozen=True, slots=True)
class SadeSatiResult:
    """
    Sade Sati windows for one natal Moon over a scanned JD range.

    Attributes
    ----------
    janma_rashi_index : int
    start_jd / end_jd : float
        The scanned range.
    ayanamsa_system : str
    windows : tuple[SadeSatiWindow, ...]
        Chronological phase windows within the range.
    """

    janma_rashi_index: int
    start_jd: float
    end_jd: float
    ayanamsa_system: str
    windows: tuple[SadeSatiWindow, ...]


def _status_from_house(janma_rashi: int, saturn_rashi: int) -> SadeSatiStatus:
    house = (saturn_rashi - janma_rashi) % 12 + 1
    phase = SADE_SATI_PHASES.get(house)
    return SadeSatiStatus(
        janma_rashi_index=janma_rashi,
        saturn_rashi_index=saturn_rashi,
        house_from_moon=house,
        in_sade_sati=phase is not None,
        phase=phase,
        is_ashtama_shani=(house == 8),
        is_kantaka_shani=(house == 4),
    )


def sade_sati_status(
    natal_moon_sidereal_lon: float,
    saturn_sidereal_lon: float,
) -> SadeSatiStatus:
    """
    Classify Saturn's current position relative to the natal Moon.

    Pure whole-sign arithmetic over the two sidereal longitudes; no
    kernel access.  Use ``sade_sati_windows`` for phase timing.
    """
    return _status_from_house(
        int(natal_moon_sidereal_lon % 360.0 // 30),
        int(saturn_sidereal_lon % 360.0 // 30),
    )


def _saturn_sidereal_sign(jd: float, ayanamsa_system: str, reader) -> int:
    from .planets import planet_at
    from .sidereal import tropical_to_sidereal

    lon_trop = planet_at("Saturn", jd, reader=reader).longitude
    return int(tropical_to_sidereal(lon_trop, jd, system=ayanamsa_system) % 360.0 // 30)


def _bisect_sign_change(
    jd_lo: float,
    jd_hi: float,
    sign_lo: int,
    ayanamsa_system: str,
    reader,
) -> float:
    """JD at which Saturn's sidereal sign first differs from *sign_lo*."""
    lo, hi = jd_lo, jd_hi
    while (hi - lo) > _BISECT_TOL_DAYS:
        mid = 0.5 * (lo + hi)
        if _saturn_sidereal_sign(mid, ayanamsa_system, reader) == sign_lo:
            lo = mid
        else:
            hi = mid
    return hi


def sade_sati_windows(
    natal_moon_sidereal_lon: float,
    start_jd: float,
    end_jd: float,
    ayanamsa_system: str = "Lahiri",
    reader=None,
    scan_step_days: float = _SCAN_STEP_DAYS,
) -> SadeSatiResult:
    """
    Find every Sade Sati phase window in ``[start_jd, end_jd]``.

    Saturn's sidereal sign is sampled every *scan_step_days*; each sign
    change is bisected to ~86 s.  Retrograde boundary re-entries yield
    separate windows.  Windows clamped by the range bounds are marked via
    ``start_is_ingress`` / ``end_is_egress``.

    Parameters
    ----------
    natal_moon_sidereal_lon : float
        Natal Moon sidereal longitude (janma rashi source).
    start_jd, end_jd : float
        Scan range (UT Julian dates); ``start_jd < end_jd`` required.
    ayanamsa_system : str
        Ayanamsa for the sidereal frame.  Defaults to ``'Lahiri'``.
    reader : optional
        Kernel reader; defaults to the active reader context.
    scan_step_days : float
        Sampling step.  The default (5 d) bounds Saturn's motion per step
        to well under one degree.

    Returns
    -------
    SadeSatiResult
    """
    if not (start_jd < end_jd):
        raise ValueError(f"start_jd must be < end_jd, got {start_jd} >= {end_jd}")

    janma_rashi = int(natal_moon_sidereal_lon % 360.0 // 30)

    # Build contiguous same-sign segments across the range.
    segments: list[tuple[float, float, int, bool, bool]] = []
    seg_start = start_jd
    seg_sign = _saturn_sidereal_sign(start_jd, ayanamsa_system, reader)
    seg_started_by_ingress = False

    jd = start_jd
    while jd < end_jd:
        jd_next = min(jd + scan_step_days, end_jd)
        sign_next = _saturn_sidereal_sign(jd_next, ayanamsa_system, reader)
        if sign_next != seg_sign:
            crossing = _bisect_sign_change(jd, jd_next, seg_sign, ayanamsa_system, reader)
            segments.append((seg_start, crossing, seg_sign, seg_started_by_ingress, True))
            seg_start = crossing
            seg_sign = _saturn_sidereal_sign(jd_next, ayanamsa_system, reader)
            seg_started_by_ingress = True
        jd = jd_next
    segments.append((seg_start, end_jd, seg_sign, seg_started_by_ingress, False))

    windows: list[SadeSatiWindow] = []
    for s_jd, e_jd, sign, by_ingress, by_egress in segments:
        phase = SADE_SATI_PHASES.get((sign - janma_rashi) % 12 + 1)
        if phase is None or s_jd >= e_jd:
            continue
        windows.append(SadeSatiWindow(
            phase=phase,
            sign_index=sign,
            start_jd=s_jd,
            end_jd=e_jd,
            start_is_ingress=by_ingress,
            end_is_egress=by_egress,
        ))

    return SadeSatiResult(
        janma_rashi_index=janma_rashi,
        start_jd=start_jd,
        end_jd=end_jd,
        ayanamsa_system=ayanamsa_system,
        windows=tuple(windows),
    )
