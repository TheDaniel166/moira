"""Chart-time states and parent–moon events for Jupiter and Saturn.

This opt-in module uses DE441 for solar-system states, isolated JPL satellite
SPKs for local states, and nominal reference figures for disk geometry. All
results refer to the explicitly declared observers and light-time policies.
"""

from contextlib import ExitStack
from dataclasses import dataclass
import json
from math import cos, degrees, isfinite
from pathlib import Path
from typing import Literal

from ._planetary_moon_data import (
    NAIF_SATELLITES,
    PCK_SHA256,
    PCK_URL,
    RADII_URL,
    SUN_RADIUS_KM,
    SYSTEMS,
    MoonIdentity,
    MoonSystem,
    Planet,
    segment_pairs,
    segment_receipt,
)
from ._planetary_moon_geometry import (
    DiskOverlap,
    angle_between,
    disk_overlap,
    planet_pole,
    sky_offsets_arcsec,
)
from .constants import C_KM_PER_DAY
from .coordinates import Vec3, vec_add, vec_norm, vec_scale, vec_sub
from .corrections import _iterate_light_time
from .julian import tt_to_tdb
from .spk_reader import KernelPool, SpkReader, _intersect_closed_intervals

__all__ = [
    "EarthMoonView",
    "MoonPhase",
    "PlanetaryMoon",
    "PlanetaryMoonSnapshot",
    "PlanetaryMoonSource",
    "PlanetaryMoons",
]


@dataclass(frozen=True, slots=True)
class PlanetaryMoonSource:
    """Identity of the original JPL source and the extracted SPK used."""

    planet: Planet
    source_url: str
    source_sha256: str
    extract_sha256: str


@dataclass(frozen=True, slots=True)
class EarthMoonView:
    """Nominal Earth-center view with independently retarded limbs.

    Positive range offset places the moon farther away. An emission offset is
    in TDB days relative to the snapshot's reception epoch. The active event
    requires positive overlap, and contact is reported separately.
    """

    east_arcsec: float
    north_arcsec: float
    range_offset_km: float
    moon_emission_offset_days: float
    planet_emission_offset_days: float
    overlap: DiskOverlap
    event: Literal["transit", "occultation"] | None

    @property
    def side(self) -> Literal["near", "far", "same_range"]:
        """Return the moon's range ordering in the Earth view."""
        if self.range_offset_km < 0:
            return "near"
        return "far" if self.range_offset_km > 0 else "same_range"


@dataclass(frozen=True, slots=True)
class MoonPhase:
    """Parent-center phase, with nominal illumination before shadowing."""

    angle_deg: float
    illuminated_fraction: float
    emission_offset_days: float


@dataclass(frozen=True, slots=True)
class PlanetaryMoon:
    """Geometric parent-relative ICRF state and observer-dependent phenomena.

    Eclipse means solar-disk coverage at the moon's Earth-directed emission
    epoch. It can coexist with an Earth-view occultation or a full-like phase.
    """

    name: str
    naif_id: int
    planet: Planet
    planet_naif_id: int
    position_km: Vec3
    velocity_km_per_day: Vec3
    distance_km: float
    earth_view: EarthMoonView
    phase: MoonPhase
    eclipse: Literal["clear", "contact", "partial", "total"]
    eclipse_epoch_offset_days: float


@dataclass(frozen=True, slots=True)
class PlanetaryMoonSnapshot:
    """All requested moon states at one TT epoch and their source receipts."""

    jd_tt: float
    jd_tdb: float
    moons: tuple[PlanetaryMoon, ...]
    sources: tuple[PlanetaryMoonSource, ...]
    de441_sha256: str
    figure_pck_sha256: str = PCK_SHA256


def _read_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema": 1,
        "frame": "ICRF",
        "epoch": "TDB seconds past J2000",
        "pck_source": PCK_URL,
        "pck_sha256": PCK_SHA256,
        "moon_radii_source": RADII_URL,
    }
    if (not isinstance(manifest, dict) or type(manifest.get("schema")) is not int
            or any(manifest.get(k) != v for k, v in expected.items())):
        raise ValueError(f"Invalid planetary moons manifest: {path}")
    records = manifest.get("systems")
    if not isinstance(records, dict) or not records or records.keys() - {s.name for s in SYSTEMS}:
        raise ValueError("Planetary moons manifest must list Jupiter, Saturn, or both")
    return records


def _open_satellites(stack: ExitStack, directory: Path, system: MoonSystem, record: dict) -> SpkReader:
    filename = f"{Path(system.source).stem}-moons.bsp"
    if (not isinstance(record, dict) or record.get("filename") != filename
            or record.get("source_url") != NAIF_SATELLITES + system.source
            or record.get("source_sha256") != system.source_sha256):
        raise ValueError(f"Invalid source receipt for {system.name}")
    reader = stack.enter_context(SpkReader(directory / filename))
    if (record.get("sha256") != reader._source_identity.sha256
            or record.get("bytes") != reader._source_identity.byte_length):
        raise ValueError(f"Extract hash or length disagrees for {system.name}")
    segments = segment_receipt(reader._kernel.catalog)
    if (segments != record.get("segments")
            or set(reader._coverage_pairs_tdb()) != segment_pairs(system)
            or any(row["frame"] != 1 for row in segments)):
        raise ValueError(f"Invalid segment receipt for {system.name}")
    return reader


def _coverage(base: SpkReader, satellite: SpkReader, system: MoonSystem) -> tuple[tuple[float, float], ...]:
    intervals = base.coverage_intervals_tdb(0, system.barycenter)
    for center, target in ((0, 3), (3, 399), (0, 10)):
        intervals = _intersect_closed_intervals(intervals, base.coverage_intervals_tdb(center, target))
    for center, target in sorted(segment_pairs(system)):
        intervals = _intersect_closed_intervals(intervals, satellite.coverage_intervals_tdb(center, target))
    if not intervals:
        raise ValueError(f"No common DE441 and satellite coverage for {system.name}")
    return intervals


def _received(body: int, observer: Vec3, offset: float, position) -> tuple[Vec3, float]:
    # Retain the TDB offset through the iteration. The pool selects a route at
    # each emission rather than assuming the reception segment still applies.
    _, delay = _iterate_light_time(
        observer,
        position(body, offset),
        lambda delay: position(body, offset - delay),
        guard_norm=True,
    )
    emission = offset - delay
    direction = vec_sub(position(body, emission), observer)
    if abs(vec_norm(direction) / C_KM_PER_DAY - delay) > 1e-14:
        raise ArithmeticError(f"Light time did not converge for NAIF body {body}")
    return direction, emission


def _moon_at(system: MoonSystem, identity: MoonIdentity, epoch: float,
             parent: Vec3, earth: Vec3, earth_planet: Vec3, planet_emission: float,
             state, position) -> PlanetaryMoon:
    body = identity.naif_id
    xyz, velocity = state(system.center, body)

    earth_moon, moon_emission = _received(body, earth, 0.0, position)
    east, north = sky_offsets_arcsec(earth_planet, earth_moon)
    depth = vec_norm(earth_moon) - vec_norm(earth_planet)
    overlap = disk_overlap(
        earth_planet, planet_pole(system, epoch, planet_emission), system.radii_km,
        earth_moon, identity.radius_km,
    )
    event = None
    if overlap in ("partial", "contained"):
        event = "transit" if depth < 0.0 else "occultation"
    view = EarthMoonView(east, north, depth, moon_emission, planet_emission, overlap, event)

    parent_moon, phase_emission = _received(body, parent, 0.0, position)
    moon_at_phase = vec_add(parent, parent_moon)
    phase_sun, _ = _received(10, moon_at_phase, phase_emission, position)
    phase_angle = angle_between(phase_sun, vec_scale(parent_moon, -1.0))
    phase = MoonPhase(degrees(phase_angle), (1.0 + cos(phase_angle)) / 2.0, phase_emission)

    moon_at_eclipse = vec_add(earth, earth_moon)
    eclipse_planet, shade_emission = _received(system.center, moon_at_eclipse, moon_emission, position)
    eclipse_sun, _ = _received(10, moon_at_eclipse, moon_emission, position)
    obscuration = disk_overlap(
        eclipse_planet, planet_pole(system, epoch, shade_emission), system.radii_km,
        eclipse_sun, SUN_RADIUS_KM,
    )
    eclipse = "total" if obscuration == "contained" else obscuration
    return PlanetaryMoon(
        identity.name, body, system.name, system.center, xyz, velocity, vec_norm(xyz),
        view, phase, eclipse, moon_emission,
    )


class PlanetaryMoons:
    """
    RITE: Planetary moon snapshot context
    THEOREM: A fixed DE441 and satellite source set serves complete timed snapshots.

    RITE OF PURPOSE:
        Own the explicitly opened SPK resources and expose their geometric and
        reception-time moon states without ambient reader configuration.

    LAW OF OPERATION:
        Validate manifests and exact body pairs before opening the context to
        callers. Resolve every emission epoch using the same leased pool.
        Return immutable results or raise when the requested data is unavailable.

    Canon: JPL JUP365 and SAT441, DE441, and the NAIF PCK00011 planet figures.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.planetary_moons.PlanetaryMoons",
      "risk": "high",
      "api": {"frozen": ["open", "at", "coverage_tdb", "close"]},
      "state": {"mutable": true, "owners": ["owned kernel pool lifecycle"]},
      "effects": {"signals_emitted": [], "io": ["explicit local SPK and manifest access"]},
      "concurrency": {
        "thread": "request_local",
        "cross_thread_calls": "forbidden",
        "owner_thread_only_mutation": true
      },
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, pool: KernelPool, base_hash: str, sources: dict,
                 coverage: dict) -> None:
        self._pool = pool
        self._base_hash = base_hash
        self._sources = sources
        self._coverage = coverage

    @classmethod
    def open(cls, *, de441_path: str | Path, manifest_path: str | Path) -> "PlanetaryMoons":
        """Bind DE441 and one or both explicitly installed satellite systems."""
        path = Path(manifest_path)
        records = _read_manifest(path)
        with ExitStack() as opens:
            base = opens.enter_context(SpkReader(de441_path))
            if base._kernel_identity.planetary_ephemeris != "DE441":
                raise ValueError("Planetary moons require the DE441 planetary kernel")
            satellite_targets = {
                target for system in SYSTEMS for _, target in segment_pairs(system)
            }
            if any(target in satellite_targets for _, target in base._coverage_pairs_tdb()):
                raise ValueError("The DE441 reader cannot supply satellite body centers")
            sources, coverage = {}, {}
            readers = [base]
            for system in SYSTEMS:
                if system.name not in records:
                    continue
                record = records[system.name]
                reader = _open_satellites(opens, path.parent, system, record)
                coverage[system.name] = _coverage(base, reader, system)
                sources[system.name] = PlanetaryMoonSource(
                    system.name, record["source_url"], record["source_sha256"], record["sha256"],
                )
                readers.append(reader)
            pool = KernelPool(readers)
            context = cls(pool, base._source_identity.sha256, sources, coverage)
            opens.pop_all()
            return context

    def coverage_tdb(self) -> dict[Planet, tuple[tuple[float, float], ...]]:
        """Return joint state intervals per installed planet as closed TDB JDs.

        Reception queries also require each retarded evaluation to be covered.
        """
        with self._pool._read_lease():
            return dict(self._coverage)

    def at(self, jd_tt: float, *, planet: Planet | None = None) -> PlanetaryMoonSnapshot:
        """Calculate all twelve moons, or one explicitly requested system."""
        if isinstance(jd_tt, bool) or not isfinite(jd_tt):
            raise ValueError("jd_tt must be a finite Julian day in TT")
        systems = tuple(s for s in SYSTEMS if planet is None or s.name == planet)
        if not systems:
            raise ValueError(f"Unsupported planetary moon system: {planet!r}")
        with self._pool._read_lease() as lease:
            for system in systems:
                if system.name not in self._sources:
                    raise FileNotFoundError(f"Install the satellite extract for {system.name}")
            epoch = tt_to_tdb(jd_tt)

            def position(body: int, offset: float = 0.0) -> Vec3:
                return self._pool._position_tdb_offset(0, body, epoch, offset, snapshot=lease)

            def state(center: int, target: int) -> tuple[Vec3, Vec3]:
                return self._pool._position_and_velocity_tdb_offset(
                    center, target, epoch, 0.0, snapshot=lease,
                )

            earth = position(399)
            moons = []
            for system in systems:
                parent = position(system.center)
                earth_planet, planet_emission = _received(system.center, earth, 0.0, position)
                moons.extend(_moon_at(
                    system, identity, epoch, parent, earth, earth_planet, planet_emission,
                    state, position,
                ) for identity in system.moons)
            sources = tuple(self._sources[system.name] for system in systems)
            return PlanetaryMoonSnapshot(jd_tt, epoch, tuple(moons), sources, self._base_hash)

    def close(self) -> None:
        """Close the planetary and satellite readers owned by this context."""
        self._pool.close()

    def __enter__(self) -> "PlanetaryMoons":
        """Return the reusable context."""
        return self

    def __exit__(self, *exc) -> None:
        """Close the context on every exit."""
        self.close()
