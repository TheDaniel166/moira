"""
Asteroid Oracle — moira/asteroids.py

Archetype: Oracle
Purpose: Provides geocentric tropical ecliptic positions for astrologically
         significant minor planets (asteroids, centaurs, TNOs) from JPL SPK
         kernels using a four-kernel priority architecture.

Boundary declaration
--------------------
Owns:
    - _Type13Segment — jplephem extension for SPK type 13 (Hermite, unequal
      time steps); registered with jplephem at import time.
    - _AsteroidKernel — thin wrapper around a jplephem SPK file.
    - AsteroidData — geocentric ecliptic position result.
    - ASTEROID_NAIF — name → NAIF ID mapping for all supported bodies.
    - Four-kernel singleton management (primary, secondary, tertiary,
      quaternary) with lazy loading and priority routing.
    - asteroid_at()       — position of one body at a JD.
    - all_asteroids_at()  — positions of a set of bodies at a JD.
    - list_asteroids()    — all known body names.
    - available_in_kernel() — names present in loaded kernels.
    - load_asteroid_kernel() / load_secondary_kernel() / load_tertiary_kernel()
      / load_quaternary_kernel() — explicit kernel load / reload.
Delegates:
    - Earth/Sun barycentric positions to moira.planets / moira.spk_reader.
    - Light-time, aberration, deflection, frame-bias corrections to
      moira.corrections.
    - Precession and nutation matrices to moira.coordinates.
    - Obliquity to moira.obliquity.
    - Precession in longitude to moira.precession.
    - JD conversion to moira.julian.

Import-time side effects:
    - Registers _Type13Segment in jplephem's _segment_classes dict
      (_segment_classes[13] = _Type13Segment).  This is a one-time mutation
      of a jplephem global; it is idempotent and harmless.

External dependency assumptions:
    - jplephem must be installed (ImportError raised otherwise).
    - asteroids.bsp (primary kernel) must be present before any position
      query; FileNotFoundError is raised otherwise.
    - sb441-n373s.bsp, centaurs.bsp, minor_bodies.bsp are optional; absent
      kernels are silently skipped.
    - No Qt, no database, no OS threads.

Public surface / exports:
    AsteroidData          — position result dataclass
    ASTEROID_NAIF         — name → NAIF ID dict
    asteroid_at()         — single-body position
    all_asteroids_at()    — multi-body positions
    list_asteroids()      — all known names
    available_in_kernel() — names present in loaded kernels
    load_asteroid_kernel(), load_secondary_kernel(),
    load_tertiary_kernel(), load_quaternary_kernel()

Four-kernel architecture
------------------------
PRIMARY  — asteroids.bsp  (codes_300ast_20100725.bsp renamed)
    DE421-based, 300 main-belt bodies, SPK type 13, 1800–2200 CE.

SECONDARY — sb441-n373s.bsp  (optional supplement)
    DE441-consistent, 373 bodies, SPK type 2, 1550–2650 CE.
    Preferred over PRIMARY for any body it contains (sub-arcsecond accuracy).

TERTIARY — centaurs.bsp  (generated locally)
    Horizons n-body integrations for six centaurs, < 1 arcsecond, 1800–2200.

QUATERNARY — minor_bodies.bsp  (generated locally)
    Horizons n-body integrations for bodies absent from all other kernels.

Body routing priority: SECONDARY → TERTIARY → QUATERNARY → PRIMARY.

NAIF IDs for small bodies: 2_000_000 + catalogue_number
  e.g. Ceres = 2000001, Chiron = 2002060

Usage
-----
    from moira.asteroids import asteroid_at, all_asteroids_at, list_asteroids

    pos = asteroid_at("Ceres", jd_ut)
    print(pos.longitude, pos.sign, pos.retrograde)
"""

from dataclasses import dataclass, field
from bisect import bisect_left
from pathlib import Path

from .constants import sign_of
from .coordinates import (
    Vec3, vec_add, vec_sub, vec_norm, icrf_to_ecliptic, mat_vec_mul,
    precession_matrix_equatorial, nutation_matrix_equatorial
)
from .obliquity import mean_obliquity, true_obliquity, nutation
from .precession import general_precession_in_longitude
from .julian import ut_to_tt
from .planets import _earth_barycentric, _barycentric as _planet_barycentric
from .corrections import (
    apply_light_time, apply_aberration, apply_deflection, apply_frame_bias,
    SCHWARZSCHILD_RADII,
)

try:
    from jplephem.spk import SPK as _SPK, BaseSegment, _segment_classes, _jd, S_PER_DAY, T0, reify
except ImportError as exc:
    raise ImportError("Moira requires jplephem.  Install: pip install jplephem") from exc


# ---------------------------------------------------------------------------
# SPK Type 13: Hermite Interpolation — Unequal Time Steps
# ---------------------------------------------------------------------------
# jplephem 2.x supports only types 2, 3, 9.  codes_300ast_20100725.bsp uses
# type 13.  We register a compatible segment class here so SPK.open() picks
# it up automatically.

def _hermite_eval_3d(
    t: float,
    ti: list[float],
    pos: list[list[float]],
    vel: list[list[float]],
) -> tuple[float, float, float]:
    """
    Hermite divided-difference interpolation in R³.

    Parameters
    ----------
    t   : scalar query time (seconds from J2000)
    ti  : (n,) node times (seconds from J2000)
    pos : (3, n) positions in km
    vel : (3, n) velocities in km/s  [d(km)/d(second)]

    Returns
    -------
    (3,) interpolated position in km
    """
    n = len(pos[0])
    m = 2 * n

    # Extended nodes: [t0,t0, t1,t1, ..., t_{n-1},t_{n-1}]
    z = [0.0] * m
    for i, value in enumerate(ti):
        z[2 * i] = value
        z[2 * i + 1] = value

    # Divided-differences table, working column-by-column.
    # We only need the first element of each column (Q[0, j]) for the Newton form.
    prev = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        for i in range(n):
            prev[axis][2 * i] = pos[axis][i]
            prev[axis][2 * i + 1] = pos[axis][i]

    coeffs = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        coeffs[axis][0] = prev[axis][0]   # Q[0, 0] = pos at first node

    # j = 1: equal adjacent nodes → use known derivative
    curr = [[0.0] * (m - 1) for _ in range(3)]
    for i in range(m - 1):
        if i % 2 == 0:
            for axis in range(3):
                curr[axis][i] = vel[axis][i // 2]             # derivative at duplicate node
        else:
            denom = z[i + 1] - z[i]
            for axis in range(3):
                curr[axis][i] = (prev[axis][i + 1] - prev[axis][i]) / denom
    for axis in range(3):
        coeffs[axis][1] = curr[axis][0]
    prev = curr

    # j ≥ 2: no equal nodes remain, standard divided differences
    for j in range(2, m):
        curr = [[0.0] * (m - j) for _ in range(3)]
        for i in range(m - j):
            denom = z[i + j] - z[i]
            for axis in range(3):
                curr[axis][i] = (prev[axis][i + 1] - prev[axis][i]) / denom
        for axis in range(3):
            coeffs[axis][j] = curr[axis][0]
        prev = curr

    # Evaluate Newton form via Horner's method
    # p(t) = c₀ + (t−z₀)[c₁ + (t−z₁)[c₂ + ⋯ (t−z_{m-2})·c_{m-1}⋯]]
    result = [coeffs[axis][m - 1] for axis in range(3)]
    for j in range(m - 2, -1, -1):
        delta = t - z[j]
        for axis in range(3):
            result[axis] = coeffs[axis][j] + delta * result[axis]

    return (result[0], result[1], result[2])


class _Type13Segment(BaseSegment):
    """
    RITE: The Hermite Interpreter — a jplephem segment extension that reads
    SPK type 13 (Hermite interpolation with unequal time steps).

    THEOREM: Extends jplephem's BaseSegment to compute positions from SPK
    type 13 segments by performing Hermite divided-difference interpolation
    over a sliding window of state vectors at non-uniform epochs.

    RITE OF PURPOSE:
        jplephem 2.x natively supports only SPK types 2, 3, and 9.  The
        primary asteroid kernel (codes_300ast_20100725.bsp) uses type 13.
        _Type13Segment bridges this gap by implementing the type 13 layout
        and interpolation algorithm, then registering itself in jplephem's
        segment class registry so SPK.open() handles type 13 files
        transparently.  Without it the primary asteroid kernel cannot be
        opened at all.

    LAW OF OPERATION:
        Responsibilities:
            - Parse the type 13 DAF segment layout (state vectors, epochs,
              directory, window size, record count).
            - Select a sliding window of ws points centred on the query epoch.
            - Delegate interpolation to _hermite_eval_3d.
            - Provide compute() returning (x, y, z) in km.
            - Provide compute_and_differentiate() returning position and
              velocity (km, km/day) via central finite difference.
        Non-responsibilities:
            - Does not open or close the DAF file (BaseSegment owns that).
            - Does not convert to ecliptic coordinates.
            - Does not apply light-time or aberration corrections.
        Dependencies:
            - jplephem.spk.BaseSegment, reify, S_PER_DAY, T0.
            - _hermite_eval_3d (module-level function).
        Behavioral invariants:
            - compute() is deterministic for a given tdb.
            - Window selection clamps to valid index range; no out-of-bounds.
        Failure behavior:
            - Raises KeyError (via jplephem) if the query JD is outside the
              segment's coverage.

    Canon: NAIF SPK Required Reading, §2.3.13 (Type 13 segment layout)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.asteroids._Type13Segment",
        "id": "moira.asteroids._Type13Segment",
        "risk": "low",
        "api": {
            "inputs": ["tdb (float)", "tdb2 (float, optional)"],
            "outputs": ["(x, y, z) tuple of floats in km"],
            "raises": ["KeyError if JD outside segment coverage"]
        },
        "state": "stateless",
        "effects": {
            "reads": ["DAF segment data via jplephem mmap"],
            "writes": [],
            "signals_emitted": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": "KeyError from jplephem if JD is outside segment time bounds.",
        "succession": {
            "stance": "terminal",
            "extension_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    Segment layout (1-indexed DAF words from start_i to end_i):
      [start_i,          start_i + 6N − 1] : N state vectors (x,y,z,vx,vy,vz) km / km·s⁻¹
      [start_i + 6N,     start_i + 7N − 1] : N epochs (seconds from J2000)
      [start_i + 7N,     end_i − 2        ] : epoch directory (every 100th epoch)
      [end_i − 1,        end_i            ] : [window_size, N]
    """

    @reify
    def _data(self):
        # Last two words: [window_size, N]
        ws_f, n_f = self.daf.read_array(self.end_i - 1, self.end_i)
        n  = int(n_f)
        ws = int(ws_f)

        # State vectors: shape (N, 6) → (6, N)
        i = self.start_i
        raw_states = self.daf.map_array(i, i + 6 * n - 1)
        states = [[0.0] * n for _ in range(6)]
        for row in range(n):
            base = row * 6
            for axis in range(6):
                states[axis][row] = float(raw_states[base + axis])

        # Epochs: seconds from J2000 → JD
        raw_epochs = self.daf.map_array(i + 6 * n, i + 7 * n - 1)
        epochs_jd = [float(v) / S_PER_DAY + T0 for v in raw_epochs]

        return states, epochs_jd, ws

    def compute(self, tdb, tdb2=0.0):
        """Return (x, y, z) in km at time *tdb* (JD TT)."""
        states, epochs_jd, ws = self._data
        t = float(tdb) + float(tdb2)

        # Select window of ws points centred on the query epoch
        idx = bisect_left(epochs_jd, t)
        half  = ws // 2
        start = max(0, min(idx - half, len(epochs_jd) - ws))

        win_jd = epochs_jd[start:start + ws]
        win_t = [(jd - T0) * S_PER_DAY for jd in win_jd]          # seconds from J2000
        t_sec  = (t - T0) * S_PER_DAY

        pos = [axis[start:start + ws] for axis in states[:3]]   # (3, ws) km
        vel = [axis[start:start + ws] for axis in states[3:]]   # (3, ws) km/s

        return _hermite_eval_3d(t_sec, win_t, pos, vel)

    def compute_and_differentiate(self, tdb, tdb2=0.0):
        """Return ((x,y,z), (vx,vy,vz)) — velocity via finite difference (km, km/day)."""
        dt = 1.0    # 1 JD step
        p0 = self.compute(tdb - dt * 0.5, tdb2)
        p1 = self.compute(tdb + dt * 0.5, tdb2)
        pos = self.compute(tdb, tdb2)
        vel = tuple((b - a) / dt for a, b in zip(p0, p1))    # km/day
        return pos, vel


# Register with jplephem so SPK.open() uses it automatically
_segment_classes[13] = _Type13Segment


# ---------------------------------------------------------------------------
# Default kernel paths
# ---------------------------------------------------------------------------

_REPO_KERNELS_DIR = Path(__file__).parent.parent / "kernels"
_PACKAGE_KERNELS_DIR = Path(__file__).parent / "kernels"


def _first_existing_path(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


_PRIMARY_KERNEL_PATH = _REPO_KERNELS_DIR / "asteroids.bsp"
_SECONDARY_KERNEL_PATH = _REPO_KERNELS_DIR / "sb441-n373s.bsp"
_TERTIARY_KERNEL_PATH = _first_existing_path(
    _PACKAGE_KERNELS_DIR / "centaurs.bsp",
    _REPO_KERNELS_DIR / "centaurs.bsp",
)
_QUATERNARY_KERNEL_PATH = _first_existing_path(
    _PACKAGE_KERNELS_DIR / "minor_bodies.bsp",
    _REPO_KERNELS_DIR / "minor_bodies.bsp",
)

# Speed step for numerical differentiation of longitude (days)
_SPEED_STEP = 0.5


# ---------------------------------------------------------------------------
# Astrologically significant asteroids with NAIF IDs
# ---------------------------------------------------------------------------
# NAIF convention: small body N → NAIF ID = 2_000_000 + N

ASTEROID_NAIF: dict[str, int] = {
    # Four main-belt asteroids (classical)
    "Ceres":        2000001,
    "Pallas":       2000002,
    "Juno":         2000003,
    "Vesta":        2000004,
    # Other major main-belt bodies
    "Astraea":      2000005,
    "Hebe":         2000006,
    "Iris":         2000007,
    "Flora":        2000008,
    "Metis":        2000009,
    "Hygiea":       2000010,
    "Parthenope":   2000011,
    "Victoria":     2000012,
    "Egeria":       2000013,
    "Irene":        2000014,
    "Eunomia":      2000015,
    "Psyche":       2000016,
    "Thetis":       2000017,
    "Melpomene":    2000018,
    "Fortuna":      2000019,
    "Massalia":     2000020,
    "Lutetia":      2000021,
    "Kalliope":     2000022,
    "Thalia":       2000023,
    "Themis":       2000024,
    "Proserpina":   2000026,
    "Euterpe":      2000027,
    "Bellona":      2000028,
    "Amphitrite":   2000029,
    "Urania":       2000030,
    "Euphrosyne":   2000031,
    "Pomona":       2000032,
    "Isis":         2000042,
    "Ariadne":      2000043,
    "Nysa":         2000044,
    "Eugenia":      2000045,
    "Hestia":       2000046,
    "Aglaja":       2000047,
    "Doris":        2000048,
    "Pales":        2000049,
    "Virginia":     2000050,
    "Sappho":       2000080,
    "Niobe":        2000071,
    "Pandora":      2000055,
    "Kassandra":    2000114,
    "Nemesis":      2000128,
    "Eros":         2000433,
    "Lilith":       2001181,
    "Amor":         2001221,
    "Icarus":       2001566,
    "Apollo":       2001862,
    # Centaurs (astrologically significant)
    "Chiron":       2002060,
    "Pholus":       2005145,
    "Nessus":       2007066,
    "Asbolus":      2008405,
    "Chariklo":     2010199,
    "Hylonome":     2010370,
    # Trans-Neptunian / dwarf planets
    "Ixion":        2028978,
    "Quaoar":       2050000,
    "Varuna":       2020000,
    "Orcus":        2090482,
    # Named bodies with astrological use
    "Karma":        2003811,
    "Persephone":   2000399,
}

# Reverse lookup: NAIF ID → name
_NAIF_TO_NAME: dict[int, str] = {v: k for k, v in ASTEROID_NAIF.items()}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AsteroidData:
    """
    RITE: The Minor Body's Witness — the geocentric tropical ecliptic position
    of a minor planet at a specific moment in time.

    THEOREM: Holds the computed tropical ecliptic longitude, latitude, geocentric
    distance, daily speed, and retrograde flag for a named minor planet at a
    given Julian Day.

    RITE OF PURPOSE:
        AsteroidData is the public result vessel of the Asteroid Oracle.  It
        carries the apparent place of a minor planet in the tropical ecliptic
        frame of date, together with the motion data (speed, retrograde) needed
        for astrological interpretation.  Without it callers would receive raw
        floats with no semantic context, no sign assignment, and no retrograde
        flag.  It serves the Asteroid Oracle pillar as its sole output type.

    LAW OF OPERATION:
        Responsibilities:
            - Store name, NAIF ID, tropical longitude, ecliptic latitude,
              geocentric distance, daily speed, and retrograde flag.
            - Derive sign name, sign symbol, and sign-relative degree via
              __post_init__ (delegating to sign_of).
            - Expose longitude_dms property for degree/minute/second breakdown.
        Non-responsibilities:
            - Does not compute positions (that is asteroid_at's role).
            - Does not perform kernel lookups.
            - Does not carry equatorial coordinates.
        Dependencies:
            - moira.constants.sign_of for sign derivation.
        Structural invariants:
            - longitude is always in [0, 360).
            - sign, sign_symbol, sign_degree are set by __post_init__ and
              remain consistent with longitude.
        Mutation authority: Fields are mutable post-construction (not frozen).

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.asteroids.AsteroidData",
        "id": "moira.asteroids.AsteroidData",
        "risk": "high",
        "api": {
            "inputs": ["name", "naif_id", "longitude", "latitude", "distance",
                       "speed", "retrograde"],
            "outputs": ["AsteroidData instance", "sign (str)", "sign_symbol (str)",
                        "sign_degree (float)", "longitude_dms (tuple)"],
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
    """

    name:        str
    naif_id:     int
    longitude:   float        # tropical ecliptic longitude, degrees [0, 360)
    latitude:    float        # ecliptic latitude, degrees
    distance:    float        # distance from Earth, km
    speed:       float        # daily motion in longitude, degrees/day
    retrograde:  bool         # True when speed < 0
    sign:        str  = field(init=False)
    sign_symbol: str  = field(init=False)
    sign_degree: float= field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    @property
    def longitude_dms(self) -> tuple[int, int, float]:
        d   = self.sign_degree
        deg = int(d)
        m   = int((d - deg) * 60)
        s   = ((d - deg) * 60 - m) * 60
        return deg, m, s

    def __repr__(self) -> str:
        r = "℞" if self.retrograde else ""
        deg, m, s = self.longitude_dms
        return (f"{self.name}: {deg}°{m:02d}′{s:04.1f}″ {self.sign} {self.sign_symbol}"
                f"  ({self.longitude:.4f}°) {r}  Δ={self.speed:+.4f}°/d")


# ---------------------------------------------------------------------------
# Asteroid kernel singleton
# ---------------------------------------------------------------------------

class _AsteroidKernel:
    """
    RITE: The Kernel Warden — a thin wrapper around a jplephem SPK file for
    asteroid position queries.

    THEOREM: Opens a single JPL SPK kernel file, indexes its available NAIF
    body IDs and reference centers, and provides a position() method that
    returns the ICRF position of a body at a given JD.

    RITE OF PURPOSE:
        _AsteroidKernel isolates all jplephem SPK file interaction behind a
        minimal interface.  The Asteroid Oracle governs four kernel singletons
        (primary, secondary, tertiary, quaternary); each is an _AsteroidKernel
        instance.  Without this wrapper the routing logic in _kernel_for()
        would be entangled with jplephem's segment API, making kernel swapping
        and availability checks fragile.

    LAW OF OPERATION:
        Responsibilities:
            - Open the SPK file via jplephem.spk.SPK.
            - Index available NAIF IDs and their reference centers at
              construction time.
            - Expose has_body(), segment_center(), position(), list_naif_ids(),
              and close().
        Non-responsibilities:
            - Does not convert to ecliptic coordinates.
            - Does not apply light-time, aberration, or frame corrections.
            - Does not manage the four-kernel priority routing (that is
              _kernel_for's role).
        Dependencies:
            - jplephem.spk.SPK (must be installed).
            - _Type13Segment must be registered before SPK.open() is called
              (guaranteed by module-level registration at import time).
        Failure behavior:
            - __init__ raises FileNotFoundError if the kernel file is absent.
            - position() raises KeyError if no segment covers the body/JD.
        Mutation authority: _available and _center are set at construction
            and never mutated thereafter.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.asteroids._AsteroidKernel",
        "id": "moira.asteroids._AsteroidKernel",
        "risk": "low",
        "api": {
            "inputs": ["path (Path)"],
            "outputs": ["_AsteroidKernel instance"],
            "raises": ["FileNotFoundError if kernel absent",
                       "KeyError from position() if body/JD not covered"]
        },
        "state": "stateless",
        "effects": {
            "reads": ["SPK kernel file (mmap via jplephem)"],
            "writes": [],
            "signals_emitted": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": "FileNotFoundError on construction; KeyError from position().",
        "succession": {
            "stance": "terminal",
            "extension_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Asteroid kernel not found at {path}")
        self._path   = path
        self._kernel = _SPK.open(str(path))

        # Index available bodies and their reference center
        self._available: set[int]   = set()
        self._center:    dict[int, int] = {}
        for seg in self._kernel.segments:
            self._available.add(seg.target)
            if seg.target not in self._center:
                self._center[seg.target] = seg.center

    def has_body(self, naif_id: int) -> bool:
        return naif_id in self._available

    def segment_center(self, naif_id: int) -> int:
        """Return the reference center NAIF ID for this body (typically 10 = Sun)."""
        return self._center.get(naif_id, 0)

    def position(self, naif_id: int, jd_tt: float) -> Vec3:
        """
        Return position of *naif_id* relative to its segment center (km, ICRF).
        For codes_300ast_20100725.bsp the center is 10 (Sun), i.e. heliocentric.
        """
        for seg in self._kernel.segments:
            if seg.target == naif_id and seg.start_jd <= jd_tt <= seg.end_jd:
                pos = seg.compute(jd_tt)
                return (float(pos[0]), float(pos[1]), float(pos[2]))
        raise KeyError(
            f"No segment covers NAIF {naif_id} at JD {jd_tt:.2f}. "
            "The date may be outside the kernel's coverage."
        )

    def list_naif_ids(self) -> list[int]:
        return sorted(self._available)

    def close(self) -> None:
        try:
            self._kernel.close()
        except Exception:
            pass


_primary_kernel:    _AsteroidKernel | None = None   # codes300 (accurate, main-belt)
_secondary_kernel:  _AsteroidKernel | None = None   # sb441 (TNO supplement, optional)
_tertiary_kernel:   _AsteroidKernel | None = None   # centaurs.bsp (Horizons, optional)
_quaternary_kernel: _AsteroidKernel | None = None   # minor_bodies.bsp (Horizons, optional)

# NAIF IDs for which sb441-n373s.bsp is preferred over codes300.
# Benchmarked against JPL Horizons OBSERVER (quantity 31): sb441 is
# sub-arcsecond for all main-belt bodies it contains; codes300 has errors
# of arcminutes to degrees for the same bodies.
# This set is populated at first use from the loaded secondary kernel.
_SB441_PREFERRED: frozenset[int] = frozenset({
    2000001,   # Ceres
    2000002,   # Pallas
    2000003,   # Juno
    2000004,   # Vesta
})


def load_asteroid_kernel(path: str | Path | None = None) -> None:
    """
    Load (or reload) the PRIMARY asteroid kernel (codes_300ast / asteroids.bsp).

    If *path* is None the default location is used:
        <project_root>/asteroids.bsp   (rename codes_300ast_20100725.bsp)

    Raises FileNotFoundError if the file does not exist.
    """
    global _primary_kernel
    p = Path(path) if path else _PRIMARY_KERNEL_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"Primary asteroid kernel not found at {p}\n"
            "Download codes_300ast_20100725.bsp from:\n"
            "  https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/asteroids/\n"
            "rename it to asteroids.bsp, and place it in the project root."
        )
    if _primary_kernel is not None:
        _primary_kernel.close()
    _primary_kernel = _AsteroidKernel(p)


def load_secondary_kernel(path: str | Path | None = None) -> None:
    """
    Load (or reload) the SECONDARY asteroid kernel (sb441-n373s.bsp).

    Used only for TNOs/bodies absent from the primary kernel:
    Ixion, Quaoar, Varuna, Orcus, and a few others.

    Accuracy for bodies also present in codes300 is several degrees — the
    secondary is never consulted for those bodies.

    If *path* is None the default location is used:
        <project_root>/sb441-n373s.bsp

    Raises FileNotFoundError if the file does not exist.
    """
    global _secondary_kernel
    p = Path(path) if path else _SECONDARY_KERNEL_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"Secondary asteroid kernel not found at {p}\n"
            "Download sb441-n373s.bsp from:\n"
            "  https://ssd.jpl.nasa.gov/ftp/eph/small_bodies/asteroids_de441/sb441-n373s.bsp\n"
            "and place it in the project root alongside de441.bsp."
        )
    if _secondary_kernel is not None:
        _secondary_kernel.close()
    _secondary_kernel = _AsteroidKernel(p)


def _ensure_primary_kernel() -> _AsteroidKernel:
    if _primary_kernel is None:
        load_asteroid_kernel()
    assert _primary_kernel is not None
    return _primary_kernel


def load_tertiary_kernel(path: str | Path | None = None) -> None:
    """
    Load (or reload) the TERTIARY asteroid kernel (centaurs.bsp).

    Generated by scripts/build_centaur_kernel.py from JPL Horizons full
    n-body integrations.  Provides Chiron, Pholus, Nessus, Asbolus,
    Chariklo, Hylonome — accurate to < 1 arcsecond over 1800–2200.

    If *path* is None the default location is used:
        <project_root>/centaurs.bsp

    Raises FileNotFoundError if the file does not exist.
    Run  py scripts/build_centaur_kernel.py  to generate it.
    """
    global _tertiary_kernel
    p = Path(path) if path else _TERTIARY_KERNEL_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"Centaur kernel not found at {p}\n"
            "Generate it with:\n"
            "    py -3.14 scripts/build_centaur_kernel.py"
        )
    if _tertiary_kernel is not None:
        _tertiary_kernel.close()
    _tertiary_kernel = _AsteroidKernel(p)


def _ensure_secondary_kernel() -> _AsteroidKernel | None:
    """Try to load the secondary kernel; return None (not an error) if absent."""
    if _secondary_kernel is None:
        if _SECONDARY_KERNEL_PATH.exists():
            try:
                load_secondary_kernel()
            except Exception:
                pass
    return _secondary_kernel


def _ensure_tertiary_kernel() -> _AsteroidKernel | None:
    """Try to load the centaur kernel; return None (not an error) if absent."""
    if _tertiary_kernel is None:
        if _TERTIARY_KERNEL_PATH.exists():
            try:
                load_tertiary_kernel()
            except Exception:
                pass
    return _tertiary_kernel


def load_quaternary_kernel(path: str | Path | None = None) -> None:
    """
    Load (or reload) the QUATERNARY asteroid kernel (minor_bodies.bsp).

    Generated by scripts/build_minor_bodies_kernel.py from JPL Horizons full
    n-body integrations.  Provides Pandora, Amor, Icarus, Apollo, Karma,
    Persephone — bodies absent from all other kernels.

    If *path* is None the default location is used:
        <project_root>/kernels/minor_bodies.bsp

    Raises FileNotFoundError if the file does not exist.
    Run  py -3.14 scripts/build_minor_bodies_kernel.py  to generate it.
    """
    global _quaternary_kernel
    p = Path(path) if path else _QUATERNARY_KERNEL_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"Minor bodies kernel not found at {p}\n"
            "Generate it with:\n"
            "    py -3.14 scripts/build_minor_bodies_kernel.py"
        )
    if _quaternary_kernel is not None:
        _quaternary_kernel.close()
    _quaternary_kernel = _AsteroidKernel(p)


def _ensure_quaternary_kernel() -> _AsteroidKernel | None:
    """Try to load the minor bodies kernel; return None (not an error) if absent."""
    if _quaternary_kernel is None:
        if _QUATERNARY_KERNEL_PATH.exists():
            try:
                load_quaternary_kernel()
            except Exception:
                pass
    return _quaternary_kernel


def _kernel_for(naif_id: int) -> _AsteroidKernel:
    """
    Return the best kernel for *naif_id*.

    Priority order:
      1. Secondary (sb441-n373s.bsp) for any body it contains — benchmarked
         sub-arcsecond vs. codes300's arcminute-to-degree errors for the same
         bodies.  sb441 is preferred whenever it has the body.
      2. Tertiary  (centaurs.bsp)    — Horizons centaurs (< 1 arcsec)
      3. Quaternary (minor_bodies.bsp) — Horizons bodies absent from all above
      4. Primary   (codes300/asteroids.bsp) — bodies absent from all above
    """
    # sb441 is the precision source for all bodies it contains
    secondary = _ensure_secondary_kernel()
    if secondary is not None and secondary.has_body(naif_id):
        return secondary

    # Centaur kernel (Horizons n-body, < 1 arcsec)
    tertiary = _ensure_tertiary_kernel()
    if tertiary is not None and tertiary.has_body(naif_id):
        return tertiary

    # Minor bodies kernel (Horizons n-body — Pandora, Amor, Icarus, Apollo, Karma, Persephone)
    quaternary = _ensure_quaternary_kernel()
    if quaternary is not None and quaternary.has_body(naif_id):
        return quaternary

    # Primary for bodies absent from all above
    primary = _ensure_primary_kernel()
    if primary.has_body(naif_id):
        return primary

    raise KeyError(
        f"NAIF ID {naif_id} not found in any loaded asteroid kernel. "
        "Use available_in_kernel() to see what bodies are available.\n"
        "For minor bodies (Pandora, Amor, Icarus, Apollo, Karma, Persephone), run:\n"
        "    py -3.14 scripts/build_minor_bodies_kernel.py"
    )


# ---------------------------------------------------------------------------
# Core position computation
# ---------------------------------------------------------------------------

def _asteroid_barycentric(naif_id: int, jd_tt: float, kernel: _AsteroidKernel, de441_reader) -> Vec3:
    """Return SSB position of asteroid (km, ICRF)."""
    center = kernel.segment_center(naif_id)
    ref_pos = kernel.position(naif_id, jd_tt)
    if center == 10:  # Heliocentric
        sun_ssb = de441_reader.position(0, 10, jd_tt)
        return vec_add(ref_pos, sun_ssb)
    return ref_pos    # SSB

def _asteroid_apparent(
    naif_id: int,
    jd_tt:   float,
    kernel:  _AsteroidKernel,
    de441_reader,
) -> Vec3:
    """
    Return apparent geocentric ICRF position of *naif_id* with 
    all relativistic and matrix corrections.
    """
    # 1. Earth at observation time
    earth_ssb = _earth_barycentric(jd_tt, de441_reader)

    # 2. Light-time: Body(t-lt) - Earth(t)
    def _bary_fn(nid, t, reader):
        return _asteroid_barycentric(nid, t, kernel, de441_reader)
    
    xyz, _lt = apply_light_time(naif_id, jd_tt, de441_reader, earth_ssb, _bary_fn)

    # 3. Gravitational deflection (near Sun)
    sun_geocentric = vec_sub(de441_reader.position(0, 10, jd_tt), earth_ssb)
    xyz = apply_deflection(xyz, [(sun_geocentric, SCHWARZSCHILD_RADII["Sun"])])

    # 4. Annual aberration
    from .planets import _earth_velocity
    v_earth = _earth_velocity(jd_tt, de441_reader)
    xyz = apply_aberration(xyz, v_earth)

    # 5. Frame bias
    xyz = apply_frame_bias(xyz)

    # 6. Precession
    P = precession_matrix_equatorial(jd_tt)
    xyz = mat_vec_mul(P, xyz)

    # 7. Nutation
    N = nutation_matrix_equatorial(jd_tt)
    xyz = mat_vec_mul(N, xyz)

    return xyz


# ---------------------------------------------------------------------------
# Semi-private helpers (used by tests and integration tools)
# ---------------------------------------------------------------------------

def _asteroid_geocentric(
    naif_id: int,
    jd_tt: float,
    kernel: _AsteroidKernel,
    de441_reader,
    apparent: bool = False,
) -> Vec3:
    """
    Return geocentric ICRF position of *naif_id* (km).

    Parameters
    ----------
    naif_id      : NAIF ID of the asteroid
    jd_tt        : Julian Day in Terrestrial Time
    kernel       : asteroid kernel to use (from _kernel_for)
    de441_reader : DE441 SpkReader for Earth/Sun positions
    apparent     : if True, apply full apparent-sky corrections
                   (deflection, aberration, frame bias, P+N matrices);
                   if False (default), return light-time-corrected
                   geometric geocentric vector only

    Returns
    -------
    (x, y, z) in km, ICRF
    """
    if apparent:
        return _asteroid_apparent(naif_id, jd_tt, kernel, de441_reader)

    # Geometric geocentric: light-time-corrected position, no other corrections
    earth_ssb = _earth_barycentric(jd_tt, de441_reader)

    def _bary_fn(nid, t, reader):
        return _asteroid_barycentric(nid, t, kernel, de441_reader)

    xyz, _lt = apply_light_time(naif_id, jd_tt, de441_reader, earth_ssb, _bary_fn)
    return xyz


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def asteroid_at(
    name_or_naif: str | int,
    jd_ut: float,
    kernel_path: str | Path | None = None,
    de441_reader=None,
) -> AsteroidData:
    """
    Return the tropical geocentric ecliptic position of a minor planet.

    Parameters
    ----------
    name_or_naif : asteroid name (from ASTEROID_NAIF) or integer NAIF ID
    jd_ut        : Julian Day in Universal Time (UT1)
    kernel_path  : override path to the asteroid SPK kernel
    de441_reader : optional SpkReader for DE441 (uses singleton if None)

    Returns
    -------
    AsteroidData

    Raises
    ------
    FileNotFoundError if the asteroid kernel is not found
    KeyError          if the body is not in the kernel or ASTEROID_NAIF dict
    """
    from .spk_reader import get_reader

    if kernel_path:
        load_asteroid_kernel(kernel_path)

    if de441_reader is None:
        de441_reader = get_reader()

    jd_tt = ut_to_tt(jd_ut)

    # Resolve name → NAIF ID
    if isinstance(name_or_naif, str):
        key = name_or_naif.strip()
        if key not in ASTEROID_NAIF:
            lower = key.lower()
            match = next((v for k, v in ASTEROID_NAIF.items() if k.lower() == lower), None)
            if match is None:
                raise KeyError(
                    f"Asteroid {name_or_naif!r} not in ASTEROID_NAIF. "
                    "Pass an integer NAIF ID directly, or use list_asteroids()."
                )
            naif_id = match
        else:
            naif_id = ASTEROID_NAIF[key]
        name = key
    else:
        naif_id = int(name_or_naif)
        name    = _NAIF_TO_NAME.get(naif_id, f"NAIF-{naif_id}")

    kernel = _kernel_for(naif_id)

    # Compute obliquity once
    obliquity = true_obliquity(jd_tt)

    def _lon_lat_dist(jd: float):
        xyz = _asteroid_apparent(naif_id, jd, kernel, de441_reader)
        return icrf_to_ecliptic(xyz, obliquity)

    lon0, lat0, dist0 = _lon_lat_dist(jd_tt)

    # Speed via central finite difference
    lon_m, _, _ = _lon_lat_dist(jd_tt - _SPEED_STEP)
    lon_p, _, _ = _lon_lat_dist(jd_tt + _SPEED_STEP)
    dlon = (lon_p - lon_m + 540.0) % 360.0 - 180.0   # wrap-safe
    speed = dlon / (2.0 * _SPEED_STEP)

    return AsteroidData(
        name=name,
        naif_id=naif_id,
        longitude=lon0,
        latitude=lat0,
        distance=dist0,
        speed=speed,
        retrograde=(speed < 0.0),
    )


def all_asteroids_at(
    jd_ut: float,
    bodies: list[str | int] | None = None,
    kernel_path: str | Path | None = None,
    de441_reader=None,
    skip_missing: bool = True,
) -> dict[str, AsteroidData]:
    """
    Return positions for a set of asteroids at *jd_ut*.

    Parameters
    ----------
    jd_ut        : Julian Day in Universal Time
    bodies       : list of names / NAIF IDs (defaults to all of ASTEROID_NAIF)
    kernel_path  : override path to the asteroid SPK kernel
    de441_reader : optional SpkReader for DE441
    skip_missing : silently skip bodies absent from the kernel when True

    Returns
    -------
    dict mapping name → AsteroidData
    """
    if bodies is None:
        bodies = list(ASTEROID_NAIF.keys())

    results: dict[str, AsteroidData] = {}
    for body in bodies:
        try:
            pos = asteroid_at(body, jd_ut, kernel_path=kernel_path,
                              de441_reader=de441_reader)
            results[pos.name] = pos
            kernel_path = None   # kernel already loaded after first call
        except (KeyError, FileNotFoundError):
            if not skip_missing:
                raise
    return results


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------

def list_asteroids() -> list[str]:
    """Return the list of asteroid names known to Moira (ASTEROID_NAIF keys)."""
    return list(ASTEROID_NAIF.keys())


def available_in_kernel(kernel_path: str | Path | None = None) -> list[str]:
    """
    Return names of ASTEROID_NAIF entries present in any loaded kernel.

    Loads the primary (and optionally the secondary/tertiary/quaternary)
    kernel as needed.
    """
    if kernel_path:
        load_asteroid_kernel(kernel_path)
    primary    = _ensure_primary_kernel()
    secondary  = _ensure_secondary_kernel()
    tertiary   = _ensure_tertiary_kernel()
    quaternary = _ensure_quaternary_kernel()
    available_ids: set[int] = set(primary._available)
    if secondary is not None:
        available_ids |= secondary._available
    if tertiary is not None:
        available_ids |= tertiary._available
    if quaternary is not None:
        available_ids |= quaternary._available
    return [
        name for name, naif_id in ASTEROID_NAIF.items()
        if naif_id in available_ids
    ]
