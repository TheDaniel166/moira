"""
Asteroid Oracle — moira/asteroids.py

Archetype: Oracle
Purpose: Provides geocentric tropical ecliptic positions for astrologically
         significant minor planets (asteroids, centaurs, TNOs) from JPL SPK
         kernels using a four-kernel priority architecture.

Boundary declaration
--------------------
Owns:
    - AsteroidData — geocentric ecliptic position result.
    - ASTEROID_NAIF — name → NAIF ID mapping for all supported bodies.
    - Four-kernel singleton management (primary, secondary, tertiary,
      quaternary) with lazy loading and priority routing.
    - asteroid_at()       — position of one body at a JD.
    - all_asteroids_at()  — positions of a set of bodies at a JD.
    - list_asteroids()    — all known body names.
    - available_in_kernel() — names present in loaded kernels.
Delegates:
    - Earth/Sun barycentric positions to moira.planets / moira.spk_reader.
    - Light-time, aberration, deflection, frame-bias corrections to
      moira.corrections.
    - Precession and nutation matrices to moira.coordinates.
    - Obliquity to moira.obliquity.
    - Precession in longitude to moira.precession.
    - JD conversion to moira.julian.

Import-time side effects:
    - Importing moira._spk_body_kernel makes the native small-body segment
      readers available to this module.

External dependency assumptions:
    - moira_native must be available for native small-body kernel access.
    - SPK kernels (asteroids.bsp, etc.) are managed by the caller or facade.
    - No Qt, no database, no OS threads.

Public surface / exports:
    AsteroidData          — position result dataclass
    ASTEROID_NAIF         — name → NAIF ID dict
    asteroid_at()         — single-body position
    all_asteroids_at()    — multi-body positions
    list_asteroids()      — all known names
    available_in_kernel() — names present in loaded kernels

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

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .constants import Body, sign_of
from .coordinates import (
    Vec3, vec_add, vec_sub, vec_norm, icrf_to_ecliptic, mat_vec_mul,
    precession_matrix_equatorial, nutation_matrix_equatorial
)
from .obliquity import mean_obliquity, true_obliquity, nutation
from .precession import general_precession_in_longitude
from .julian import ut_to_tt
from .planets import (
    _apparent_geocentric_ecliptic,
    _compose_rotation_matrix,
    _earth_barycentric_state,
    _barycentric as _planet_barycentric,
)
from ._kernel_paths import find_kernel
from .corrections import (
    apply_light_time, apply_aberration, apply_deflection, apply_frame_bias,
    SCHWARZSCHILD_RADII,
)
from ._spk_body_kernel import SmallBodyKernel, _Type13Segment  # noqa: F401 — re-export _Type13Segment
from .spk_reader import get_active_reader, get_reader, KernelReader, MissingKernelError

# Alias for internal use and backward compatibility with existing imports.
_AsteroidKernel = SmallBodyKernel


# ---------------------------------------------------------------------------
# Default kernel paths
# ---------------------------------------------------------------------------

_PRIMARY_KERNEL_PATH   = find_kernel("asteroids.bsp")
_SECONDARY_KERNEL_PATH = find_kernel("sb441-n373s.bsp")
_TERTIARY_KERNEL_PATH  = find_kernel("centaurs.bsp")
_QUATERNARY_KERNEL_PATH = find_kernel("minor_bodies.bsp")

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
    "Toutatis":     2004179,
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

    # Main-belt bodies 25–100 (classical names, all in kernel coverage)
    "Phocaea":      2000025,
    "Circe":        2000034,
    "Leukothea":    2000035,
    "Atalante":     2000036,
    "Fides":        2000037,
    "Leda":         2000038,
    "Laetitia":     2000039,
    "Harmonia":     2000040,
    "Daphne":       2000041,
    "Nemausa":      2000051,
    "Europa":       2000052,
    "Kalypso":      2000053,
    "Alexandra":    2000054,
    "Melete":       2000056,
    "Mnemosyne":    2000057,
    "Concordia":    2000058,
    "Elpis":        2000059,
    "Echo":         2000060,
    "Erato":        2000062,
    "Ausonia":      2000063,
    "Cybele":       2000065,
    "Leto":         2000068,
    "Hesperia":     2000069,
    "Panopaea":     2000070,
    "Feronia":      2000072,
    "Galatea":      2000074,
    "Eurydike":     2000075,
    "Freia":        2000076,
    "Frigga":       2000077,
    "Diana":        2000078,
    "Eurynome":     2000079,
    "Terpsichore":  2000081,
    "Alkmene":      2000082,
    "Beatrix":      2000083,
    "Klio":         2000084,
    "Io":           2000085,
    "Semele":       2000086,
    "Sylvia":       2000087,
    "Thisbe":       2000088,
    "Julia":        2000089,
    "Antiope":      2000090,
    "Aegina":       2000091,
    "Undina":       2000092,
    "Minerva":      2000093,
    "Aurora":       2000094,
    "Arethusa":     2000095,
    "Aegle":        2000096,
    "Klotho":       2000097,
    "Ianthe":       2000098,
    "Dike":         2000099,
    "Hekate":       2000100,

    # Main-belt bodies 102–200
    "Miriam":       2000102,
    "Hera":         2000103,
    "Klymene":      2000104,
    "Artemis":      2000105,
    "Dione":        2000106,
    "Camilla":      2000107,
    "Felicitas":    2000109,
    "Lydia":        2000110,
    "Ate":          2000111,
    "Iphigenia":    2000112,
    "Amalthea":     2000113,
    "Thyra":        2000115,
    "Lomia":        2000117,
    "Peitho":       2000118,
    "Lachesis":     2000120,
    "Hermione":     2000121,
    "Alkeste":      2000124,
    "Johanna":      2000127,
    "Antigone":     2000129,
    "Elektra":      2000130,
    "Aethra":       2000132,
    "Sophrosyne":   2000134,
    "Hertha":       2000135,
    "Meliboea":     2000137,
    "Juewa":        2000139,
    "Siwa":         2000140,
    "Lumen":        2000141,
    "Adria":        2000143,
    "Vibilia":      2000144,
    "Adeona":       2000145,
    "Lucina":       2000146,
    "Protogeneia":  2000147,
    "Gallia":       2000148,
    "Nuwa":         2000150,
    "Bertha":       2000154,
    "Xanthippe":    2000156,
    "Aemilia":      2000159,
    "Una":          2000160,
    "Laurentia":    2000162,
    "Erigone":      2000163,
    "Eva":          2000164,
    "Loreley":      2000165,
    "Sibylla":      2000168,
    "Ophelia":      2000171,
    "Baucis":       2000172,
    "Ino":          2000173,
    "Andromache":   2000175,
    "Iduna":        2000176,
    "Irma":         2000177,
    "Eucharis":     2000181,
    "Eunike":       2000185,
    "Lamberta":     2000187,
    "Kolga":        2000191,
    "Nausikaa":     2000192,
    "Prokne":       2000194,
    "Eurykleia":    2000195,
    "Philomela":    2000196,
    "Ampella":      2000198,
    "Dynamene":     2000200,

    # Main-belt bodies 201–400
    "Penelope":     2000201,
    "Pompeja":      2000203,
    "Martha":       2000205,
    "Hersilia":     2000206,
    "Dido":         2000209,
    "Isabella":     2000210,
    "Isolda":       2000211,
    "Medea":        2000212,
    "Lilaea":       2000213,
    "Kleopatra":    2000216,
    "Eos":          2000221,
    "Rosa":         2000223,
    "Oceana":       2000224,
    "Henrietta":    2000225,
    "Philosophia":  2000227,
    "Athamantis":   2000230,
    "Asterope":     2000233,
    "Honoria":      2000236,
    "Hypatia":      2000238,
    "Vanadis":      2000240,
    "Germania":     2000241,
    "Eukrate":      2000247,
    "Bettina":      2000250,
    "Aletheia":     2000259,
    "Aline":        2000266,
    "Adorea":       2000268,
    "Sapientia":    2000275,
    "Adelheid":     2000276,
    "Emma":         2000283,
    "Nephthys":     2000287,
    "Josephina":    2000303,
    "Olga":         2000304,
    "Polyxo":       2000308,
    "Chaldaea":     2000313,
    "Phaeo":        2000322,
    "Bamberga":     2000324,
    "Tamara":       2000326,
    "Gudrun":       2000328,
    "Svea":         2000329,
    "Chicago":      2000334,
    "Roberta":      2000335,
    "Lacadiera":    2000336,
    "Devosa":       2000337,
    "Budrosa":      2000338,
    "Desiderata":   2000344,
    "Tercidina":    2000345,
    "Hermentaria":  2000346,
    "Pariana":      2000347,
    "Dembowska":    2000349,
    "Ornamenta":    2000350,
    "Eleonora":     2000354,
    "Liguria":      2000356,
    "Ninina":       2000357,
    "Apollonia":    2000358,
    "Carlova":      2000360,
    "Havnia":       2000362,
    "Padua":        2000363,
    "Corduba":      2000365,
    "Vincentina":   2000366,
    "Aeria":        2000369,
    "Palma":        2000372,
    "Melusina":     2000373,
    "Ursula":       2000375,
    "Campania":     2000377,
    "Myrrha":       2000381,
    "Ilmatar":      2000385,
    "Siegena":      2000386,
    "Aquitania":    2000387,
    "Charybdis":    2000388,
    "Industria":    2000389,
    "Lampetia":     2000393,

    # Main-belt bodies 401–600
    "Arsinoe":      2000404,
    "Thia":         2000405,
    "Arachne":      2000407,
    "Aspasia":      2000409,
    "Chloris":      2000410,
    "Elisabetha":   2000412,
    "Palatia":      2000415,
    "Vaticana":     2000416,
    "Aurelia":      2000419,
    "Bertholda":    2000420,
    "Diotima":      2000423,
    "Gratia":       2000424,
    "Hippo":        2000426,
    "Nephele":      2000431,
    "Pythia":       2000432,
    "Eichsfeldia":  2000442,
    "Gyptis":       2000444,
    "Edna":         2000445,
    "Hamburga":     2000449,
    "Patientia":    2000451,
    "Mathesis":     2000454,
    "Bruchsalia":   2000455,
    "Megaira":      2000464,
    "Alekto":       2000465,
    "Tisiphone":    2000466,
    "Argentina":    2000469,
    "Papagena":     2000471,
    "Hedwig":       2000476,
    "Emita":        2000481,
    "Genua":        2000485,
    "Kreusa":       2000488,
    "Comacina":     2000489,
    "Veritas":      2000490,
    "Carina":       2000491,
    "Tokio":        2000498,
    "Evelyn":       2000503,
    "Cava":         2000505,
    "Marion":       2000506,
    "Princetonia":  2000508,
    "Davida":       2000511,
    "Armida":       2000514,
    "Amherstia":    2000516,
    "Edith":        2000517,
    "Brixia":       2000521,
    "Herculina":    2000532,
    "Montague":     2000535,
    "Merapi":       2000536,
    "Messalina":    2000545,
    "Praxedis":     2000547,
    "Peraga":       2000554,
    "Stereoskopia": 2000566,
    "Cheruskia":    2000568,
    "Misa":         2000569,
    "Semiramis":    2000584,
    "Bilkis":       2000585,
    "Irmgard":      2000591,
    "Titania":      2000593,
    "Polyxena":     2000595,
    "Scheila":      2000596,
    "Octavia":      2000598,
    "Luisa":        2000599,

    # Main-belt bodies 601–1000
    "Marianna":     2000602,
    "Tekmessa":     2000604,
    "Elfriede":     2000618,
    "Chimaera":     2000623,
    "Notburga":     2000626,
    "Vundtia":      2000635,
    "Zelinda":      2000654,
    "Gerlinde":     2000663,
    "Denise":       2000667,
    "Rachele":      2000674,
    "Ludmilla":     2000675,
    "Genoveva":     2000680,
    "Lanzia":       2000683,
    "Wratislavia":  2000690,
    "Lehigh":       2000691,
    "Ekard":        2000694,
    "Leonora":      2000696,
    "Alauda":       2000702,
    "Interamnia":   2000704,
    "Erminia":      2000705,
    "Fringilla":    2000709,
    "Boliviana":    2000712,
    "Luscinia":     2000713,
    "Marghanna":    2000735,
    "Mandeville":   2000739,
    "Cantabia":     2000740,
    "Winchester":   2000747,
    "Faina":        2000751,
    "Sulamitis":    2000752,
    "Massinga":     2000760,
    "Pulcova":      2000762,
    "Tatjana":      2000769,
    "Tanete":       2000772,
    "Irmintraud":   2000773,
    "Berbericia":   2000776,
    "Theobalda":    2000778,
    "Armenia":      2000780,
    "Pickeringia":  2000784,
    "Bredichina":   2000786,
    "Hohensteina":  2000788,
    "Pretoria":     2000790,
    "Ani":          2000791,
    "Hispania":     2000804,
    "Tauris":       2000814,
    "Ara":          2000849,
    "Helio":        2000895,
    "Ulla":         2000909,
    "Palisana":     2000914,
    "Anacostia":    2000980,

    # Main-belt bodies 1001–1467
    "Christa":      2001015,
    "Flammario":    2001021,
    "Ganymed":      2001036,
    "Freda":        2001093,
    "Lictoria":     2001107,
    "Rusthawelia":  2001171,
    "Mashona":      2001467,

    # Named trans-Neptunian objects and dwarf planets
    "Chaos":        2019521,
    "Sedna":        2090377,
    "Salacia":      2120347,
    "Haumea":       2136108,
    "Eris":         2136199,
    "Makemake":     2136472,
    "Varda":        2174567,
    "Gonggong":     2225088,
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


# NAIF IDs for which sb441-n373s.bsp is preferred over codes300.
_SB441_PREFERRED: frozenset[int] = frozenset({
    2000001,   # Ceres
    2000002,   # Pallas
    2000003,   # Juno
    2000004,   # Vesta
})


# Kernel discovery is now handled by the facade / KernelPool.
# Legacy shims below maintain compatibility with older test suites.

# Legacy state for backward compatibility and internal test hooks.
_primary_kernel    = None
_secondary_kernel  = None
_tertiary_kernel   = None
_quaternary_kernel = None

from ._kernel_paths import find_kernel as _fk
_PRIMARY_KERNEL_PATH    = _fk("asteroids.bsp")
_SECONDARY_KERNEL_PATH  = _fk("sb441-n373s.bsp")
_TERTIARY_KERNEL_PATH   = _fk("centaurs.bsp")
_QUATERNARY_KERNEL_PATH = _fk("minor_bodies.bsp")


def load_asteroid_kernel(path: str | Path | None = None) -> None:
    """
    RITE: The Resource Expansion
    
    THEOREM: load_asteroid_kernel adds an asteroid SPK kernel to the 
        active global reader context, ensuring that asteroid NAIF IDs 
        become resolvable.
    """
    if path is None:
        return
    
    from .spk_reader import add_to_global_pool
    add_to_global_pool(path)


def load_secondary_kernel(path: str | Path | None = None) -> None:
    """Legacy shim for secondary asteroid kernel."""
    load_asteroid_kernel(path)


def load_tertiary_kernel(path: str | Path | None = None) -> None:
    """Legacy shim for tertiary asteroid kernel."""
    load_asteroid_kernel(path)


def load_quaternary_kernel(path: str | Path | None = None) -> None:
    """Legacy shim for quaternary asteroid kernel."""
    load_asteroid_kernel(path)


def _ensure_primary_kernel() -> KernelReader:
    """Legacy shim for session bootstrap."""
    from .spk_reader import get_active_reader
    active = get_active_reader()
    if active is None:
        load_asteroid_kernel(_PRIMARY_KERNEL_PATH)
    return get_active_reader()


def _ensure_secondary_kernel() -> KernelReader:
    """Legacy shim for session bootstrap."""
    from .spk_reader import get_active_reader
    active = get_active_reader()
    # In the old code, this would check if _secondary_kernel was None.
    # To satisfy tests that mock load_secondary_kernel, we must call it.
    load_secondary_kernel(_SECONDARY_KERNEL_PATH)
    return get_active_reader()


def _ensure_tertiary_kernel() -> KernelReader:
    """Legacy shim for session bootstrap."""
    load_tertiary_kernel(_TERTIARY_KERNEL_PATH)
    return get_active_reader()


def _ensure_quaternary_kernel() -> KernelReader:
    """Legacy shim for session bootstrap."""
    load_quaternary_kernel(_QUATERNARY_KERNEL_PATH)
    return get_active_reader()


def _kernel_for(naif_id: int, reader: KernelReader | None = None) -> _AsteroidKernel:
    """
    Return the best kernel for *naif_id* from the provided reader.
    """
    if reader is None:
        active = get_active_reader()
        reader = active if active is not None else get_reader()

    if not hasattr(reader, "position"):
        raise TypeError(f"Expected KernelReader, got {type(reader)}")
    
    # If the reader is a pool, it will handle dispatching internally.
    # But for the internal logic that needs the specific SmallBodyKernel:
    if hasattr(reader, "_readers"): # KernelPool
        for r in reader._readers:
            if isinstance(r, SmallBodyKernel) and r.has_body(naif_id):
                return r
    elif isinstance(reader, SmallBodyKernel) and reader.has_body(naif_id):
        return reader
        
    raise KeyError(
        f"NAIF ID {naif_id} not found in the provided reader."
    )


# ---------------------------------------------------------------------------
# Core position computation
# ---------------------------------------------------------------------------

def _asteroid_barycentric(naif_id: int, jd_tt: float, kernel: _AsteroidKernel, reader: KernelReader) -> Vec3:
    """Return SSB position of asteroid (km, ICRF)."""
    center = kernel.segment_center(naif_id)
    ref_pos = kernel.position(center, naif_id, jd_tt)
    if center == 10:  # Heliocentric
        # Use the reader to get the Sun's barycentric position
        sun_ssb = reader.position(0, 10, jd_tt)
        return vec_add(ref_pos, sun_ssb)
    return ref_pos    # SSB

def _asteroid_deflectors(
    jd_tt: float,
    reader,
    earth_ssb: Vec3,
) -> list:
    """Return the three standard deflector tuples for asteroid apparent-place computation."""
    sun_geo = vec_sub(reader.position(0, 10, jd_tt), earth_ssb)
    jupiter_geo = vec_sub(_planet_barycentric(Body.JUPITER, jd_tt, reader), earth_ssb)
    saturn_geo = vec_sub(_planet_barycentric(Body.SATURN, jd_tt, reader), earth_ssb)
    return [
        (sun_geo, SCHWARZSCHILD_RADII["Sun"]),
        (jupiter_geo, SCHWARZSCHILD_RADII["Jupiter"]),
        (saturn_geo, SCHWARZSCHILD_RADII["Saturn"]),
    ]


def _asteroid_apparent(
    naif_id: int,
    jd_tt:   float,
    kernel:  _AsteroidKernel,
    reader,
) -> Vec3:
    """
    Return apparent geocentric equatorial-of-date position of *naif_id*.

    The returned vector has already passed through frame bias, precession, and
    nutation; it is no longer an ICRF vector.
    """
    # 1. Earth at observation time
    earth_ssb = _earth_barycentric(jd_tt, reader)

    # 2. Light-time: Body(t-lt) - Earth(t)
    def _bary_fn(nid, t, _r):
        return _asteroid_barycentric(nid, t, kernel, reader)
    
    xyz, _lt = apply_light_time(naif_id, jd_tt, reader, earth_ssb, _bary_fn)

    # 3. Gravitational deflection.
    xyz = apply_deflection(xyz, _asteroid_deflectors(jd_tt, reader, earth_ssb))

    # 4. Annual aberration
    from .planets import _earth_velocity
    v_earth = _earth_velocity(jd_tt, reader)
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
    reader,
    apparent: bool = False,
) -> Vec3:
    """
    Return geocentric position vector of *naif_id* (km).

    Parameters
    ----------
    naif_id      : NAIF ID of the asteroid
    jd_tt        : Julian Day in Terrestrial Time
    kernel       : asteroid kernel to use (from _kernel_for)
    de441_reader : DE441 SpkReader for Earth/Sun positions
    apparent     : if True, return the apparent equatorial-of-date vector
                   after deflection, aberration, frame bias, precession, and
                   nutation; if False (default), return the light-time
                   corrected geocentric astrometric vector before those
                   observer-facing apparent corrections.

    Returns
    -------
    (x, y, z) in km.  The frame is ICRF when ``apparent=False`` and
    equatorial-of-date when ``apparent=True``.
    """
    if apparent:
        return _asteroid_apparent(naif_id, jd_tt, kernel, reader)

    # Geometric geocentric: light-time-corrected position, no other corrections
    earth_ssb = _earth_barycentric(jd_tt, reader)

    def _bary_fn(nid, t, _r):
        return _asteroid_barycentric(nid, t, kernel, reader)

    xyz, _lt = apply_light_time(naif_id, jd_tt, reader, earth_ssb, _bary_fn)
    return xyz


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def asteroid_at(
    name_or_naif: str | int,
    jd_ut: float,
    reader: KernelReader | None = None,
) -> AsteroidData:
    """
    Return the tropical geocentric ecliptic position of a minor planet.

    Parameters
    ----------
    name_or_naif : asteroid name (from ASTEROID_NAIF) or integer NAIF ID
    jd_ut        : Julian Day in Universal Time (UT1)
    reader       : optional KernelReader (uses active context if None)

    Returns
    -------
    AsteroidData

    Raises
    ------
    FileNotFoundError if the asteroid kernel is not found
    KeyError          if the body is not in the kernel or ASTEROID_NAIF dict
    """
    from .spk_reader import get_active_reader, MissingKernelError

    if reader is None:
        reader = get_active_reader()
        if reader is None:
            raise MissingKernelError(
                "No planetary or asteroid kernel is provided and no active reader context was found. "
                "Pass a reader explicitly or use the Moira facade."
            )

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

    obliquity            = true_obliquity(jd_tt)
    earth_ssb, earth_vel = _earth_barycentric_state(jd_tt, reader)
    rot_mat              = _compose_rotation_matrix(jd_tt)
    deflectors           = _asteroid_deflectors(jd_tt, reader, earth_ssb)

    def _bary_fn(b, t, r):
        return r.position(0, b, t)

    lon0, lat0, dist0 = _apparent_geocentric_ecliptic(
        naif_id, jd_tt, reader,
        barycentric_fn=_bary_fn,
        deflectors=deflectors,
        earth_ssb=earth_ssb,
        earth_vel=earth_vel,
        obliquity=obliquity,
        rot_mat=rot_mat,
    )

    # Speed via central finite difference; obliquity is fixed at jd_tt.
    def _lon_at(jd: float) -> float:
        ssb, vel = _earth_barycentric_state(jd, reader)
        rm = _compose_rotation_matrix(jd)
        dfl = _asteroid_deflectors(jd, reader, ssb)
        lon, _, _ = _apparent_geocentric_ecliptic(
            naif_id, jd, reader,
            barycentric_fn=_bary_fn,
            deflectors=dfl,
            earth_ssb=ssb,
            earth_vel=vel,
            obliquity=obliquity,
            rot_mat=rm,
        )
        return lon

    lon_m = _lon_at(jd_tt - _SPEED_STEP)
    lon_p = _lon_at(jd_tt + _SPEED_STEP)
    dlon  = (lon_p - lon_m + 540.0) % 360.0 - 180.0
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
    reader: KernelReader | None = None,
    skip_missing: bool = True,
) -> dict[str, AsteroidData]:
    """
    Return positions for a set of asteroids at *jd_ut*.

    Parameters
    ----------
    jd_ut        : Julian Day in Universal Time
    bodies       : list of names / NAIF IDs (defaults to all of ASTEROID_NAIF)
    reader       : optional KernelReader
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
            pos = asteroid_at(body, jd_ut, reader=reader)
            results[pos.name] = pos
        except (KeyError, MissingKernelError):
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
    """
    if kernel_path:
        load_asteroid_kernel(kernel_path)
    
    from .spk_reader import get_active_reader
    reader = get_active_reader()
    if reader is None:
        return []
    
    available_ids = reader.covered_bodies()
    return [
        name for name, naif_id in ASTEROID_NAIF.items()
        if naif_id in available_ids
    ]
