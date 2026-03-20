"""
Variable Star Oracle — moira/variable_stars.py

Archetype: Oracle
Purpose: Provides brightness-phase calculations and astrological quality
         assessments for astrologically significant variable stars.

Boundary declaration
--------------------
Owns:
    - VarType — class of variable-type string constants (EA, EB, EW, DCEP,
      RRAB, M, SRc, SRb).
    - VariableStar — frozen catalog record for one variable star.
    - _CATALOG — module-level dict of all registered variable stars.
    - phase_at()          — phase [0, 1) at a given JD.
    - magnitude_at()      — estimated V magnitude at a given JD.
    - next_minimum()      — JD of next primary minimum.
    - next_maximum()      — JD of next maximum.
    - minima_in_range()   — all primary minima in a JD range.
    - maxima_in_range()   — all maxima in a JD range.
    - malefic_intensity() — malefic score [0, 1] at a given JD.
    - benefic_strength()  — benefic score [0, 1] at a given JD.
    - is_in_eclipse()     — True if an eclipsing binary is in eclipse.
    - variable_star()     — catalog lookup by name.
    - list_variable_stars() / variable_stars_by_type() — introspection.
    - Algol convenience functions (algol_phase, algol_magnitude, …).
Delegates:
    - Nothing; all computation is self-contained using linear ephemerides.

Import-time side effects:
    - _CATALOG is populated at import time by module-level _reg() calls.
      This is a pure in-memory dict build; no I/O occurs.

External dependency assumptions:
    - No Qt, no database, no OS threads.
    - No external catalog files required.

Public surface / exports:
    VarType, VariableStar
    phase_at(), magnitude_at()
    next_minimum(), next_maximum()
    minima_in_range(), maxima_in_range()
    malefic_intensity(), benefic_strength(), is_in_eclipse()
    variable_star(), list_variable_stars(), variable_stars_by_type()
    algol_phase(), algol_magnitude(), algol_next_minimum(), algol_is_eclipsed()

Classes of variable star handled
---------------------------------
  EA  — Algol-type eclipsing binary: flat light curve with sharp primary
        (and shallow secondary) dip.  Epoch = primary minimum.
  EB  — Beta Lyrae type: continuously varying; contact binary with thick disk.
        Epoch = primary minimum.
  EW  — W UMa type: shallow continuous variation, very short period.
        Epoch = primary minimum.
  DCEP — Classical (δ) Cepheid: asymmetric pulsation, fast rise / slow decline.
        Epoch = maximum light.
  RRAB — RR Lyrae (fundamental mode): very short period, fast rise, slower fall.
        Epoch = maximum light.
  M   — Mira-type long-period variable: slow, very large amplitude.
        Period and epoch are approximate (±weeks); Mira's own period drifts.
        Epoch = maximum light.
  SRc — Semi-regular supergiant (e.g. Betelgeuse, μ Cephei).
        Epoch = maximum light.  Period is a dominant cycle only.
  SRb — Semi-regular (e.g. W Cygni).  Multiple periods interfere; single
        period given is the dominant one.

Catalog sources
---------------
  GCVS (General Catalogue of Variable Stars, Samus+ 2017)
  AAVSO VSX (Variable Star Index)
  Published linear ephemerides (see per-star notes)

Accuracy notes
--------------
  Eclipsing binaries (EA/EB/EW) and Cepheids: epochs and periods are
  precise; computed phases should be correct to minutes.

  Mira and semi-regular variables: periods drift by days to weeks per
  cycle; treat predicted maxima/minima as ±days to ±weeks.  Use AAVSO
  real-time observations for current ephemeris when high precision matters.
"""

import math
from dataclasses import dataclass, field
from collections.abc import Iterator

from .constants import DEG2RAD, RAD2DEG

# ---------------------------------------------------------------------------
# Variable type identifiers
# ---------------------------------------------------------------------------

class VarType:
    """
    RITE: The Typologist's Seal — a namespace of variable-star classification constants.

    THEOREM: Provides string constants identifying the GCVS variability class
    of each supported variable star type.

    RITE OF PURPOSE:
        VarType governs the classification vocabulary used throughout the
        Variable Star Oracle.  Every VariableStar record carries a var_type
        field whose value must be one of these constants.  Without VarType the
        light-curve dispatch in magnitude_at() would rely on bare string
        literals scattered across the module, making the classification contract
        invisible and fragile.

    LAW OF OPERATION:
        Responsibilities:
            - Declare string constants for each supported GCVS variability class.
        Non-responsibilities:
            - Does not compute anything.
            - Does not validate var_type values on VariableStar instances.
            - Does not enumerate all GCVS types — only those with catalog entries.
        Dependencies:
            - None.
        Mutation authority: None — class-level constants only; never instantiated.

    Canon: GCVS (General Catalogue of Variable Stars, Samus+ 2017)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.variable_stars.VarType",
        "id": "moira.variable_stars.VarType",
        "risk": "low",
        "api": {
            "inputs": [],
            "outputs": ["string constants: EA, EB, EW, DCEP, RRAB, M, SRc, SRb"],
            "raises": []
        },
        "state": "stateless",
        "effects": {
            "reads": [],
            "writes": [],
            "signals_emitted": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": "None.",
        "succession": {
            "stance": "terminal",
            "extension_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    ECLIPSING_ALGOL   = "EA"    # Algol type — sharp primary eclipse
    ECLIPSING_BETA    = "EB"    # Beta Lyrae — continuous sinusoidal
    ECLIPSING_W_UMA   = "EW"    # W UMa — shallow rapid contact
    CEPHEID           = "DCEP"  # Classical Cepheid
    RR_LYRAE          = "RRAB"  # RR Lyrae fundamental
    MIRA              = "M"     # Mira long-period
    SEMI_REG_SG       = "SRc"   # Semi-regular supergiant
    SEMI_REG          = "SRb"   # Semi-regular (multiple periods)


# ---------------------------------------------------------------------------
# Data record
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VariableStar:
    """
    RITE: The Pulsing Record — an immutable catalog entry for one variable star.

    THEOREM: Holds the astrometric and photometric parameters needed to compute
    the brightness phase and estimated V magnitude of a variable star at any
    Julian Day.

    RITE OF PURPOSE:
        VariableStar is the internal and public catalog vessel of the Variable
        Star Oracle.  It carries the linear ephemeris (epoch, period), light-
        curve shape parameters (mag_max, mag_min, eclipse_width), and
        astrological metadata (classical_quality, note) for one star.  Without
        it the phase and magnitude engines would have no stable substrate to
        query, and the astrological quality helpers would have no classification
        to act on.

    LAW OF OPERATION:
        Responsibilities:
            - Store all parameters required by phase_at() and magnitude_at().
            - Carry the astrological quality classification and note.
        Non-responsibilities:
            - Does not compute phases or magnitudes.
            - Does not validate field ranges or epoch consistency.
            - Does not perform coordinate lookups (it is not a position type).
        Dependencies:
            - None (pure data container).
        Structural invariants:
            - All fields are set at construction; the instance is immutable.
            - period_days == 0 signals an irregular or unknown period.
        Mutation authority: None — frozen dataclass.

    Canon: GCVS (General Catalogue of Variable Stars, Samus+ 2017);
           AAVSO VSX (Variable Star Index)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.variable_stars.VariableStar",
        "id": "moira.variable_stars.VariableStar",
        "risk": "low",
        "api": {
            "inputs": ["name", "designation", "var_type", "epoch_jd",
                       "epoch_is_minimum", "period_days", "mag_max", "mag_min",
                       "mag_min2", "eclipse_width", "classical_quality", "note"],
            "outputs": ["frozen dataclass instance"],
            "raises": []
        },
        "state": "stateless",
        "effects": {
            "reads": [],
            "writes": [],
            "signals_emitted": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": "None — construction only fails if caller passes wrong types.",
        "succession": {
            "stance": "terminal",
            "extension_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    All magnitudes are Johnson V-band unless noted.
    Epoch reference:
      - EA/EB/EW  : Julian Day of primary minimum
      - DCEP/RRAB : Julian Day of maximum light
      - M/SR*     : Julian Day of maximum light (approximate)
    """
    name:              str    # common/traditional name
    designation:       str    # GCVS / Bayer designation (e.g. "bet Per")
    var_type:          str    # VarType.* constant
    epoch_jd:          float  # reference epoch (JD)
    epoch_is_minimum:  bool   # True if epoch is primary minimum, False if maximum
    period_days:       float  # mean period in days (0 = irregular / unknown)
    mag_max:           float  # V magnitude at maximum (smallest number = brightest)
    mag_min:           float  # V magnitude at primary minimum (faintest)
    mag_min2:          float  # secondary minimum magnitude (EA only; else == mag_max)
    eclipse_width:     float  # primary eclipse half-width in phase units (EA only)
    classical_quality: str    # "malefic", "benefic", "neutral", "mixed"
    note:              str    # astrological and astronomical notes


# ---------------------------------------------------------------------------
# Catalog — astrologically significant variable stars
# ---------------------------------------------------------------------------

_CATALOG: dict[str, VariableStar] = {}

def _reg(star: VariableStar) -> VariableStar:
    _CATALOG[star.name.lower()] = star
    _CATALOG[star.designation.lower()] = star
    return star


# ── Eclipsing Binaries ──────────────────────────────────────────────────────

_reg(VariableStar(
    name="Algol", designation="bet Per",
    var_type=VarType.ECLIPSING_ALGOL,
    epoch_jd=2453600.8877, epoch_is_minimum=True,
    period_days=2.8673075,
    mag_max=2.12, mag_min=3.40, mag_min2=2.20,
    eclipse_width=0.056,          # primary eclipse ~9.6 h / 2.867 d ≈ 0.056 phase
    classical_quality="malefic",
    note=(
        "The Demon Star — head of Medusa.  Ptolemy (Tetrabiblos) called it "
        "the most unfortunate star in the heavens.  At primary minimum the "
        "companion star eclipses the bright primary; the star dims by 1.28 "
        "magnitudes over ~5 hours.  Traditionally most malefic at minimum "
        "(demon fully awake).  Saturn/Mars nature."
    ),
))

_reg(VariableStar(
    name="Sheliak", designation="bet Lyr",
    var_type=VarType.ECLIPSING_BETA,
    epoch_jd=2408247.966, epoch_is_minimum=True,
    period_days=12.91380,
    mag_max=3.25, mag_min=4.36, mag_min2=3.80,
    eclipse_width=0.0,            # EB: continuous, no discrete eclipse width
    classical_quality="mixed",
    note=(
        "Beta Lyrae prototype — a mass-transferring semi-detached binary "
        "whose light curve is continuous; no flat out-of-eclipse plateau. "
        "Associated with the Lyre of Orpheus (benefic music / arts) but "
        "also with strife (the instrument as weapon / seduction).  "
        "Mercury/Venus with Mars overtone."
    ),
))

_reg(VariableStar(
    name="Epsilon Aurigae", designation="eps Aur",
    var_type=VarType.ECLIPSING_ALGOL,
    epoch_jd=2455197.0, epoch_is_minimum=True,  # mid-eclipse Jan 2010
    period_days=9896.0,                          # ~27.1 years
    mag_max=2.92, mag_min=3.83, mag_min2=2.92,
    eclipse_width=0.11,           # eclipse lasts ~2 years of 27-year period ≈ 0.074;
    classical_quality="neutral",
    note=(
        "The longest-known eclipsing binary: a supergiant eclipsed by an "
        "immense dark disk of gas/dust every 27.1 years.  Last eclipse: "
        "2009–2011 (JD 2455000–2455750).  Next eclipse: ~2036–2038.  "
        "A chart moment inside the eclipse occurs only once per generation. "
        "Saturn-like in its slow, inexorable timing."
    ),
))

_reg(VariableStar(
    name="Lambda Tauri", designation="lam Tau",
    var_type=VarType.ECLIPSING_ALGOL,
    epoch_jd=2450001.0, epoch_is_minimum=True,
    period_days=3.952952,
    mag_max=3.37, mag_min=3.91, mag_min2=3.55,
    eclipse_width=0.060,
    classical_quality="neutral",
    note=(
        "Naked-eye eclipsing binary in Taurus near the Pleiades / Hyades "
        "region.  Modest amplitude (0.5 mag).  Taurus associations: "
        "Venus, material accumulation, the throat."
    ),
))

_reg(VariableStar(
    name="VV Cephei", designation="VV Cep",
    var_type=VarType.ECLIPSING_ALGOL,
    epoch_jd=2426011.0, epoch_is_minimum=True,  # reference minimum ~1904
    period_days=7430.5,                          # ~20.3 years
    mag_max=4.80, mag_min=5.40, mag_min2=4.80,
    eclipse_width=0.060,
    classical_quality="neutral",
    note=(
        "One of the largest known stars (supergiant M2) eclipsed by a "
        "smaller hot companion every ~20 years.  The supergiant is ~1900 "
        "solar radii — if placed at the Sun, it would engulf Jupiter.  "
        "Eclipses last ~2 years.  Saturn archetype of vast slow time."
    ),
))

# ── Classical Cepheids ──────────────────────────────────────────────────────

_reg(VariableStar(
    name="Delta Cephei", designation="del Cep",
    var_type=VarType.CEPHEID,
    epoch_jd=2436075.445, epoch_is_minimum=False,  # epoch of maximum
    period_days=5.366249,
    mag_max=3.48, mag_min=4.37, mag_min2=4.37,
    eclipse_width=0.0,
    classical_quality="benefic",
    note=(
        "Prototype of all Cepheid variables; its period-luminosity relation "
        "(Leavitt 1908) became the first rung of the cosmic distance ladder. "
        "Fast rise (~2 days) then slow decline over 3+ days.  In Cepheus, "
        "king of Ethiopia — royal, commanding, leadership cycles.  "
        "Jupiter nature at maximum; Saturn at minimum."
    ),
))

_reg(VariableStar(
    name="Eta Aquilae", designation="eta Aql",
    var_type=VarType.CEPHEID,
    epoch_jd=2437050.682, epoch_is_minimum=False,
    period_days=7.176641,
    mag_max=3.48, mag_min=4.39, mag_min2=4.39,
    eclipse_width=0.0,
    classical_quality="benefic",
    note=(
        "Classical Cepheid in Aquila the Eagle — one of the brightest "
        "Cepheids in the sky.  In the Eagle's wing, near Altair.  "
        "Jupiter/Mercury nature; power and swiftness alternating in "
        "a 7.2-day heartbeat.  Rulers, messengers, divine missions."
    ),
))

_reg(VariableStar(
    name="Zeta Geminorum", designation="zet Gem",
    var_type=VarType.CEPHEID,
    epoch_jd=2443419.773, epoch_is_minimum=False,
    period_days=10.15073,
    mag_max=3.62, mag_min=4.18, mag_min2=4.18,
    eclipse_width=0.0,
    classical_quality="benefic",
    note=(
        "Bright Cepheid in Gemini — the brightest Cepheid north of the "
        "ecliptic.  Near the foot of Pollux.  10.15-day cycle.  "
        "Mercury/Jupiter duality; the twins themselves alternate dominance "
        "as the star pulses.  Strong at maximum when near the feet of Pollux."
    ),
))

_reg(VariableStar(
    name="X Sagittarii", designation="X Sgr",
    var_type=VarType.CEPHEID,
    epoch_jd=2445018.234, epoch_is_minimum=False,
    period_days=7.012705,
    mag_max=4.20, mag_min=4.90, mag_min2=4.90,
    eclipse_width=0.0,
    classical_quality="neutral",
    note=(
        "Cepheid in Sagittarius, close to the Galactic Centre direction. "
        "7-day pulse in the heart of the galaxy — a marker for galactic "
        "centre transits.  Pluto / Sagittarius archetype of deep-space power."
    ),
))

# ── RR Lyrae ────────────────────────────────────────────────────────────────

_reg(VariableStar(
    name="RR Lyrae", designation="RR Lyr",
    var_type=VarType.RR_LYRAE,
    epoch_jd=2447893.498, epoch_is_minimum=False,
    period_days=0.5668352,
    mag_max=7.06, mag_min=8.12, mag_min2=8.12,
    eclipse_width=0.0,
    classical_quality="neutral",
    note=(
        "Prototype of the RR Lyrae class — pulsating horizontal-branch star, "
        "period 13.6 hours, amplitude 1 mag.  Too faint for naked-eye "
        "observation but the prototype of the 'cosmic clock' standard "
        "candle for old stellar populations (globular clusters, galactic halo). "
        "Near Vega in the Lyre; Moon archetype — cyclic, rapid, reliable."
    ),
))

# ── Mira Variables ──────────────────────────────────────────────────────────

_reg(VariableStar(
    name="Mira", designation="omi Cet",
    var_type=VarType.MIRA,
    epoch_jd=2451175.0, epoch_is_minimum=False,   # max ≈ Oct 1999 (approx)
    period_days=331.96,
    mag_max=2.0, mag_min=10.1, mag_min2=10.1,
    eclipse_width=0.0,
    classical_quality="malefic",
    note=(
        "The original Long Period Variable — 'Mira' means 'wonderful' (Fabricius 1596). "
        "At maximum it is among the brightest stars in Cetus; at minimum "
        "it vanishes entirely to naked-eye observers.  Range of 8 magnitudes "
        "= 1600× brightness change.  Period drifts ±10 days per cycle; "
        "predicted maxima can be weeks off.  Cetus = the sea-monster / "
        "Leviathan; Saturn/Mars malefic when near the head.  "
        "But at maximum, some traditions see the 'wonderful' epiphany."
    ),
))

_reg(VariableStar(
    name="Chi Cygni", designation="chi Cyg",
    var_type=VarType.MIRA,
    epoch_jd=2450870.0, epoch_is_minimum=False,   # max ≈ Jul 1998 (approx)
    period_days=407.6,
    mag_max=3.3, mag_min=14.2, mag_min2=14.2,
    eclipse_width=0.0,
    classical_quality="benefic",
    note=(
        "Largest amplitude Mira with a naked-eye maximum — the range of 10.9 "
        "magnitudes (mag 3.3 → 14.2) is one of the greatest of any variable "
        "star.  In the neck of Cygnus the Swan.  At maximum: a first-magnitude "
        "star rivalling Deneb; at minimum: invisible in a medium amateur "
        "telescope.  The Swan archetype: Apollonian music/poetry at maximum, "
        "silence/death at minimum.  Jupiter at peak."
    ),
))

_reg(VariableStar(
    name="R Leonis", designation="R Leo",
    var_type=VarType.MIRA,
    epoch_jd=2451120.0, epoch_is_minimum=False,   # max ≈ Aug 1999 (approx)
    period_days=309.95,
    mag_max=4.4, mag_min=11.3, mag_min2=11.3,
    eclipse_width=0.0,
    classical_quality="benefic",
    note=(
        "Mira variable near Regulus in Leo — within 5° of the Royal Star. "
        "At maximum it reaches naked-eye visibility and can approach "
        "conjunction with Regulus in the ecliptic frame.  The Lion's 'hidden "
        "star' that appears and disappears.  Sun/Jupiter nature at maximum; "
        "depleted at minimum.  Watch for R Leo maximum near Regulus transits."
    ),
))

_reg(VariableStar(
    name="R Hydrae", designation="R Hya",
    var_type=VarType.MIRA,
    epoch_jd=2449700.0, epoch_is_minimum=False,   # approx
    period_days=388.87,
    mag_max=3.5, mag_min=10.9, mag_min2=10.9,
    eclipse_width=0.0,
    classical_quality="malefic",
    note=(
        "Mira in Hydra — the multi-headed water serpent of Heracles.  "
        "Near Alphard ('the solitary one'), the only bright star in Hydra.  "
        "At maximum, briefly visible to the naked eye in this otherwise "
        "sparse region.  Saturn/Mars malefic (Hydra archetype).  "
        "Note: R Hydrae's period has been shortening over the past century "
        "(from 495 days in 1770 to 389 today) — it is evolving in real time."
    ),
))

_reg(VariableStar(
    name="T Cephei", designation="T Cep",
    var_type=VarType.MIRA,
    epoch_jd=2450800.0, epoch_is_minimum=False,   # approx
    period_days=388.14,
    mag_max=5.2, mag_min=11.3, mag_min2=11.3,
    eclipse_width=0.0,
    classical_quality="neutral",
    note=(
        "Mira in Cepheus, the royal constellation.  Deep red M-type giant; "
        "appears blood-orange at maximum.  Royal archetype: the king's "
        "power waxes and wanes on a 13-month cycle.  Saturn / Mars quality "
        "of the red color vs. royal Jupiter significance of Cepheus."
    ),
))

_reg(VariableStar(
    name="R Carinae", designation="R Car",
    var_type=VarType.MIRA,
    epoch_jd=2449400.0, epoch_is_minimum=False,   # approx
    period_days=308.71,
    mag_max=3.9, mag_min=10.5, mag_min2=10.5,
    eclipse_width=0.0,
    classical_quality="benefic",
    note=(
        "Southern Mira in Carina — part of the old Argo Navis.  At maximum, "
        "a bright red star in the ship's keel.  The Argo (Jason's quest for "
        "the Golden Fleece) gives it a Sun/Jupiter / heroic-journey quality "
        "at maximum.  Invisible at minimum — the ship sinks below the horizon "
        "of perception."
    ),
))

# ── Semi-regular Supergiants ────────────────────────────────────────────────

_reg(VariableStar(
    name="Betelgeuse", designation="alp Ori",
    var_type=VarType.SEMI_REG_SG,
    epoch_jd=2451545.0, epoch_is_minimum=False,   # J2000 baseline
    period_days=417.0,                             # dominant ~417-day pulsation
    mag_max=0.0, mag_min=1.3, mag_min2=1.3,
    eclipse_width=0.0,
    classical_quality="malefic",
    note=(
        "Red supergiant in Orion — one of the largest stars known (~700 R☉). "
        "Multiple periodicities: ~417 days (fundamental), ~2100 days (long "
        "secondary).  The 2019-2020 'Great Dimming' (to magnitude 1.6) was "
        "caused by a mass-ejection event.  Mars/Mercury malefic (Ptolemy); "
        "violence, rashness, but also martial heroism at maximum brightness. "
        "A future supernova candidate — its eventual explosion will be "
        "visible in daylight from Earth.  Single period given is dominant; "
        "actual behaviour is multi-period and irregular."
    ),
))

_reg(VariableStar(
    name="Mu Cephei", designation="mu Cep",
    var_type=VarType.SEMI_REG_SG,
    epoch_jd=2451000.0, epoch_is_minimum=False,
    period_days=730.0,
    mag_max=3.4, mag_min=5.1, mag_min2=5.1,
    eclipse_width=0.0,
    classical_quality="malefic",
    note=(
        "The Garnet Star (Herschel's name) — one of the reddest naked-eye "
        "stars.  An extreme red supergiant ~1650 R☉, near the upper limit "
        "of stellar size.  Two dominant cycles (~730 d and ~4400 d) "
        "interfere to produce its semi-regular variation.  Deep crimson "
        "colour → Mars/Saturn malefic, bloodshed, intensity, deep time.  "
        "Its redness was noted by ancient observers in Cepheus."
    ),
))

_reg(VariableStar(
    name="W Cygni", designation="W Cyg",
    var_type=VarType.SEMI_REG,
    epoch_jd=2451000.0, epoch_is_minimum=False,
    period_days=131.0,
    mag_max=5.0, mag_min=7.6, mag_min2=7.6,
    eclipse_width=0.0,
    classical_quality="neutral",
    note=(
        "Semi-regular variable in Cygnus with a dominant ~131-day period. "
        "M-type giant; moderate amplitude.  In the Swan's body.  "
        "Apollo / music archetype; Jupiter quality at maximum."
    ),
))

_reg(VariableStar(
    name="Antares", designation="alp Sco",
    var_type=VarType.SEMI_REG_SG,
    epoch_jd=2451545.0, epoch_is_minimum=False,
    period_days=1733.0,                           # ~4.75-year dominant cycle
    mag_max=0.6, mag_min=1.6, mag_min2=1.6,
    eclipse_width=0.0,
    classical_quality="malefic",
    note=(
        "The Rival of Mars (anti-Ares) — one of the four Royal Stars of "
        "Persia (Watcher of the West).  Red supergiant, variability modest "
        "but real.  Dominant period ~1733 days (~4.75 years), but irregular. "
        "Even at minimum it is prominent; the variability adds a Mars "
        "intensity pulse to its already malefic character.  Watch for "
        "Antares near maximum when it transits natal charts."
    ),
))


# ---------------------------------------------------------------------------
# Phase and light curve
# ---------------------------------------------------------------------------

def phase_at(star: VariableStar, jd: float) -> float:
    """
    Return the phase (0.0–1.0) of a variable star at a given JD.

    Phase convention:
      - EA/EB/EW : 0.0 = primary minimum (faintest)
      - DCEP/RRAB: 0.0 = maximum light (brightest)
      - M/SR*    : 0.0 = maximum light (brightest)

    Parameters
    ----------
    star : VariableStar record
    jd   : Julian Day (TT or UT — difference negligible at this precision)

    Returns
    -------
    Phase in [0.0, 1.0)
    """
    if star.period_days <= 0.0:
        return 0.0
    return ((jd - star.epoch_jd) / star.period_days) % 1.0


def magnitude_at(star: VariableStar, jd: float) -> float:
    """
    Estimate the V magnitude of a variable star at a given JD.

    Uses simplified light curve models appropriate to each type.
    Accuracy: ~0.05–0.2 mag for EA/Cepheids; ~0.5–1.5 mag for Mira/SR types.

    Parameters
    ----------
    star : VariableStar record
    jd   : Julian Day

    Returns
    -------
    Estimated V magnitude (Johnson)
    """
    phi = phase_at(star, jd)

    if star.var_type == VarType.ECLIPSING_ALGOL:
        return _ea_magnitude(phi, star.mag_max, star.mag_min, star.mag_min2,
                             star.eclipse_width)

    elif star.var_type in (VarType.ECLIPSING_BETA, VarType.ECLIPSING_W_UMA):
        # Continuous sinusoidal (two minima per cycle at phase 0 and 0.5)
        # Primary min at phi=0, secondary at phi=0.5
        mag_range = star.mag_min - star.mag_max
        # cos² model: 0 at phi=0/1, +1 at phi=0.5
        depth = mag_range * 0.5 * (1.0 - math.cos(2.0 * math.pi * phi))
        # Secondary minimum at phi=0.5 slightly shallower
        sec_depth = (star.mag_min2 - star.mag_max) * 0.5 * (
            1.0 - math.cos(2.0 * math.pi * (phi + 0.5))
        )
        return star.mag_max + max(depth, sec_depth * 0.6)

    elif star.var_type == VarType.CEPHEID:
        # Asymmetric sawtooth: fast rise (10% of period), slow decline (90%)
        # Phase 0 = maximum
        rise_frac = 0.10
        if phi <= rise_frac:
            # On the way up — but since phase=0 is MAX, this is the tail of
            # the previous cycle.  Reframe: phase 0 = max, 0→rise_frac is
            # declining slightly from peak before the rapid rise at end.
            # Standard Cepheid: rise from minimum to max is fast;
            # let phase (1-rise_frac)→1 be the rapid rise.
            t = phi / (1.0 - rise_frac)  # normalise decline
            return star.mag_max + (star.mag_min - star.mag_max) * t
        else:
            # Rapid rise portion: phi = (1-rise_frac) → 1 remapped
            # This simplified model: decline only.
            t = (phi - rise_frac) / (1.0 - rise_frac)
            # Slow decline using a sin-curve shape
            return star.mag_max + (star.mag_min - star.mag_max) * math.sin(
                0.5 * math.pi * t
            )

    elif star.var_type == VarType.RR_LYRAE:
        # Very similar to Cepheid but even faster rise (~5% of period)
        rise_frac = 0.05
        if phi <= rise_frac:
            t = phi / rise_frac
            # Near maximum: small decline from exact max
            return star.mag_max + (star.mag_min - star.mag_max) * 0.05 * t
        else:
            t = (phi - rise_frac) / (1.0 - rise_frac)
            return star.mag_max + (star.mag_min - star.mag_max) * math.sin(
                0.5 * math.pi * t
            )

    else:
        # Mira and semi-regular: sinusoidal approximation
        # Phase 0 = maximum
        return star.mag_max + (star.mag_min - star.mag_max) * 0.5 * (
            1.0 - math.cos(2.0 * math.pi * phi)
        )


def _ea_magnitude(
    phi: float,
    mag_max: float,
    mag_min: float,
    mag_min2: float,
    hw: float,
) -> float:
    """
    EA light curve: flat at mag_max with a primary eclipse at phi=0
    and a shallower secondary at phi=0.5.

    hw : half-width of the primary eclipse in phase units
    """
    # Fold to [0, 0.5] — symmetric about phi=0 and phi=0.5
    p = phi if phi <= 0.5 else 1.0 - phi

    # Primary eclipse: centred on phi=0 (p=0 after fold)
    if p < hw:
        depth = (hw - p) / hw            # 1 at centre, 0 at contact
        # Trapezoid: linear ingress/egress with a flat bottom for p < hw*0.3
        if p < hw * 0.3:
            depth = 1.0
        else:
            depth = (hw - p) / (hw * 0.7)
        depth = max(0.0, min(1.0, depth))
        return mag_max + depth * (mag_min - mag_max)

    # Secondary eclipse: centred on phi=0.5 (p=0 after the second fold)
    p2 = abs(phi - 0.5)
    sec_hw = hw * 0.8          # secondary eclipse usually slightly narrower
    if p2 < sec_hw:
        depth2 = (sec_hw - p2) / sec_hw
        depth2 = max(0.0, min(1.0, depth2))
        return mag_max + depth2 * (mag_min2 - mag_max)

    return mag_max


# ---------------------------------------------------------------------------
# Extremum finders
# ---------------------------------------------------------------------------

def next_minimum(star: VariableStar, jd_start: float) -> float | None:
    """
    Find the Julian Day of the next primary minimum after jd_start.

    For pulsating variables (DCEP, RR Lyrae, Mira, SR) this returns the
    next phase-0.5 point (minimum is half a period after maximum).

    For EA/EB/EW this returns the next phase-0 point (primary minimum).

    Returns None for irregular or zero-period stars.
    """
    if star.period_days <= 0.0:
        return None

    phi_now = phase_at(star, jd_start)

    if star.epoch_is_minimum:
        # Phase 0 = minimum; next min is at end of current cycle
        days_to_min = (1.0 - phi_now) * star.period_days
        if phi_now < 1e-6:
            days_to_min = star.period_days
    else:
        # Phase 0 = maximum; minimum is at phase 0.5
        phi_min = 0.5
        days_to_min = ((phi_min - phi_now) % 1.0) * star.period_days

    if days_to_min < 0.01:
        days_to_min += star.period_days

    return jd_start + days_to_min


def next_maximum(star: VariableStar, jd_start: float) -> float | None:
    """
    Find the Julian Day of the next maximum after jd_start.

    For pulsating variables: next phase-0 point.
    For eclipsing binaries: next phase-0.5 point (approximate mid-eclipse
    secondary, if secondary max is meaningful) or one cycle past last eclipse.

    Returns None for irregular or zero-period stars.
    """
    if star.period_days <= 0.0:
        return None

    phi_now = phase_at(star, jd_start)

    if star.epoch_is_minimum:
        # Phase 0 = minimum; maximum is at phase 0.5
        phi_max = 0.5
        days_to_max = ((phi_max - phi_now) % 1.0) * star.period_days
    else:
        # Phase 0 = maximum
        days_to_max = (1.0 - phi_now) * star.period_days
        if phi_now < 1e-6:
            days_to_max = star.period_days

    if days_to_max < 0.01:
        days_to_max += star.period_days

    return jd_start + days_to_max


def minima_in_range(
    star: VariableStar,
    jd_start: float,
    jd_end: float,
) -> list[float]:
    """
    Return all primary minima JDs in [jd_start, jd_end].

    Returns an empty list for irregular or zero-period stars.
    """
    if star.period_days <= 0.0:
        return []

    results: list[float] = []
    jd = next_minimum(star, jd_start)
    while jd is not None and jd <= jd_end:
        results.append(jd)
        jd += star.period_days

    return results


def maxima_in_range(
    star: VariableStar,
    jd_start: float,
    jd_end: float,
) -> list[float]:
    """Return all maxima JDs in [jd_start, jd_end]."""
    if star.period_days <= 0.0:
        return []

    results: list[float] = []
    jd = next_maximum(star, jd_start)
    while jd is not None and jd <= jd_end:
        results.append(jd)
        jd += star.period_days

    return results


# ---------------------------------------------------------------------------
# Astrological quality helpers
# ---------------------------------------------------------------------------

def malefic_intensity(star: VariableStar, jd: float) -> float:
    """
    Return a malefic intensity score in [0.0, 1.0] for a malefic variable star.

    For malefic stars (Algol, Antares, Mira, Betelgeuse, etc.):
      - EA  : 1.0 at primary minimum, 0.0 between eclipses
      - Others: 1.0 at minimum brightness, 0.0 at maximum

    For benefic or neutral stars this is always 0.0.
    """
    if star.classical_quality not in ("malefic", "mixed"):
        return 0.0

    mag = magnitude_at(star, jd)
    # Normalise within the star's own range: faintest = most malefic
    mag_range = star.mag_min - star.mag_max
    if mag_range < 0.01:
        return 0.0
    return max(0.0, min(1.0, (mag - star.mag_max) / mag_range))


def benefic_strength(star: VariableStar, jd: float) -> float:
    """
    Return a benefic strength score in [0.0, 1.0].

    For benefic / neutral stars: 1.0 at maximum brightness, 0.0 at minimum.
    For malefic stars: inverted — 1.0 when the malefic is weakest (faintest).
    """
    mag = magnitude_at(star, jd)
    mag_range = star.mag_min - star.mag_max
    if mag_range < 0.01:
        return 1.0
    # Brightness fraction: 0 = minimum (faintest), 1 = maximum (brightest)
    brightness = 1.0 - (mag - star.mag_max) / mag_range
    if star.classical_quality == "malefic":
        # Malefic is "strongest" when faintest; "weakest" when brightest
        return brightness          # high brightness = low threat
    return brightness


def is_in_eclipse(star: VariableStar, jd: float,
                  threshold_mag_above_max: float = 0.05) -> bool:
    """
    Return True if an eclipsing binary is currently in or near primary eclipse.

    Parameters
    ----------
    threshold_mag_above_max : magnitude above max to count as "in eclipse"
                              (default 0.05 mag — about 5% of primary depth)
    """
    if star.var_type not in (VarType.ECLIPSING_ALGOL,
                              VarType.ECLIPSING_BETA,
                              VarType.ECLIPSING_W_UMA):
        return False
    return magnitude_at(star, jd) > star.mag_max + threshold_mag_above_max


# ---------------------------------------------------------------------------
# Catalog access
# ---------------------------------------------------------------------------

def variable_star(name: str) -> VariableStar:
    """
    Look up a variable star by name (case-insensitive).

    Accepts traditional names ('Algol') and designations ('bet Per').

    Raises
    ------
    KeyError if the star is not in the catalog.
    """
    key = name.lower().strip()
    rec = _CATALOG.get(key)
    if rec is None:
        # Prefix match
        matches = [v for k, v in _CATALOG.items() if k.startswith(key)]
        seen: list[VariableStar] = []
        for m in matches:
            if m not in seen:
                seen.append(m)
        if len(seen) == 1:
            return seen[0]
        elif len(seen) > 1:
            return min(seen, key=lambda s: len(s.name))
        raise KeyError(
            f"Variable star {name!r} not in catalog.  "
            f"Use list_variable_stars() to see available names."
        )
    return rec


def list_variable_stars() -> list[str]:
    """Return a sorted list of all variable star names in the catalog."""
    seen: set[str] = set()
    names: list[str] = []
    for v in _CATALOG.values():
        if v.name not in seen:
            seen.add(v.name)
            names.append(v.name)
    return sorted(names)


def variable_stars_by_type(var_type: str) -> list[VariableStar]:
    """Return all catalog entries of a given VarType."""
    seen: set[str] = set()
    results: list[VariableStar] = []
    for v in _CATALOG.values():
        if v.var_type == var_type and v.name not in seen:
            seen.add(v.name)
            results.append(v)
    return results


# ---------------------------------------------------------------------------
# Convenience: Algol special-case (most common astrological use)
# ---------------------------------------------------------------------------

def algol_phase(jd: float) -> float:
    """Return Algol's current phase (0 = deepest eclipse)."""
    return phase_at(_CATALOG["algol"], jd)


def algol_magnitude(jd: float) -> float:
    """Return Algol's estimated V magnitude at jd."""
    return magnitude_at(_CATALOG["algol"], jd)


def algol_next_minimum(jd_start: float) -> float:
    """Return the JD of Algol's next primary minimum."""
    result = next_minimum(_CATALOG["algol"], jd_start)
    assert result is not None
    return result


def algol_is_eclipsed(jd: float, threshold: float = 0.05) -> bool:
    """Return True if Algol is currently within its primary eclipse."""
    return is_in_eclipse(_CATALOG["algol"], jd, threshold)
