"""Generate provisional native solar rows from a supplied discovery index.

This validation tool is not a NASA catalog or a release admission.  Contact
families are recorded independently, and any computation error fails the run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

os.environ["MOIRA_NO_DOWNLOAD"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import moira
import moira.eclipse as eclipse
from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira._eclipse_solar_geometry import _topocentric_solar_disc_geometry
from moira._kernel_paths import find_planetary_kernel
from moira.spk_reader import SpkReader
from discovery import source_fingerprint as discovery_fingerprint

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
CONTACT_NAMES = ("p1", "p2", "p3", "p4", "u1", "u2", "u3", "u4")
FIELDS = [
    "lunation_number",
    "index_jd_ut1",
    "status",
    "error",
    "jd_tt",
    "jd_ut1",
    "date_tt",
    "time_tt",
    "delta_t_seconds",
    "eclipse_type",
    "saros_series",
    "gamma_earth_radii",
    "site_latitude_deg",
    "site_longitude_deg",
    "site_definition",
    "magnitude",
    "obscuration",
    "local_class",
    "sun_altitude_deg",
    "sun_azimuth_deg",
    "instantaneous_support_width_km",
    "width_status",
    "width_reason",
    "full_phase_duration_seconds",
    "duration_status",
    "duration_reason",
    "duration_horizon_policy",
    "penumbral_contacts_status",
    "penumbral_contacts_error",
    "umbral_contacts_status",
    "umbral_contacts_error",
]
for _name in CONTACT_NAMES:
    FIELDS += [
        f"{_name}_status",
        f"{_name}_jd_tt",
        f"{_name}_jd_ut1",
        f"{_name}_latitude_deg",
        f"{_name}_longitude_deg",
    ]
FIELDS += [
    "sun_ecliptic_longitude_deg",
    "moon_ecliptic_longitude_deg",
    "surface_model",
    "limb_model",
    "elapsed_seconds",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_digest(root: Path) -> str:
    """Fingerprint every regular file apart from transient interpreter caches."""
    digest = hashlib.sha256()
    for path in sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix.lower() not in (".pyc", ".pyo")
    ):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def source_fingerprint() -> dict[str, str]:
    """Identify runtime source, data, native sources and this solar runner."""
    return {
        "engine_package_sha256": package_digest(Path(moira.__file__).resolve().parent),
        "native_source_sha256": package_digest(REPO_ROOT / "src" / "native"),
        "runner_sha256": sha256(Path(__file__)),
    }


def has_error(row: dict[str, str]) -> bool:
    """Distinguish computation errors from unavailable or inapplicable fields."""
    return any(
        row.get(field) == "error"
        for field in ("status", "penumbral_contacts_status", "umbral_contacts_status")
    )


def format_tt(jd: float) -> tuple[str, str]:
    # Julian before 1582-10-15; Gregorian thereafter; astronomical year.
    jd += 0.5 + 0.5 / 86400
    z = math.floor(jd)
    if z >= 2299161:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - math.floor(alpha / 4)
    else:
        a = z
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day = b - d - math.floor(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    second = min(86399, math.floor((jd - z) * 86400))
    return (
        f"{year:+05d}-{month:02d}-{day:02d}",
        f"{second // 3600:02d}:{second // 60 % 60:02d}:{second % 60:02d}",
    )


def contact_fields(row, name, jd_ut1, latitude, longitude, reader):
    row[f"{name}_status"] = "available"
    row[f"{name}_jd_ut1"] = jd_ut1
    row[f"{name}_jd_tt"] = _ut1_to_ephemeris_tt(jd_ut1, reader)
    row[f"{name}_latitude_deg"] = latitude
    row[f"{name}_longitude_deg"] = longitude


def compute(calc, reader, index_row, *, contacts):
    started = time.perf_counter()
    lunation = int(index_row["lunation_number"])
    seed = float(index_row["jd_ut1"])
    row = {"lunation_number": lunation, "index_jd_ut1": seed, "status": "ok"}
    valid_event = False
    try:
        event = calc.next_solar_eclipse(seed - 1)
        if event.data.saros_lunation_number != lunation:
            raise ValueError("index and computed lunation do not match")
        if abs(event.jd_ut - seed) > 0.02:
            raise ValueError("index and computed epoch differ by more than 0.02 days")
        valid_event = True
        jd_tt = _ut1_to_ephemeris_tt(event.jd_ut, reader)
        date, clock = format_tt(jd_tt)
        row.update(
            jd_tt=jd_tt,
            jd_ut1=event.jd_ut,
            date_tt=date,
            time_tt=clock,
            delta_t_seconds=(jd_tt - event.jd_ut) * 86400,
            eclipse_type=str(event.data.eclipse_type),
            saros_series=event.data.saros_series,
            sun_ecliptic_longitude_deg=event.data.sun_longitude,
            moon_ecliptic_longitude_deg=event.data.moon_longitude,
            surface_model="WGS84_ZERO_ELEVATION",
            limb_model="SPHERICAL_MEAN_LIMB",
        )
        b = calc.solar_besselian_elements(event.jd_ut)
        row["gamma_earth_radii"] = math.copysign(math.hypot(b.x, b.y), b.y)
        path = calc.solar_eclipse_path(seed - 1, sample_count=2)
        if path.eclipse_data.saros_lunation_number != lunation:
            raise ValueError("path and computed lunation do not match")
        discs = _topocentric_solar_disc_geometry(
            calc, event.jd_ut, path.max_eclipse_lat, path.max_eclipse_lon
        )
        axis = eclipse._solar_axis_surface_point(calc, event.jd_ut)
        row.update(
            site_latitude_deg=path.max_eclipse_lat,
            site_longitude_deg=path.max_eclipse_lon,
            site_definition=(
                "shadow_axis_intersection"
                if axis is not None
                else (
                    "native_partial_greatest_site"
                    if event.data.eclipse_type.is_partial
                    else "native_noncentral_greatest_site"
                )
            ),
            magnitude=discs.magnitude,
            obscuration=discs.obscuration,
            local_class=discs.local_class,
            sun_altitude_deg=discs.sun_altitude_deg,
            sun_azimuth_deg=discs.sun_azimuth_deg,
            instantaneous_support_width_km=(
                path.umbral_width_km
                if path.umbral_width_status == "available"
                else None
            ),
            width_status=path.umbral_width_status,
            width_reason=path.umbral_width_reason,
        )
        if discs.local_class in ("total", "annular") and path.duration_at_max_s > 0:
            row.update(
                full_phase_duration_seconds=path.duration_at_max_s,
                duration_status="available",
                duration_horizon_policy=(
                    "native_central_horizon_clipped"
                    if axis is not None
                    else "native_noncentral_unclipped"
                ),
            )
        elif discs.local_class in ("total", "annular"):
            row.update(
                duration_status="not_admitted",
                duration_reason="native_solver_returned_nonpositive_duration",
            )
        else:
            row.update(duration_status="not_applicable")
    except Exception as exc:
        row.update(status="error", error=f"{type(exc).__name__}: {exc}")
        row.setdefault("width_status", "not_computed")
        row.setdefault("duration_status", "not_computed")
        if not valid_event:
            row.update(
                penumbral_contacts_status="not_computed",
                umbral_contacts_status="not_computed",
            )
            for name in CONTACT_NAMES:
                row[f"{name}_status"] = "not_computed"
            row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            return row

    if not contacts:
        row.update(
            penumbral_contacts_status="not_requested",
            umbral_contacts_status="not_requested",
        )
        for name in CONTACT_NAMES:
            row[f"{name}_status"] = "not_requested"
    else:
        try:
            found, _ = eclipse._solve_solar_penumbral_contacts(calc, event.jd_ut)
            for name in CONTACT_NAMES[:4]:
                contact = getattr(found, name)
                if contact is not None:
                    point = contact.point
                    contact_fields(
                        row,
                        name,
                        point.jd_ut,
                        point.latitude_deg,
                        point.longitude_deg,
                        reader,
                    )
                else:
                    row[f"{name}_status"] = "not_applicable"
            row["penumbral_contacts_status"] = "available"
        except Exception as exc:
            for name in CONTACT_NAMES[:4]:
                row[f"{name}_status"] = "error"
                for suffix in ("jd_tt", "jd_ut1", "latitude_deg", "longitude_deg"):
                    row.pop(f"{name}_{suffix}", None)
            row.update(
                penumbral_contacts_status="error",
                penumbral_contacts_error=f"{type(exc).__name__}: {exc}",
            )
        if event.data.eclipse_type.is_partial:
            row["umbral_contacts_status"] = "not_applicable"
            for name in CONTACT_NAMES[4:]:
                row[f"{name}_status"] = "not_applicable"
        else:
            try:
                found = eclipse._solve_solar_umbral_contacts(calc, event.jd_ut)
                for name in CONTACT_NAMES[4:]:
                    contact = getattr(found, name)
                    if contact is not None:
                        contact_fields(
                            row,
                            name,
                            contact.epoch.jd_ut1,
                            contact.latitude_deg,
                            contact.longitude_deg,
                            reader,
                        )
                    else:
                        row[f"{name}_status"] = "not_applicable"
                row["umbral_contacts_status"] = "available"
            except Exception as exc:
                for name in CONTACT_NAMES[4:]:
                    row[f"{name}_status"] = "error"
                    for suffix in ("jd_tt", "jd_ut1", "latitude_deg", "longitude_deg"):
                        row.pop(f"{name}_{suffix}", None)
                row.update(
                    umbral_contacts_status="error",
                    umbral_contacts_error=f"{type(exc).__name__}: {exc}",
                )
    row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--index-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-year", type=int, default=-1999)
    parser.add_argument("--end-year", type=int, default=3000)
    parser.add_argument("--lunation", type=int, action="append")
    parser.add_argument("--contacts", choices=("yes", "no"), default="yes")
    parser.add_argument("--kernel-sha256", required=True)
    parser.add_argument(
        "--parent-kernel-attestation",
        type=Path,
        help="attestation from solar_shard; parent verifies full kernel before and after",
    )
    parser.add_argument(
        "--resume", action="store_true", help="resume only an exactly matching run"
    )
    args = parser.parse_args()
    if args.end_year < args.start_year:
        raise ValueError("end year precedes start year")
    if args.output.resolve() == REPO_ROOT or REPO_ROOT in args.output.resolve().parents:
        raise ValueError("bulk catalog output must be outside the source checkout")
    if args.output.resolve() in (args.index.resolve(), args.index_receipt.resolve()):
        raise ValueError("output must not overwrite an input")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    kernel = Path(find_planetary_kernel()).resolve()
    kernel_stat = kernel.stat()
    moira_dir = Path(moira.__file__).resolve().parent
    if args.parent_kernel_attestation:
        attestation = json.loads(
            args.parent_kernel_attestation.read_text(encoding="utf8")
        )
        expected_kernel = {
            "path": str(kernel),
            "size": kernel_stat.st_size,
            "mtime_ns": kernel_stat.st_mtime_ns,
            "sha256": args.kernel_sha256,
        }
        if attestation != expected_kernel:
            raise RuntimeError("parent kernel attestation does not match")
    elif sha256(kernel) != args.kernel_sha256:
        raise RuntimeError("kernel hash mismatch")
    fingerprints = source_fingerprint()
    index_receipt = json.loads(args.index_receipt.read_text(encoding="utf8"))
    if (
        index_receipt.get("status") != "provisional"
        or index_receipt.get("family") != "solar"
        or index_receipt.get("merged_sha256") != sha256(args.index)
        or index_receipt.get("kernel_sha256") != args.kernel_sha256
        or index_receipt.get("source_fingerprint_sha256") != discovery_fingerprint()
    ):
        raise RuntimeError(
            "discovery receipt does not match index, kernel, or current source"
        )
    metadata = {
        "admission": "provisional research output; incomplete stage-5 acceptance",
        "mode": "native_moira; not NASA compatibility",
        "engine_version": moira.__version__,
        "engine_package": str(moira_dir),
        **fingerprints,
        "event_index": str(args.index.resolve()),
        "event_index_sha256": sha256(args.index),
        "event_index_receipt": str(args.index_receipt.resolve()),
        "event_index_receipt_sha256": sha256(args.index_receipt),
        "kernel_path": str(kernel),
        "kernel_size_bytes": kernel_stat.st_size,
        "kernel_mtime_ns": kernel_stat.st_mtime_ns,
        "kernel_sha256": args.kernel_sha256,
        "kernel_sha256_policy": (
            "parent start/end verified"
            if args.parent_kernel_attestation
            else "runner start/end verified"
        ),
        "calendar": "Julian before 1582-10-15, Gregorian thereafter; astronomical year",
        "time_scales": "TT and UT1, neither labelled UTC",
        "width_definition": "instantaneous cone cross-track support, not NASA catalog path width",
        "gamma_definition": "signed hypot(x,y), sign of Bessel y, native greatest-eclipse epoch; x/y in Earth equatorial radii; not asserted identical to NASA gamma",
        "contact_definition": "Global physical cone tangencies with WGS84; P1/P4 and U1/U4 external, P2/P3 and U2/U3 optional internal. These are not observer contact times and do not assert daylight visibility.",
        "lunar_limb": "spherical",
        "earth": "WGS84 at zero elevation",
        "contacts": args.contacts,
        "range": [args.start_year, args.end_year],
        "lunations": args.lunation,
        "python": sys.version,
        "platform": platform.platform(),
        "limits": "Component errors retained; no claim of NASA parity. Contact absence is not zero.",
    }
    metafile = args.output.with_suffix(".metadata.json")
    if metafile.exists():
        if not args.resume:
            raise RuntimeError("output metadata exists; explicitly request resume")
        previous = json.loads(metafile.read_text(encoding="utf-8"))
        if previous != metadata:
            raise RuntimeError("existing metadata differs; choose a new output file")
    else:
        if args.output.exists():
            raise RuntimeError("existing output has no metadata; refusing to resume")
        with metafile.open("x", encoding="utf8") as stream:
            stream.write(json.dumps(metadata, indent=2))
    done = set()
    failures = []
    if args.output.exists():
        with args.output.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS:
                raise RuntimeError("existing output schema differs")
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise RuntimeError("existing output contains a truncated row")
                key = int(row["lunation_number"])
                if key in done:
                    raise RuntimeError("duplicate lunation in output")
                done.add(key)
                if has_error(row):
                    failures.append(key)
    with args.index.open(encoding="utf-8", newline="") as stream:
        all_events = list(csv.DictReader(stream))
    if len(all_events) != index_receipt.get("row_count"):
        raise RuntimeError("discovery receipt row count differs")
    if any(row.get("family") != "solar" for row in all_events):
        raise RuntimeError("discovery index contains a non-solar event")
    all_keys = [int(r["lunation_number"]) for r in all_events]
    if len(all_keys) != len(set(all_keys)):
        raise RuntimeError("discovery index has duplicate lunations")
    events = [
        r
        for r in all_events
        if args.start_year <= int(r["year_astronomical"]) <= args.end_year
        and (args.lunation is None or int(r["lunation_number"]) in args.lunation)
    ]
    keys = [int(r["lunation_number"]) for r in events]
    if len(keys) != len(set(keys)):
        raise RuntimeError("event index has duplicate lunations")
    if not done.issubset(keys):
        raise RuntimeError("existing output contains an unexpected lunation")
    with (
        SpkReader(kernel) as reader,
        args.output.open("a", encoding="utf-8", newline="") as stream,
    ):
        calc = eclipse.EclipseCalculator(reader=reader)
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        if stream.tell() == 0:
            writer.writeheader()
            stream.flush()
        for index_row in events:
            if int(index_row["lunation_number"]) in done:
                continue
            row = compute(calc, reader, index_row, contacts=args.contacts == "yes")
            writer.writerow(row)
            stream.flush()
            if has_error(row):
                failures.append(int(index_row["lunation_number"]))
            print(
                json.dumps(
                    {
                        "lunation": row["lunation_number"],
                        "date_tt": row.get("date_tt"),
                        "status": row["status"],
                        "width_status": row.get("width_status"),
                        "penumbral": row["penumbral_contacts_status"],
                        "umbral": row["umbral_contacts_status"],
                        "seconds": row["elapsed_seconds"],
                    }
                ),
                flush=True,
            )
    if (
        source_fingerprint() != fingerprints
        or sha256(args.index) != metadata["event_index_sha256"]
        or sha256(args.index_receipt) != metadata["event_index_receipt_sha256"]
        or discovery_fingerprint() != index_receipt["source_fingerprint_sha256"]
    ):
        raise RuntimeError("source or index changed during generation")
    stat_after = kernel.stat()
    if (stat_after.st_size, stat_after.st_mtime_ns) != (
        kernel_stat.st_size,
        kernel_stat.st_mtime_ns,
    ):
        raise RuntimeError("kernel changed during generation")
    if not args.parent_kernel_attestation and sha256(kernel) != args.kernel_sha256:
        raise RuntimeError("kernel hash changed during generation")
    if failures:
        raise RuntimeError(
            f"{len(failures)} solar rows have computation errors: {failures[:10]}"
        )


if __name__ == "__main__":
    main()
