#!/usr/bin/env python3
"""Capture and compare Orbital Core Stage 1 compatibility witnesses.

The capture command is intentionally runnable by two separately installed
Moira builds.  It records stable logical inputs, path-free resource identities,
and representative values from every protected consumer family named by the
Stage 1 plan.  The compare command turns those two snapshots into the three
reviewable release receipts without importing either build.

This is a measurement tool, not a golden-file updater.  It never downloads a
resource and never rewrites accepted primary-source fixtures.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
import json
import math
import os
import platform
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any


SCHEMA_CAPTURE = "moira.orbital-core-stage1.compatibility-capture/v1"
SCHEMA_CLOCK = "moira.orbital-core-stage1.reader-clock-shift/v1"
SCHEMA_FRAME = "moira.orbital-core-stage1.frame-shift/v1"
SCHEMA_VALIDATION = "moira.orbital-core-stage1.validation/v1"
MEASUREMENT_DATE = "2026-09-15"
JD_UT1 = 2_460_676.5
OBSERVER = {
    "latitude_deg": 42.2917,
    "longitude_deg": -85.5872,
    "elevation_m": 256.0,
}
PLANET_BODIES = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
FRAME_EPOCHS_TT = {
    "ancient": 2_086_302.5,
    "iau2006_lower_boundary": 2_415_020.0,
    "j2000": 2_451_545.0,
    "iau2006_upper_boundary": 2_488_070.0,
    "far_future": 2_816_787.5,
}
REQUIRED_PROBES = {
    "clock": {"raw_states"},
    "planetary": {"planet_at", "all_planets_native", "all_planets_python"},
    "small_bodies": {"asteroid", "comet"},
    "searches": {"aspect_transit", "fixed_star_heliacal"},
    "eclipses": {"solar", "lunar"},
    "lunar_geometry": {"limb_light_cone", "occultation_separation"},
    "phase_phenomena": {"phase", "phenomena"},
    "shadbala": {"end_to_end"},
    "frames": {"matrices", "true_node", "galactic_points", "sky_position"},
}
FRAME_RECEIPT_GROUPS = {
    "frames",
    "planetary",
    "eclipses",
    "lunar_geometry",
}
_WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?:[a-z]:[\\/])[^\r\n\t\"']+")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize(value: Any) -> Any:
    """Return deterministic JSON data without leaking local paths."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite compatibility value: {value!r}")
        return value
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, Path):
        return value.name
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _normalize(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if hasattr(value, "__dict__"):
        return {
            str(key): _normalize(item)
            for key, item in sorted(vars(value).items())
            if not str(key).startswith("_")
        }
    return str(value)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    normalized = _normalize(payload)
    rendered = json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if _WINDOWS_ABSOLUTE_PATH.search(rendered):
        raise ValueError("compatibility artifact contains a local absolute path")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8", newline="\n")


def _probe(operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"status": "ok", "data": _normalize(operation())}
    except Exception as exc:  # measurement must preserve per-surface failure
        return {
            "status": "error",
            "error_type": type(exc).__name__,
        }


def _selected(value: Any, names: Iterable[str]) -> dict[str, Any]:
    return {name: _normalize(getattr(value, name)) for name in names}


def _planet_row(value: Any) -> dict[str, Any]:
    return _selected(
        value,
        ("longitude", "latitude", "distance", "speed", "retrograde"),
    )


def _state_row(state: tuple[Sequence[float], Sequence[float]]) -> dict[str, Any]:
    position, velocity = state
    return {
        "position_km": [float(item) for item in position],
        "velocity_km_per_day": [float(item) for item in velocity],
    }


def _max_vector_delta(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    return max(
        abs(float(a) - float(b))
        for key in ("position_km", "velocity_km_per_day")
        for a, b in zip(left[key], right[key])
    )


def _resource_receipt() -> tuple[Path, dict[str, Any], list[Path]]:
    from moira._kernel_paths import (
        find_all_small_body_manifests,
        find_planetary_kernel,
    )

    planetary_path = find_planetary_kernel()
    if planetary_path is None:
        raise FileNotFoundError("no admitted planetary kernel is installed")
    planetary_path = Path(planetary_path)
    manifests = [Path(path) for path in find_all_small_body_manifests()]
    manifest_receipts = []
    for path in manifests:
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifest_receipts.append(
            {
                "filename": path.name,
                "sha256": _sha256(path),
                "catalog_id": payload.get("catalog_id"),
                "catalog_version": payload.get("catalog_version"),
                "body_count": payload.get("body_count"),
                "shard_count": payload.get("shard_count"),
                "released_utc": (payload.get("release") or {}).get("released_utc"),
            }
        )
    return (
        planetary_path,
        {
            "planetary": {
                "filename": planetary_path.name,
                "sha256": _sha256(planetary_path),
                "bytes": planetary_path.stat().st_size,
                "identity": "DE441" if planetary_path.name.casefold() == "de441.bsp" else None,
            },
            "small_body_manifests": manifest_receipts,
        },
        manifests,
    )


def _raw_state_probe(reader: Any, jd_ut1: float) -> dict[str, Any]:
    from moira._ephemeris_time import _ut1_to_ephemeris_tt
    from moira.julian import tt_to_tdb

    jd_tt = float(_ut1_to_ephemeris_tt(jd_ut1, reader))
    jd_tdb = float(tt_to_tdb(jd_tt))
    result: dict[str, Any] = {
        "jd_ut1": jd_ut1,
        "jd_tt": jd_tt,
        "jd_tdb": jd_tdb,
        "tdb_minus_tt_seconds": (jd_tdb - jd_tt) * 86_400.0,
        "routes": {},
    }
    explicit_tdb = getattr(reader, "position_and_velocity_tdb", None)
    for center, target in ((0, 10), (0, 4), (3, 301), (3, 399)):
        name = f"{center}_to_{target}"
        tt_wrapper = _state_row(reader.position_and_velocity(center, target, jd_tt))
        row: dict[str, Any] = {"tt_wrapper": tt_wrapper}
        if callable(explicit_tdb):
            at_numeric_tt = _state_row(explicit_tdb(center, target, jd_tt))
            once = _state_row(explicit_tdb(center, target, jd_tdb))
            twice_tdb = float(tt_to_tdb(jd_tdb))
            twice = _state_row(explicit_tdb(center, target, twice_tdb))
            row.update(
                {
                    "tdb_explicit_at_numeric_tt": at_numeric_tt,
                    "tdb_explicit_once": once,
                    "tdb_explicit_twice": twice,
                    "tt_adapter_once_residual": _max_vector_delta(tt_wrapper, once),
                    "once_vs_twice_delta": _max_vector_delta(once, twice),
                }
            )
        result["routes"][name] = row
    return result


def _planet_probes(reader: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    import moira.planets as planets_module
    from moira.planets import all_planets_at, planet_at

    singles = {
        body: _planet_row(planet_at(body, JD_UT1, reader=reader))
        for body in PLANET_BODIES
    }
    native = {
        body: _planet_row(value)
        for body, value in all_planets_at(
            JD_UT1,
            bodies=list(PLANET_BODIES),
            reader=reader,
        ).items()
    }
    original = planets_module._native_all_planets_admitted
    try:
        planets_module._native_all_planets_admitted = lambda *args, **kwargs: None
        python = {
            body: _planet_row(value)
            for body, value in all_planets_at(
                JD_UT1,
                bodies=list(PLANET_BODIES),
                reader=reader,
            ).items()
        }
    finally:
        planets_module._native_all_planets_admitted = original
    return singles, native, python


def _small_body_probes(pool: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    from moira.asteroids import asteroid_at
    from moira.comets import comet_at

    asteroid = asteroid_at("Ceres", JD_UT1, reader=pool)
    comet = comet_at("1P/Halley", JD_UT1, reader=pool)
    fields = ("name", "naif_id", "longitude", "latitude", "distance", "speed", "retrograde")
    return _selected(asteroid, fields), _selected(comet, fields)


def _transit_probe(reader: Any) -> dict[str, Any]:
    from moira.transits_aspects import find_aspect_transits

    events = find_aspect_transits(
        "Mercury",
        265.0,
        0.0,
        0.5,
        JD_UT1,
        JD_UT1 + 10.0,
        reader=reader,
    )
    return {
        "input": {
            "body": "Mercury",
            "target_longitude_deg": 265.0,
            "aspect_angle_deg": 0.0,
            "orb_deg": 0.5,
            "jd_start_ut1": JD_UT1,
            "jd_end_ut1": JD_UT1 + 10.0,
        },
        "events": [
            _selected(
                event,
                (
                    "jd_exact",
                    "jd_entering",
                    "jd_leaving",
                    "is_retrograde_hit",
                    "search_motion",
                ),
            )
            for event in events
        ],
    }


def _heliacal_probe() -> dict[str, Any]:
    from moira.stars import heliacal_rising_event

    event = heliacal_rising_event(
        "Sirius",
        JD_UT1,
        31.2,
        29.9,
        arcus_visionis=10.0,
        search_days=250,
    )
    payload = _normalize(event)
    return {
        "input": {
            "star": "Sirius",
            "jd_start_ut1": JD_UT1,
            "latitude_deg": 31.2,
            "longitude_deg": 29.9,
            "arcus_visionis_deg": 10.0,
            "search_days": 250,
        },
        "event": payload,
    }


def _eclipse_row(event: Any) -> dict[str, Any]:
    data = event.data
    return {
        "jd_ut1": float(event.jd_ut),
        "eclipse_type": _normalize(data.eclipse_type),
        "eclipse_magnitude": float(data.eclipse_magnitude),
        "sun_longitude_deg": float(data.sun_longitude),
        "moon_longitude_deg": float(data.moon_longitude),
        "moon_latitude_deg": float(data.moon_latitude),
        "angular_separation_3d_deg": float(data.angular_separation_3d),
    }


def _eclipse_probes(reader: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    from moira.eclipse import EclipseCalculator

    calculator = EclipseCalculator(reader)
    return (
        _eclipse_row(calculator.next_solar_eclipse(JD_UT1)),
        _eclipse_row(calculator.next_lunar_eclipse(JD_UT1)),
    )


def _limb_probe(reader: Any) -> dict[str, Any]:
    from moira.lunar_limb import _reader_bound_moon_light_cone

    cone = _reader_bound_moon_light_cone(
        JD_UT1,
        OBSERVER["latitude_deg"],
        OBSERVER["longitude_deg"],
        OBSERVER["elevation_m"],
        reader,
    )
    return {
        "input": {"jd_ut1": JD_UT1, **OBSERVER},
        "jd_tt_reception": float(cone.jd_tt_reception),
        "jd_tt_emission": float(cone.jd_tt_emission),
        "distance_km": float(cone.distance_km),
        "observer_to_moon_icrf": [float(value) for value in cone.observer_to_moon_icrf],
        "icrf_to_true_of_date": _normalize(cone.icrf_to_true_of_date),
        "translation_label": str(cone.translation_label),
    }


def _occultation_probe(reader: Any) -> dict[str, Any]:
    from moira.constants import Body
    from moira.occultations import _sep_between

    return {
        "input": {"body1": "Moon", "body2": "Mars", "jd_ut1": JD_UT1},
        "separation_deg": float(_sep_between(Body.MOON, Body.MARS, JD_UT1, reader)),
    }


def _phase_probes() -> tuple[dict[str, Any], dict[str, Any]]:
    from moira.phase import (
        angular_diameter,
        apparent_magnitude,
        elongation,
        illuminated_fraction,
        phase_angle,
    )
    from moira.phenomena import planet_phenomena_at

    angle = float(phase_angle("Venus", JD_UT1))
    phase = {
        "body": "Venus",
        "jd_ut1": JD_UT1,
        "phase_angle_deg": angle,
        "illuminated_fraction": float(illuminated_fraction(angle)),
        "elongation_deg": float(elongation("Venus", JD_UT1)),
        "angular_diameter_arcsec": float(angular_diameter("Venus", JD_UT1)),
        "apparent_magnitude": float(apparent_magnitude("Venus", JD_UT1)),
    }
    phenomena = _normalize(planet_phenomena_at("Mars", JD_UT1))
    return phase, phenomena


def _shadbala_probe(reader: Any) -> dict[str, Any]:
    from moira.planets import all_planets_at
    from moira.sidereal import tropical_to_sidereal

    shadbala_module = importlib.import_module("moira.shadbala")

    class EqualHouses:
        asc = 0.0
        cusps = tuple(float(index * 30) for index in range(12))

    bodies = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    planets = all_planets_at(JD_UT1, bodies=list(bodies), reader=reader)
    longitudes = {
        body: float(
            tropical_to_sidereal(
                planets[body].longitude,
                JD_UT1,
                system="Lahiri",
            )
        )
        for body in bodies
    }
    speeds = {body: float(planets[body].speed) for body in bodies}
    tithi = int(((planets["Moon"].longitude - planets["Sun"].longitude) % 360.0) // 12.0) + 1
    # Kala Bala asks for the same annual and monthly Sankranti for each of the
    # seven planets.  Cache only those identical calls during this measurement;
    # the owning algorithm and every returned value remain unchanged.
    original_sankranti = shadbala_module._sankranti_jd
    shadbala_module._sankranti_jd = lru_cache(maxsize=None)(original_sankranti)
    try:
        result = shadbala_module.shadbala(
            sidereal_longitudes=longitudes,
            planet_speeds=speeds,
            houses=EqualHouses(),
            jd=JD_UT1,
            tithi_number=tithi,
            vara_lord="Sun",
            is_day=True,
            ayanamsa_system="Lahiri",
        )
    finally:
        shadbala_module._sankranti_jd = original_sankranti
    return {
        "input": {
            "jd_ut1": JD_UT1,
            "tithi_number": tithi,
            "vara_lord": "Sun",
            "is_day": True,
            "ayanamsa_system": "Lahiri",
            "sidereal_longitudes_deg": longitudes,
            "planet_speeds_deg_per_day": speeds,
        },
        "planets": {
            body: _selected(
                result.planets[body],
                (
                    "dig_bala",
                    "chesta_bala",
                    "naisargika_bala",
                    "drig_bala",
                    "total_shashtiamsas",
                    "total_rupas",
                    "required_rupas",
                    "is_sufficient",
                ),
            )
            for body in bodies
        },
    }


def _frame_probes(reader: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    from moira._ephemeris_time import _ut1_to_ephemeris_tt
    from moira.galactic import galactic_reference_points
    from moira.nodes import true_node
    from moira.obliquity import true_obliquity
    from moira.planets import sky_position_at
    from moira.precession import precession_matrix

    matrices = {
        label: {
            "jd_tt": jd_tt,
            "matrix": _normalize(precession_matrix(jd_tt)),
        }
        for label, jd_tt in FRAME_EPOCHS_TT.items()
    }
    node = _selected(true_node(JD_UT1, reader=reader), ("longitude", "speed"))
    jd_tt = float(_ut1_to_ephemeris_tt(JD_UT1, reader))
    galactic = {
        name: [float(value) for value in coordinates]
        for name, coordinates in galactic_reference_points(
            true_obliquity(jd_tt),
            jd_tt,
        ).items()
    }
    sky = _selected(
        sky_position_at(
            "Mars",
            JD_UT1,
            OBSERVER["latitude_deg"],
            OBSERVER["longitude_deg"],
            OBSERVER["elevation_m"],
            reader=reader,
            refraction=False,
        ),
        ("right_ascension", "declination", "azimuth", "altitude", "distance"),
    )
    return matrices, node, galactic, sky


def capture(label: str, revision: str, output: Path) -> None:
    if os.environ.get("MOIRA_NO_DOWNLOAD") != "1":
        raise RuntimeError("capture requires MOIRA_NO_DOWNLOAD=1")

    import moira
    from moira import moira_native
    from moira._spk_body_kernel import small_body_readers_from_manifest
    from moira.spk_reader import KernelPool, SpkReader, use_reader_override

    planetary_path, resources, manifests = _resource_receipt()
    readers: list[Any] = []
    pool = None
    try:
        primary = SpkReader(planetary_path)
        readers.append(primary)
        for manifest in manifests:
            readers.extend(small_body_readers_from_manifest(manifest))
        pool = KernelPool(tuple(readers))

        probes: dict[str, dict[str, Any]] = {
            group: {} for group in REQUIRED_PROBES
        }

        def record(group: str, name: str, operation: Callable[[], Any]) -> None:
            print(f"capture {label}: {group}.{name}", flush=True)
            probes[group][name] = _probe(operation)

        def record_bundle(
            group: str,
            names: tuple[str, ...],
            operation: Callable[[], tuple[Any, ...]],
        ) -> None:
            print(f"capture {label}: {group}.{'/'.join(names)}", flush=True)
            try:
                values = operation()
            except Exception as exc:
                failure = {"status": "error", "error_type": type(exc).__name__}
                for name in names:
                    probes[group][name] = failure.copy()
            else:
                if len(values) != len(names):
                    raise RuntimeError("compatibility probe bundle length mismatch")
                for name, value in zip(names, values):
                    probes[group][name] = {"status": "ok", "data": _normalize(value)}

        record("clock", "raw_states", lambda: _raw_state_probe(primary, JD_UT1))
        record_bundle(
            "planetary",
            ("planet_at", "all_planets_native", "all_planets_python"),
            lambda: _planet_probes(primary),
        )
        record_bundle(
            "small_bodies",
            ("asteroid", "comet"),
            lambda: _small_body_probes(pool),
        )
        record("searches", "aspect_transit", lambda: _transit_probe(primary))
        with use_reader_override(primary):
            record("searches", "fixed_star_heliacal", _heliacal_probe)
            record_bundle(
                "phase_phenomena",
                ("phase", "phenomena"),
                _phase_probes,
            )
            record("shadbala", "end_to_end", lambda: _shadbala_probe(primary))
        record_bundle(
            "eclipses",
            ("solar", "lunar"),
            lambda: _eclipse_probes(primary),
        )
        record("lunar_geometry", "limb_light_cone", lambda: _limb_probe(primary))
        record(
            "lunar_geometry",
            "occultation_separation",
            lambda: _occultation_probe(primary)
        )
        record_bundle(
            "frames",
            ("matrices", "true_node", "galactic_points", "sky_position"),
            lambda: _frame_probes(primary),
        )

        backend = getattr(moira_native, "__backend_file__", None)
        payload = {
            "schema": SCHEMA_CAPTURE,
            "measurement_date": MEASUREMENT_DATE,
            "label": label,
            "source": {
                "revision": revision,
                "moira_version": getattr(moira, "__version__", None),
                "python": platform.python_version(),
                "implementation": platform.python_implementation(),
                "platform": platform.system(),
                "native_backend_filename": None if backend is None else Path(backend).name,
            },
            "network_boundary": {
                "moira_no_download": True,
                "external_network_used": False,
            },
            "logical_inputs": {
                "jd_ut1": JD_UT1,
                "observer": OBSERVER,
                "frame_epochs_tt": FRAME_EPOCHS_TT,
            },
            "resources": resources,
            "probes": probes,
        }
        _write_json(output, payload)
    finally:
        if pool is not None:
            pool.close()
        else:
            for reader in reversed(readers):
                reader.close()


def _numeric_leaves(value: Any, prefix: str = "") -> dict[str, float]:
    result: dict[str, float] = {}
    if isinstance(value, bool) or value is None:
        return result
    if isinstance(value, (int, float)):
        result[prefix] = float(value)
        return result
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            result.update(_numeric_leaves(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]"
            result.update(_numeric_leaves(item, child))
    return result


def _comparison(baseline: Any, candidate: Any) -> dict[str, Any]:
    left = _numeric_leaves(baseline)
    right = _numeric_leaves(candidate)
    shared = sorted(set(left) & set(right))
    changes = [
        {
            "path": path,
            "baseline": left[path],
            "candidate": right[path],
            "delta": right[path] - left[path],
        }
        for path in shared
        if right[path] != left[path]
    ]
    changes.sort(key=lambda item: (-abs(item["delta"]), item["path"]))
    return {
        "shared_numeric_field_count": len(shared),
        "changed_numeric_field_count": len(changes),
        "unchanged_numeric_field_count": len(shared) - len(changes),
        "max_absolute_delta": max((abs(item["delta"]) for item in changes), default=0.0),
        "deltas": changes,
    }


def _probe_statuses(snapshot: Mapping[str, Any]) -> dict[str, str]:
    return {
        f"{group}.{name}": snapshot["probes"][group][name]["status"]
        for group, names in REQUIRED_PROBES.items()
        for name in sorted(names)
    }


def _subset(snapshot: Mapping[str, Any], groups: set[str]) -> dict[str, Any]:
    return {
        group: snapshot["probes"][group]
        for group in sorted(groups)
    }


def _clock_checks(baseline: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    baseline_raw = baseline["probes"]["clock"]["raw_states"]["data"]
    candidate_raw = candidate["probes"]["clock"]["raw_states"]["data"]
    route_checks: dict[str, Any] = {}
    for route, row in candidate_raw["routes"].items():
        baseline_wrapper = baseline_raw["routes"][route]["tt_wrapper"]
        legacy_replay = row["tdb_explicit_at_numeric_tt"]
        once = row["tdb_explicit_once"]
        twice = row["tdb_explicit_twice"]
        route_checks[route] = {
            "baseline_equals_candidate_legacy_numeric_tdb_max_residual": _max_vector_delta(
                baseline_wrapper,
                legacy_replay,
            ),
            "candidate_tt_wrapper_equals_one_tdb_conversion_max_residual": _max_vector_delta(
                row["tt_wrapper"],
                once,
            ),
            "one_vs_two_tdb_conversions_max_delta": _max_vector_delta(once, twice),
        }
    return {
        "tdb_minus_tt_seconds": candidate_raw["tdb_minus_tt_seconds"],
        "routes": route_checks,
        "all_legacy_replays_exact_to_1e_12": all(
            row["baseline_equals_candidate_legacy_numeric_tdb_max_residual"] <= 1.0e-12
            for row in route_checks.values()
        ),
        "all_tt_adapters_exactly_once_to_1e_12": all(
            row["candidate_tt_wrapper_equals_one_tdb_conversion_max_residual"] <= 1.0e-12
            for row in route_checks.values()
        ),
        "second_conversion_is_observably_distinct": all(
            row["one_vs_two_tdb_conversions_max_delta"] > 0.0
            for row in route_checks.values()
        ),
    }


def _native_python_check(candidate: Mapping[str, Any]) -> dict[str, Any]:
    native = candidate["probes"]["planetary"]["all_planets_native"]["data"]
    python = candidate["probes"]["planetary"]["all_planets_python"]["data"]
    comparison = _comparison(native, python)
    return {
        **comparison,
        "within_1e_9": comparison["max_absolute_delta"] <= 1.0e-9,
    }


def _identity(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": snapshot["source"],
        "resources": snapshot["resources"],
        "network_boundary": snapshot["network_boundary"],
    }


def compare(
    baseline_path: Path,
    candidate_path: Path,
    output_directory: Path,
    *,
    full_catalog_status: str,
    live_primary_status: str,
    targeted_status: str,
    non_network_status: str,
    documentation_status: str,
    consumer_inventory_status: str,
    changed_file_ruff_status: str,
    diff_check_status: str,
    native_status: str,
    kernel_status: str,
    targeted_collected_count: int,
    targeted_skipped_count: int,
    targeted_skip_reasons: Sequence[str],
    native_passed_count: int,
    kernel_passed_count: int,
    live_primary_passed_count: int,
    full_catalog_skipped_count: int,
) -> None:
    counts = (
        targeted_collected_count,
        targeted_skipped_count,
        native_passed_count,
        kernel_passed_count,
        live_primary_passed_count,
        full_catalog_skipped_count,
    )
    if any(count < 0 for count in counts):
        raise ValueError("test evidence counts must be nonnegative")
    if targeted_skipped_count > targeted_collected_count:
        raise ValueError("targeted skipped count exceeds collected count")
    if len(targeted_skip_reasons) != targeted_skipped_count:
        raise ValueError("targeted skip reasons must match targeted skipped count")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != SCHEMA_CAPTURE or candidate.get("schema") != SCHEMA_CAPTURE:
        raise ValueError("unsupported compatibility capture schema")
    if baseline["logical_inputs"] != candidate["logical_inputs"]:
        raise ValueError("baseline and candidate logical inputs differ")
    if baseline["resources"] != candidate["resources"]:
        raise ValueError("baseline and candidate resource identities differ")

    baseline_status = _probe_statuses(baseline)
    candidate_status = _probe_statuses(candidate)
    required_probes_green = all(
        value == "ok" for value in (*baseline_status.values(), *candidate_status.values())
    )
    clock_groups = set(REQUIRED_PROBES) - FRAME_RECEIPT_GROUPS
    clock_baseline = _subset(baseline, clock_groups)
    clock_candidate = _subset(candidate, clock_groups)
    frame_baseline = _subset(baseline, FRAME_RECEIPT_GROUPS)
    frame_candidate = _subset(candidate, FRAME_RECEIPT_GROUPS)
    clock_checks = _clock_checks(baseline, candidate)
    native_python = _native_python_check(candidate)

    common = {
        "measurement_date": MEASUREMENT_DATE,
        "baseline_identity": _identity(baseline),
        "candidate_identity": _identity(candidate),
        "logical_inputs": candidate["logical_inputs"],
        "commands": {
            "baseline_capture": "<baseline-python> measure_orbital_stage1_compatibility.py capture",
            "candidate_capture": "<candidate-python> measure_orbital_stage1_compatibility.py capture",
            "comparison": "<candidate-python> measure_orbital_stage1_compatibility.py compare",
        },
    }
    clock_receipt = {
        "schema": SCHEMA_CLOCK,
        **common,
        "status": "review_ready" if required_probes_green and all(
            (
                clock_checks["all_legacy_replays_exact_to_1e_12"],
                clock_checks["all_tt_adapters_exactly_once_to_1e_12"],
                clock_checks["second_conversion_is_observably_distinct"],
                native_python["within_1e_9"],
            )
        ) else "failed",
        "probe_status": {"baseline": baseline_status, "candidate": candidate_status},
        "clock_witness": clock_checks,
        "candidate_native_python_parity": native_python,
        "numeric_comparison": _comparison(clock_baseline, clock_candidate),
    }
    frame_receipt = {
        "schema": SCHEMA_FRAME,
        **common,
        "status": "review_ready" if required_probes_green else "failed",
        "authority": "IAU SOFA Issue 2023-10-11 frozen fixture",
        "ownership_rule": "one bias-inclusive precession route; no preceding duplicate bias",
        "component_isolation": {
            "authority_matrix_comparison": (
                "frames.matrices is a frame-only comparison at fixed TT epochs"
            ),
            "consumer_comparison": (
                "planetary, eclipse, and lunar-geometry probes contain the combined "
                "reader-clock and frame corrections"
            ),
            "reader_clock_component": (
                "separately measured in the reader-clock shift receipt"
            ),
            "reader_clock_receipt_status": clock_receipt["status"],
        },
        "probe_status": {"baseline": baseline_status, "candidate": candidate_status},
        "numeric_comparison": _comparison(frame_baseline, frame_candidate),
    }
    skips = []
    blockers = []
    if full_catalog_status != "passed":
        skips.append(full_catalog_status)
        blockers.append(full_catalog_status)
    if non_network_status != "passed":
        blockers.append(non_network_status)
    for status in (
        documentation_status,
        consumer_inventory_status,
        changed_file_ruff_status,
        diff_check_status,
        native_status,
        kernel_status,
    ):
        if status != "passed":
            blockers.append(status)
    validation_green = (
        required_probes_green
        and clock_receipt["status"] == "review_ready"
        and frame_receipt["status"] == "review_ready"
        and targeted_status == "passed"
        and live_primary_status == "passed"
        and non_network_status == "passed"
        and documentation_status == "passed"
        and consumer_inventory_status == "passed"
        and changed_file_ruff_status == "passed"
        and diff_check_status == "passed"
        and native_status == "passed"
        and kernel_status == "passed"
        and not skips
    )
    validation_receipt = {
        "schema": SCHEMA_VALIDATION,
        **common,
        "status": "release_ready" if validation_green else "implementation_review_ready_release_blocked",
        "required_probe_count": len(baseline_status),
        "required_probes_green": required_probes_green,
        "test_gates": {
            "targeted_stage1": targeted_status,
            "non_external_network": non_network_status,
            "live_jpl_horizons": live_primary_status,
            "full_catalog": full_catalog_status,
            "documentation": documentation_status,
            "consumer_inventory": consumer_inventory_status,
            "changed_file_ruff": changed_file_ruff_status,
            "git_diff_check": diff_check_status,
            "native": native_status,
            "kernel_and_extraction": kernel_status,
        },
        "test_gate_counts": {
            "compatibility_probes": {
                "baseline_green": len(baseline_status),
                "candidate_green": len(candidate_status),
            },
            "targeted_stage1": {
                "collected": targeted_collected_count,
                "passed": targeted_collected_count - targeted_skipped_count,
                "skipped": targeted_skipped_count,
                "skip_reasons": list(targeted_skip_reasons),
            },
            "native": {"passed": native_passed_count},
            "kernel_and_extraction": {"passed": kernel_passed_count},
            "live_jpl_horizons": {"passed": live_primary_passed_count},
            "full_catalog": {"skipped": full_catalog_skipped_count},
        },
        "skips": skips,
        "blockers": blockers,
        "no_download": True,
        "release_or_deployment_performed": False,
        "clock_receipt_status": clock_receipt["status"],
        "frame_receipt_status": frame_receipt["status"],
    }

    _write_json(
        output_directory / "orbital_core_stage1_reader_clock_shift_2026-09-15.json",
        clock_receipt,
    )
    _write_json(
        output_directory / "orbital_core_stage1_frame_shift_2026-09-15.json",
        frame_receipt,
    )
    _write_json(
        output_directory / "orbital_core_stage1_validation_2026-09-15.json",
        validation_receipt,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture_parser = commands.add_parser("capture")
    capture_parser.add_argument("--label", required=True)
    capture_parser.add_argument("--revision", required=True)
    capture_parser.add_argument("--output", required=True, type=Path)

    compare_parser = commands.add_parser("compare")
    compare_parser.add_argument("--baseline", required=True, type=Path)
    compare_parser.add_argument("--candidate", required=True, type=Path)
    compare_parser.add_argument("--output-directory", required=True, type=Path)
    compare_parser.add_argument(
        "--full-catalog-status",
        default="NOT RUN - full moira-asteroids@2026.08.12.1 release not installed",
    )
    compare_parser.add_argument("--live-primary-status", default="not_run")
    compare_parser.add_argument("--targeted-status", default="not_run")
    compare_parser.add_argument("--non-network-status", default="not_run")
    compare_parser.add_argument("--documentation-status", default="not_run")
    compare_parser.add_argument("--consumer-inventory-status", default="not_run")
    compare_parser.add_argument("--changed-file-ruff-status", default="not_run")
    compare_parser.add_argument("--diff-check-status", default="not_run")
    compare_parser.add_argument("--native-status", default="not_run")
    compare_parser.add_argument("--kernel-status", default="not_run")
    compare_parser.add_argument("--targeted-collected-count", type=int, default=0)
    compare_parser.add_argument("--targeted-skipped-count", type=int, default=0)
    compare_parser.add_argument(
        "--targeted-skip-reason",
        action="append",
        default=[],
    )
    compare_parser.add_argument("--native-passed-count", type=int, default=0)
    compare_parser.add_argument("--kernel-passed-count", type=int, default=0)
    compare_parser.add_argument("--live-primary-passed-count", type=int, default=0)
    compare_parser.add_argument("--full-catalog-skipped-count", type=int, default=0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "capture":
        capture(args.label, args.revision, args.output)
        return 0
    compare(
        args.baseline,
        args.candidate,
        args.output_directory,
        full_catalog_status=args.full_catalog_status,
        live_primary_status=args.live_primary_status,
        targeted_status=args.targeted_status,
        non_network_status=args.non_network_status,
        documentation_status=args.documentation_status,
        consumer_inventory_status=args.consumer_inventory_status,
        changed_file_ruff_status=args.changed_file_ruff_status,
        diff_check_status=args.diff_check_status,
        native_status=args.native_status,
        kernel_status=args.kernel_status,
        targeted_collected_count=args.targeted_collected_count,
        targeted_skipped_count=args.targeted_skipped_count,
        targeted_skip_reasons=args.targeted_skip_reason,
        native_passed_count=args.native_passed_count,
        kernel_passed_count=args.kernel_passed_count,
        live_primary_passed_count=args.live_primary_passed_count,
        full_catalog_skipped_count=args.full_catalog_skipped_count,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
