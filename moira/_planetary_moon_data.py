"""Source-pinned identities and figure constants for the planetary moons."""

from dataclasses import dataclass
from typing import Literal

from .spk_reader import _summary_label_text

Planet = Literal["Jupiter", "Saturn"]

NAIF_SATELLITES = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/"
PCK_URL = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc"
PCK_SHA256 = "3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1"
RADII_URL = "https://ssd.jpl.nasa.gov/sats/phys_par/"
SUN_RADIUS_KM = 695700.0


@dataclass(frozen=True, slots=True)
class MoonIdentity:
    """A satellite's NAIF identity and JPL mean radius in kilometers."""

    name: str
    naif_id: int
    radius_km: float


@dataclass(frozen=True, slots=True)
class MoonSystem:
    """Admitted source, target roster and PCK pole and spheroid coefficients."""

    name: Planet
    center: int
    barycenter: int
    source: str
    source_sha256: str
    radii_km: tuple[float, float]
    pole_ra_deg: tuple[float, float]
    pole_dec_deg: tuple[float, float]
    pole_periodic: tuple[tuple[float, float, float, float], ...]
    moons: tuple[MoonIdentity, ...]


# PCK00011's Jupiter pole uses five nonzero periodic terms. Each row is the
# argument at J2000, its rate per TDB century, and the RA and DEC amplitudes.
SYSTEMS = (
    MoonSystem(
        "Jupiter", 599, 5, "jup365.bsp",
        "dbf016c01ba4d022154838000cf3f06962cf958ddc503a366f7fe8f81495c5cb",
        (71492.0, 66854.0), (268.056595, -0.006499), (64.495303, 0.002413),
        (
            (99.360714, 4850.4046, 0.000117, 0.000050),
            (175.895369, 1191.9605, 0.000938, 0.000404),
            (300.323162, 262.5475, 0.001432, 0.000617),
            (114.012305, 6070.2476, 0.000030, -0.000013),
            (49.511251, 64.3000, 0.002150, 0.000926),
        ),
        (
            MoonIdentity("Io", 501, 1821.49),
            MoonIdentity("Europa", 502, 1560.80),
            MoonIdentity("Ganymede", 503, 2631.20),
            MoonIdentity("Callisto", 504, 2410.30),
        ),
    ),
    MoonSystem(
        "Saturn", 699, 6, "sat441.bsp",
        "d7e444a9ba7a52b8f448ff0747030789524d2f0c1212e4e2bd7f5fc3c96444d5",
        (60268.0, 54364.0), (40.589, -0.036), (83.537, -0.004), (),
        (
            MoonIdentity("Mimas", 601, 198.20),
            MoonIdentity("Enceladus", 602, 252.10),
            MoonIdentity("Tethys", 603, 531.10),
            MoonIdentity("Dione", 604, 561.40),
            MoonIdentity("Rhea", 605, 763.50),
            MoonIdentity("Titan", 606, 2574.76),
            MoonIdentity("Hyperion", 607, 135.00),
            MoonIdentity("Iapetus", 608, 734.30),
        ),
    ),
)


def segment_pairs(system: MoonSystem) -> frozenset[tuple[int, int]]:
    """Return the system-local segments admitted for this roster."""
    return frozenset((system.barycenter, target) for target in (
        system.center, *(moon.naif_id for moon in system.moons),
    ))


def segment_receipt(catalog: dict) -> list[dict]:
    """Describe the native reader's SPK segments without changing their order."""
    return [
        {
            "label": _summary_label_text(item["name"]),
            "start_tdb_s": item["descriptor"][0],
            "end_tdb_s": item["descriptor"][1],
            "target": item["descriptor"][2],
            "center": item["descriptor"][3],
            "frame": item["descriptor"][4],
            "type": item["descriptor"][5],
        }
        for item in catalog["summaries"]
    ]
