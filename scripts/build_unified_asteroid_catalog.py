"""
Build the unified Moira asteroid catalog: one Type-13 shard set covering every
admitted numbered asteroid, sourced uniformly from JPL Horizons.

Supersedes the split sb441_type13 + family_expansion kernel sets. Reads target
asteroid numbers from a JSON list ([{"number": N, "family": F}, ...]), fetches
heliocentric states from Horizons over a uniform window, writes Type-13 shards
(<= 25 bodies each, matching write_spk_type13's single summary/name record cap),
verifies node round-trip, and emits per-shard + master registration metadata.

Default window: the JPL small-body (DE441-derived) integration span is uniform
across most of these bodies (~1599 to ~2501 TDB), so a 1600-2500 window is used
unless Horizons reports narrower coverage. Chaotic Icarus and Apollo solutions
are explicitly limited to the observational arcs reported by JPL SBDB because
their long extrapolations depend materially on the requested Horizons interval.

RESUMABLE: a shard whose kernel + metadata already cover their bodies is skipped.

Usage:
    python scripts/build_unified_asteroid_catalog.py TARGETS.json START COUNT [OUTDIR]

Unit law: Horizons VECTORS OUT_UNITS=KM-S -> km / km-per-s; Type-13 is
seconds-based so velocities stay km/s. Horizons epochs are JDTDB (kernel time),
queried back as jd_tt directly with center = 10 (Sun).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import sys
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._spk_body_kernel import SmallBodyKernel  # noqa: E402
from moira.asteroid_families import ASTEROID_FAMILY_CATALOG_SOURCE  # noqa: E402
from moira.daf_writer import write_spk_type13  # noqa: E402
from scripts.horizons_response_cache import cached_text_response  # noqa: E402
from scripts import type13_adaptive_sampling as adaptive  # noqa: E402

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
HORIZONS_FILE_URL = "https://ssd.jpl.nasa.gov/api/horizons_file.api"
SBDB_URL = "https://ssd-api.jpl.nasa.gov/sbdb.api"
WINDOW = ("1600-01-01", "2500-01-01")  # uniform DE441 small-body span (inside 1599..2501)
STEP_DAYS = int(adaptive.BASE_STEP_DAYS)
WINDOW_SIZE = adaptive.WINDOW_SIZE
HORIZONS_TLIST_LIMIT = 10_000
REFINEMENT_REQUEST_MAX_SPAN_DAYS = 32 * 365.25
SHARD_SIZE = 25
CENTER = 10
FRAME = 1
THROTTLE_S = 1.0
SHARD_PREFIX = "asteroid_shard"
ADAPTIVE_ROSTER_PATH = ROOT / "moira" / "data" / "asteroid_type13_adaptive_bodies.json"
RESPONSE_CACHE_DIR: Path | None = None

# These near-Earth asteroids have chaotic solutions whose long extrapolations
# depend materially on the requested Horizons interval.  Their Type-13 records
# therefore cover only the observational arc reported by JPL SBDB.  This is a
# source-owned coverage policy, not an interpolation exception.
OBSERVATION_ARC_LIMITED_BODIES = frozenset({
    1566,   # Icarus
    1862,   # Apollo
    2201,   # Oljato (Shard 088)
    4581,   # Asclepius (Shard 183)
    4660,   # Nereus (Shard 186)
    25143,  # Itokawa (Shard 399)
    54509,  # YORP (Shard 399)
    69230,  # Hermes (Shard 399)
    99942,  # Apophis (Shard 398)
    367943, # Duende (Shard 399)
})

_NAME_RE = re.compile(r"Target body name:\s*(\d+)\s+([^\(]+?)\s*[\(\{]")
_FLOOR_RE = re.compile(r"prior to A\.D\.\s*([0-9]{3,4})-([A-Za-z]{3})-([0-9]{2})")
_CEIL_RE = re.compile(r"after A\.D\.\s*([0-9]{3,4})-([A-Za-z]{3})-([0-9]{2})")
_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], start=1)}
_TRANSIENT_HTTP_CODES = frozenset({429, 500, 502, 503, 504})
_MAX_REQUEST_ATTEMPTS = 4
_MAX_RANGE_NARROWING_REQUESTS = 3


def _load_adaptive_roster() -> tuple[frozenset[int], dict[str, object]]:
    payload = json.loads(ADAPTIVE_ROSTER_PATH.read_text(encoding="utf-8"))
    numbers = tuple(int(value) for value in payload["body_numbers"])
    if len(numbers) != len(set(numbers)) or len(numbers) != int(payload["body_count"]):
        raise RuntimeError("asteroid adaptive roster has duplicate or inconsistent bodies")
    if payload.get("policy_version") != adaptive.POLICY_VERSION:
        raise RuntimeError("asteroid adaptive roster does not match sampling policy")
    audit_path = ROOT / str(payload["source_audit"])
    audit_sha256 = hashlib.sha256(audit_path.read_bytes()).hexdigest()
    if audit_sha256 != payload.get("source_audit_sha256"):
        raise RuntimeError("asteroid adaptive roster source-audit hash mismatch")
    return frozenset(numbers), payload


ADAPTIVE_BODY_NUMBERS, ADAPTIVE_ROSTER = _load_adaptive_roster()


def _sampling_policy() -> dict[str, object]:
    return {
        **adaptive.sampling_policy(
            base_step_days=STEP_DAYS,
            window_size=WINDOW_SIZE,
        ),
        "scope": "audit_failed_asteroid_segments",
        "adaptive_body_count": len(ADAPTIVE_BODY_NUMBERS),
        "adaptive_roster": ADAPTIVE_ROSTER_PATH.relative_to(ROOT).as_posix(),
        "adaptive_roster_sha256": hashlib.sha256(
            ADAPTIVE_ROSTER_PATH.read_bytes()
        ).hexdigest(),
        "horizons_tlist_limit": HORIZONS_TLIST_LIMIT,
        "reserved_integration_anchor_epochs": 2,
        "refinement_request_max_span_days": REFINEMENT_REQUEST_MAX_SPAN_DAYS,
    }


def _response_receipt(raw: str, *, query_kind: str) -> dict[str, object]:
    encoded = raw.encode("utf-8")
    return {
        "query_kind": query_kind,
        "receipt_generated_utc": datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "byte_count": len(encoded),
    }


def _read_url(url: str, *, timeout: int) -> str:
    for attempt in range(_MAX_REQUEST_ATTEMPTS):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            retryable = exc.code in _TRANSIENT_HTTP_CODES
            if not retryable or attempt + 1 == _MAX_REQUEST_ATTEMPTS:
                raise
        except urllib.error.URLError:
            if attempt + 1 == _MAX_REQUEST_ATTEMPTS:
                raise
        time.sleep(2 ** attempt)
    raise AssertionError("request retry loop exhausted")


def _fetch_raw(command: str, start: str, stop: str) -> str:
    params = {
        "format": "text", "COMMAND": command, "OBJ_DATA": "NO", "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS", "CENTER": "500@10", "REF_PLANE": "FRAME",
        "START_TIME": start, "STOP_TIME": stop,
        "STEP_SIZE": f"{STEP_DAYS * 24}h",
        "OUT_UNITS": "KM-S", "VEC_TABLE": "2", "VEC_LABELS": "YES",
        "CSV_FORMAT": "YES", "TIME_DIGITS": "FRACSEC", "TIME_TYPE": "TDB",
        "REF_SYSTEM": "ICRF", "VEC_CORR": "NONE",
    }
    url = f"{HORIZONS_URL}?{urllib.parse.urlencode(params)}"
    raw, _cached = cached_text_response(
        RESPONSE_CACHE_DIR,
        namespace="uniform-vectors",
        request_identity={
            "policy_version": adaptive.POLICY_VERSION,
            "url": url,
        },
        fetch=lambda: _read_url(url, timeout=300),
    )
    return raw


def _fetch_tlist_raw(command: str, epochs_jd: list[float]) -> str:
    if not epochs_jd:
        raise ValueError("epochs_jd must not be empty")
    if len(epochs_jd) > HORIZONS_TLIST_LIMIT:
        raise ValueError(
            f"Horizons TLIST accepts at most {HORIZONS_TLIST_LIMIT} epochs"
        )
    batch_lines = [
        "!$$SOF",
        f"COMMAND={command}",
        "OBJ_DATA='NO'",
        "MAKE_EPHEM='YES'",
        "TABLE_TYPE='VECTORS'",
        "CENTER='500@10'",
        "TLIST=",
        *(f"'{epoch:.12f}'" for epoch in epochs_jd),
        "TLIST_TYPE='JD'",
        "TIME_TYPE='TDB'",
        "OUT_UNITS='KM-S'",
        "VEC_TABLE='2'",
        "VEC_LABELS='YES'",
        "CSV_FORMAT='YES'",
        "TIME_DIGITS='FRACSEC'",
        "REF_SYSTEM='ICRF'",
        "REF_PLANE='FRAME'",
        "VEC_CORR='NONE'",
        "!$$EOF",
    ]
    batch = ("\n".join(batch_lines) + "\n").encode("ascii")
    boundary = f"----moira-{uuid.uuid4().hex}"
    multipart_header = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="format"\r\n\r\n'
        "text\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="input"; filename="query.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
    ).encode("ascii")
    body = multipart_header + batch + f"\r\n--{boundary}--\r\n".encode("ascii")
    request = urllib.request.Request(
        HORIZONS_FILE_URL,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    def fetch() -> str:
        for attempt in range(_MAX_REQUEST_ATTEMPTS):
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    return response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                if (
                    exc.code not in _TRANSIENT_HTTP_CODES
                    or attempt + 1 == _MAX_REQUEST_ATTEMPTS
                ):
                    raise
            except urllib.error.URLError:
                if attempt + 1 == _MAX_REQUEST_ATTEMPTS:
                    raise
            time.sleep(2 ** attempt)
        raise AssertionError("TLIST request retry loop exhausted")

    raw, _cached = cached_text_response(
        RESPONSE_CACHE_DIR,
        namespace="tlist-vectors",
        request_identity={
            "policy_version": adaptive.POLICY_VERSION,
            "command": command,
            "epochs_jd": [f"{epoch:.12f}" for epoch in epochs_jd],
        },
        fetch=fetch,
    )
    return raw


def _refinement_request_chunks(epochs: list[float]) -> list[list[float]]:
    return adaptive.refinement_request_chunks(
        epochs,
        max_count=HORIZONS_TLIST_LIMIT - 2,
        max_span_days=REFINEMENT_REQUEST_MAX_SPAN_DAYS,
    )


def _fetch_exact_vectors(
    command: str,
    requested_epochs: list[float],
    *,
    query_kind: str,
    coverage_anchor_epochs: tuple[float, float],
) -> tuple[list[float], list[list[float]], list[dict[str, object]]]:
    additions: list[tuple[list[float], list[list[float]]]] = []
    receipts: list[dict[str, object]] = []
    chunks = _refinement_request_chunks(requested_epochs)
    for chunk_index, requested_chunk in enumerate(chunks, start=1):
        augmented_chunk = sorted(
            {
                coverage_anchor_epochs[0],
                *requested_chunk,
                coverage_anchor_epochs[1],
            }
        )
        print(
            f"      {query_kind}: chunk {chunk_index}/{len(chunks)} "
            f"({len(requested_chunk)} epochs)",
            flush=True,
        )
        raw = _fetch_tlist_raw(command, augmented_chunk)
        epochs, states = _parse_vectors(raw)
        if len(epochs) != len(augmented_chunk) or any(
            abs(actual - expected) > 5.0e-10
            for actual, expected in zip(epochs, augmented_chunk)
        ):
            raise RuntimeError("Horizons TLIST response does not match requested epochs")
        state_by_epoch = {
            f"{epoch:.12f}": tuple(states[axis][index] for axis in range(6))
            for index, epoch in enumerate(epochs)
        }
        additions.append(
            (
                requested_chunk,
                [
                    [state_by_epoch[f"{epoch:.12f}"][axis] for epoch in requested_chunk]
                    for axis in range(6)
                ],
            )
        )
        receipt = _response_receipt(raw, query_kind=query_kind)
        receipt["requested_epoch_count"] = len(requested_chunk)
        receipt["integration_anchor_epochs_jd_tdb"] = list(
            coverage_anchor_epochs
        )
        receipts.append(receipt)
    if not additions:
        return [], [[] for _ in range(6)], receipts
    epochs, states = additions[0]
    merged_epochs, merged_states = adaptive.merge_vectors(
        epochs,
        states,
        additions[1:],
    )
    return merged_epochs, merged_states, receipts


def _fetch_observation_arc(number: int) -> dict[str, str]:
    params = {"sstr": str(number), "full-prec": "true"}
    url = f"{SBDB_URL}?{urllib.parse.urlencode(params)}"
    payload = json.loads(_read_url(url, timeout=60))

    orbit = payload.get("orbit", {})
    first_obs = orbit.get("first_obs")
    last_obs = orbit.get("last_obs")
    if not first_obs or not last_obs:
        raise RuntimeError(f"body {number}: JPL SBDB response lacks an observational arc")
    return {
        "start": str(first_obs),
        "stop": str(last_obs),
        "authority": "JPL SBDB",
        "orbit_id": str(orbit.get("orbit_id", "")),
        "solution_date": str(orbit.get("soln_date", "")),
    }


def _parse_name(raw: str, number: int) -> str:
    m = _NAME_RE.search(raw)
    return m.group(2).strip() if (m and int(m.group(1)) == number) else f"Asteroid{number}"


def _parse_vectors(raw: str) -> tuple[list[float], list[list[float]]]:
    lines = raw.splitlines()
    soe = eoe = -1
    for i, line in enumerate(lines):
        if line.strip() == "$$SOE":
            soe = i
        elif line.strip() == "$$EOE":
            eoe = i
            break
    if soe < 0 or eoe < 0:
        raise RuntimeError("no $$SOE/$$EOE")
    epochs: list[float] = []
    states: list[list[float]] = [[] for _ in range(6)]
    for line in lines[soe + 1 : eoe]:
        parts = [p.strip() for p in line.strip().split(",")]
        if len(parts) < 8:
            continue
        try:
            jd = float(parts[0])
            vals = [float(parts[k]) for k in range(2, 8)]
        except ValueError:
            continue
        epochs.append(jd)
        for axis in range(6):
            states[axis].append(vals[axis])
    if not epochs:
        raise RuntimeError("no state rows parsed")
    return epochs, states


def _clamped_window(raw: str) -> tuple[str, str] | None:
    """From a failed response, derive a valid sub-window inside WINDOW, or None."""
    fm = _FLOOR_RE.search(raw)
    cm = _CEIL_RE.search(raw)
    start, stop = WINDOW
    if fm:
        y = int(fm.group(1)) + 1  # first full year at/after the floor
        start = max(start, f"{y:04d}-01-01")
    if cm:
        y = int(cm.group(1)) - 1
        stop = min(stop, f"{y:04d}-01-01")
    if not fm and not cm:
        return None
    if stop <= start:
        return None
    return start, stop


def _fetch_body(number: int) -> dict:
    command = f"{number};"
    coverage_provenance: dict[str, str] | None = None
    if number in OBSERVATION_ARC_LIMITED_BODIES:
        coverage_provenance = _fetch_observation_arc(number)
        start = coverage_provenance["start"]
        stop = coverage_provenance["stop"]
        clamped = True
    else:
        start, stop, clamped = WINDOW[0], WINDOW[1], False

    base_receipt: dict[str, object] | None = None
    for _ in range(_MAX_RANGE_NARROWING_REQUESTS):
        raw = _fetch_raw(command, start, stop)
        try:
            base_epochs, base_states = _parse_vectors(raw)
            base_receipt = _response_receipt(raw, query_kind="base_uniform_series")
            break
        except RuntimeError as exc:
            win = _clamped_window(raw)
            next_start = max(start, win[0]) if win is not None else start
            next_stop = min(stop, win[1]) if win is not None else stop
            if (
                win is None
                or next_stop <= next_start
                or (next_start, next_stop) == (start, stop)
            ):
                head = "\n".join(raw.splitlines()[:40])
                raise RuntimeError(
                    f"body {number}: no vectors and no parseable range:\n{head}"
                ) from exc
            start, stop, clamped = next_start, next_stop, True
    else:
        head = "\n".join(raw.splitlines()[:40])
        raise RuntimeError(
            f"body {number}: Horizons range narrowing did not converge:\n{head}"
        )
    adaptive.validate_uniform_cadence(
        base_epochs,
        expected_step_days=STEP_DAYS,
    )
    if number in ADAPTIVE_BODY_NUMBERS:
        epochs, states, certificate, refinement_receipts = (
            adaptive.build_certified_adaptive_series(
                base_epochs,
                base_states,
                lambda requested, query_kind: _fetch_exact_vectors(
                    command,
                    requested,
                    query_kind=query_kind,
                    coverage_anchor_epochs=(base_epochs[0], base_epochs[-1]),
                ),
                window_size=WINDOW_SIZE,
                progress=lambda level: print(
                    "      certified level "
                    f"{level['refinement_step_days']:g}d: "
                    f"passed={level['passed']} "
                    f"extrema={level['authority_extrema_detected']}/"
                    f"{level['base_extremum_brackets']} "
                    f"radial={level['worst_witness_radial_error_km']:.6g}km "
                    f"time={level['worst_event_time_error_seconds']:.6g}s "
                    f"event_distance={level['worst_event_distance_error_km']:.6g}km "
                    f"root_failure={level['root_failure']}",
                    flush=True,
                ),
            )
        )
    else:
        epochs, states = base_epochs, base_states
        certificate = {
            "status": "base_series_retained_by_exhaustive_catalog_partition",
            "source_audit": ADAPTIVE_ROSTER["source_audit"],
            "source_audit_sha256": ADAPTIVE_ROSTER["source_audit_sha256"],
            "passed": True,
        }
        refinement_receipts = []
    assert base_receipt is not None
    result = {
        "number": number, "naif_id": 2000000 + number, "name": _parse_name(raw, number),
        "center": CENTER, "frame": FRAME, "states": states, "epochs_jd": epochs,
        "window_size": WINDOW_SIZE, "clamped": clamped, "start": start, "stop": stop,
        "sampling_policy": _sampling_policy(),
        "base_nodes": len(base_epochs),
        "adaptive_nodes": len(epochs) - len(base_epochs),
        "apsidal_sampling_certificate": certificate,
        "response_receipts": {
            "base": base_receipt,
            "adaptive_chunks": refinement_receipts,
        },
    }
    if coverage_provenance is not None:
        result["coverage_policy"] = "jpl_sbdb_observation_arc"
        result["coverage_provenance"] = coverage_provenance
    return result


def _verify(kernel: SmallBodyKernel, naif_id: int, epochs: list[float], states: list[list[float]]) -> float:
    max_err = 0.0
    for i, jd_tdb in enumerate(epochs):
        gx, gy, gz = kernel.position_tdb(CENTER, naif_id, jd_tdb)
        max_err = max(max_err, abs(gx - states[0][i]), abs(gy - states[1][i]), abs(gz - states[2][i]))
    return max_err


def _limited_record_is_current(record: dict) -> bool:
    number = int(record["number"])
    if number not in OBSERVATION_ARC_LIMITED_BODIES:
        return True
    current = _fetch_observation_arc(number)
    return (
        record.get("coverage_policy") == "jpl_sbdb_observation_arc"
        and record.get("start") == current["start"]
        and record.get("stop") == current["stop"]
        and record.get("coverage_provenance") == current
    )


def _metadata_matches_build(meta: dict, expected_numbers: set[int]) -> bool:
    """Return whether shard metadata is an exact cache hit for this build."""
    if tuple(meta.get("window", ())) != WINDOW:
        return False
    if meta.get("step_days") != STEP_DAYS or meta.get("window_size") != WINDOW_SIZE:
        return False
    if meta.get("sampling_policy") != _sampling_policy():
        return False
    if meta.get("failures"):
        return False
    record_numbers = {int(record["number"]) for record in meta.get("records", ())}
    return record_numbers == expected_numbers


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_or_link_kernel(source: Path, destination: Path) -> None:
    """Materialize a candidate kernel without mutating the admitted source."""

    if destination.exists():
        raise FileExistsError(destination)
    temporary = destination.with_name(f".{destination.name}.seed-tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        try:
            os.link(source, temporary)
        except OSError:
            shutil.copy2(source, temporary)
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _base_retention_certificate() -> dict[str, object]:
    return {
        "status": "base_series_retained_by_exhaustive_catalog_partition",
        "source_audit": ADAPTIVE_ROSTER["source_audit"],
        "source_audit_sha256": ADAPTIVE_ROSTER["source_audit_sha256"],
        "passed": True,
    }


def _seed_unaffected_catalog(
    source_dir: Path,
    outdir: Path,
    all_targets: list[dict[str, object]],
) -> dict[str, object]:
    """Seed audited unaffected shards into an isolated rebuild candidate."""

    if source_dir.resolve() == outdir.resolve():
        raise ValueError("--seed-from must differ from OUTDIR")
    manifest_path = source_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("body_count") != len(all_targets):
        raise RuntimeError("seed manifest body count does not match target catalog")
    shard_map = {
        int(entry["index"]): entry
        for entry in manifest.get("shards", ())
    }
    expected_shard_count = (len(all_targets) + SHARD_SIZE - 1) // SHARD_SIZE
    if set(shard_map) != set(range(expected_shard_count)):
        raise RuntimeError("seed manifest does not contain the complete shard index set")

    affected_shards = {int(value) for value in ADAPTIVE_ROSTER["shard_indices"]}
    policy = _sampling_policy()
    source_manifest_sha256 = _sha256_file(manifest_path)
    seeded = 0
    resumed = 0
    for shard_index in range(expected_shard_count):
        if shard_index in affected_shards:
            continue
        target_slice = all_targets[
            shard_index * SHARD_SIZE : (shard_index + 1) * SHARD_SIZE
        ]
        expected_numbers = {int(target["number"]) for target in target_slice}
        expected_naif_ids = {2_000_000 + number for number in expected_numbers}
        entry = shard_map[shard_index]
        if set(int(value) for value in entry.get("bodies", ())) != expected_naif_ids:
            raise RuntimeError(f"seed shard {shard_index:03d} membership mismatch")

        source_kernel = source_dir / str(entry["path"])
        metadata_entry = entry.get("metadata")
        if not isinstance(metadata_entry, dict) or "path" not in metadata_entry:
            raise RuntimeError(f"seed shard {shard_index:03d} lacks metadata receipt")
        source_metadata = source_dir / str(metadata_entry["path"])
        if _sha256_file(source_kernel) != entry.get("sha256"):
            raise RuntimeError(f"seed shard {shard_index:03d} kernel hash mismatch")
        if _sha256_file(source_metadata) != metadata_entry.get("sha256"):
            raise RuntimeError(f"seed shard {shard_index:03d} metadata hash mismatch")
        source_meta = json.loads(source_metadata.read_text(encoding="utf-8"))
        if {int(record["number"]) for record in source_meta.get("records", ())} != (
            expected_numbers
        ):
            raise RuntimeError(f"seed shard {shard_index:03d} metadata membership mismatch")
        if source_meta.get("failures"):
            raise RuntimeError(f"seed shard {shard_index:03d} contains failures")

        destination_kernel = outdir / source_kernel.name
        destination_metadata = outdir / source_metadata.name
        if destination_kernel.exists() or destination_metadata.exists():
            if not (destination_kernel.exists() and destination_metadata.exists()):
                raise RuntimeError(
                    f"candidate shard {shard_index:03d} is only partially present"
                )
            existing = json.loads(destination_metadata.read_text(encoding="utf-8"))
            if not _metadata_matches_build(existing, expected_numbers):
                raise RuntimeError(
                    f"candidate shard {shard_index:03d} conflicts with seed policy"
                )
            resumed += 1
            continue

        _copy_or_link_kernel(source_kernel, destination_kernel)
        records: list[dict[str, object]] = []
        for source_record in source_meta["records"]:
            record = dict(source_record)
            record.update(
                {
                    "sampling_policy": policy,
                    "base_nodes": int(record["nodes"]),
                    "adaptive_nodes": 0,
                    "apsidal_sampling_certificate": _base_retention_certificate(),
                }
            )
            records.append(record)
        migrated = {
            **source_meta,
            "sampling_policy": policy,
            "records": records,
            "seed_provenance": {
                "mode": "audited_unaffected_shard_retention",
                "source_manifest": str(manifest_path),
                "source_manifest_sha256": source_manifest_sha256,
                "source_kernel_sha256": entry["sha256"],
                "source_metadata_sha256": metadata_entry["sha256"],
            },
        }
        destination_metadata.write_text(
            json.dumps(migrated, indent=2) + "\n",
            encoding="utf-8",
        )
        seeded += 1

    return {
        "source_manifest": str(manifest_path),
        "source_manifest_sha256": source_manifest_sha256,
        "affected_shards_excluded": len(affected_shards),
        "unaffected_shards_seeded": seeded,
        "unaffected_shards_resumed": resumed,
    }


def _shard_cached(
    kpath: Path,
    mpath: Path,
    *,
    expected_numbers: set[int],
) -> dict | None:
    if not (kpath.exists() and mpath.exists()):
        return None
    try:
        meta = json.loads(mpath.read_text())
        if not _metadata_matches_build(meta, expected_numbers):
            return None
        if not all(_limited_record_is_current(record) for record in meta["records"]):
            return None
        want = {r["naif_id"] for r in meta["records"]}
        if not want:
            return None
        k = SmallBodyKernel(kpath)
        try:
            have = set(int(x) for x in k.covered_bodies())
        finally:
            k.close()
        return meta if want == have else None
    except Exception:  # noqa: BLE001
        return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", type=Path)
    parser.add_argument("start", type=int)
    parser.add_argument("count", type=int)
    parser.add_argument(
        "outdir",
        nargs="?",
        type=Path,
        default=ROOT / "moira" / "kernels" / "asteroids",
    )
    parser.add_argument("--step-days", type=int, default=STEP_DAYS)
    parser.add_argument("--window-size", type=int, default=WINDOW_SIZE)
    parser.add_argument("--throttle-seconds", type=float, default=THROTTLE_S)
    parser.add_argument(
        "--seed-from",
        type=Path,
        help=(
            "admitted full-catalog directory whose audited unaffected shards "
            "should seed an isolated full rebuild candidate"
        ),
    )
    parser.add_argument(
        "--max-runtime-hours",
        type=float,
        help=(
            "stop cleanly after this many hours; the current shard is always "
            "written and verified before stopping"
        ),
    )
    args = parser.parse_args()
    if args.start < 0:
        parser.error("START must be non-negative")
    if args.count < 1:
        parser.error("COUNT must be positive")
    if args.step_days < 1:
        parser.error("--step-days must be positive")
    if args.window_size < 2:
        parser.error("--window-size must be at least 2")
    if args.throttle_seconds < 0:
        parser.error("--throttle-seconds must be non-negative")
    if args.max_runtime_hours is not None and args.max_runtime_hours <= 0:
        parser.error("--max-runtime-hours must be positive")
    return args


def main() -> None:
    global STEP_DAYS, WINDOW_SIZE, THROTTLE_S, RESPONSE_CACHE_DIR

    args = _parse_args()
    STEP_DAYS = args.step_days
    WINDOW_SIZE = args.window_size
    THROTTLE_S = args.throttle_seconds

    targets_path = args.targets
    start_idx = args.start
    count = args.count
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    RESPONSE_CACHE_DIR = outdir / ".horizons-cache" / adaptive.POLICY_VERSION
    run_started = time.perf_counter()
    runtime_limit_s = (
        args.max_runtime_hours * 60.0 * 60.0
        if args.max_runtime_hours is not None
        else None
    )

    all_targets = json.loads(targets_path.read_text())
    all_numbers = [int(target["number"]) for target in all_targets]
    if len(all_numbers) != len(set(all_numbers)):
        raise ValueError(f"{targets_path} contains duplicate asteroid numbers")
    slice_targets = all_targets[start_idx : start_idx + count]
    if len(slice_targets) != count:
        raise ValueError(
            f"requested {count} targets from index {start_idx}, "
            f"but only {len(slice_targets)} are available"
        )
    seed_receipt: dict[str, object] | None = None
    if args.seed_from is not None:
        if start_idx != 0 or count != len(all_targets):
            raise ValueError("--seed-from requires a complete START=0 catalog run")
        seed_receipt = _seed_unaffected_catalog(args.seed_from, outdir, all_targets)
    shards: dict[int, list] = {}
    for local, t in enumerate(slice_targets):
        shards.setdefault((start_idx + local) // SHARD_SIZE, []).append(t)

    m_records: list[dict] = []
    m_naif: dict[str, int] = {}
    m_failures: list[dict] = []
    completed_shards = 0
    stopped_at_time_limit = False

    for sidx in sorted(shards):
        kpath = outdir / f"{SHARD_PREFIX}_{sidx:03d}.bsp"
        mpath = outdir / f"{SHARD_PREFIX}_{sidx:03d}.metadata.json"
        expected_numbers = {int(target["number"]) for target in shards[sidx]}
        cached = _shard_cached(kpath, mpath, expected_numbers=expected_numbers)
        if cached is not None:
            m_records.extend(cached["records"])
            m_naif.update(cached["naif_map"])
            m_failures.extend(cached.get("failures", []))
            completed_shards += 1
            print(f"=== shard {sidx:03d}: SKIP (cached, {len(cached['records'])}) ===", flush=True)
            continue

        print(f"=== shard {sidx:03d}: building {len(shards[sidx])} ===", flush=True)
        bodies: list[dict] = []
        records: list[dict] = []
        failures: list[dict] = []
        for t in shards[sidx]:
            num = int(t["number"])
            t0 = time.perf_counter()
            try:
                b = _fetch_body(num)
            except Exception as e:  # noqa: BLE001
                failures.append({
                    "number": num,
                    "family": t.get("family"),
                    "families": t.get("families", []),
                    "error": str(e)[:200],
                })
                print(f"  [SKIP] {num} ({t.get('family')}): {str(e)[:70]}", flush=True)
                continue
            dt = time.perf_counter() - t0
            bodies.append(b)
            records.append({
                "number": num, "naif_id": b["naif_id"], "name": b["name"],
                "family": t.get("family"), "families": t.get("families", []),
                "nodes": len(b["epochs_jd"]), "clamped": b["clamped"],
                "start": b["start"], "stop": b["stop"], "fetch_s": round(dt, 1),
                "sampling_policy": b["sampling_policy"],
                "base_nodes": b["base_nodes"],
                "adaptive_nodes": b["adaptive_nodes"],
                "apsidal_sampling_certificate": b["apsidal_sampling_certificate"],
                "response_receipts": b["response_receipts"],
                **({"coverage_policy": b["coverage_policy"],
                    "coverage_provenance": b["coverage_provenance"]}
                   if "coverage_policy" in b else {}),
            })
            tag = f"CLAMP {b['start'][:4]}-{b['stop'][:4]}" if b["clamped"] else "full"
            print(f"  [OK] {num:>7} {b['name']:<18} nodes={len(b['epochs_jd']):>6} {tag:>13} {dt:4.1f}s", flush=True)
            time.sleep(THROTTLE_S)

        if not bodies:
            m_failures.extend(failures)
            continue

        writable = [{k: b[k] for k in ("naif_id", "name", "center", "frame", "states", "epochs_jd", "window_size")} for b in bodies]
        write_spk_type13(kpath, bodies=writable, locifn="MOIRA UNIFIED ASTEROID CATALOG")
        kernel = SmallBodyKernel(kpath)
        try:
            for b, rec in zip(bodies, records):
                rec["max_node_error_km"] = _verify(kernel, b["naif_id"], b["epochs_jd"], b["states"])
        finally:
            kernel.close()

        shard_meta = {
            "shard": sidx, "kernel": kpath.name, "kernel_bytes": kpath.stat().st_size,
            "window": WINDOW, "step_days": STEP_DAYS, "window_size": WINDOW_SIZE,
            "sampling_policy": _sampling_policy(),
            "family_catalog_source": ASTEROID_FAMILY_CATALOG_SOURCE,
            "records": records, "failures": failures,
            "naif_map": {r["name"]: r["naif_id"] for r in records},
        }
        mpath.write_text(json.dumps(shard_meta, indent=2))
        m_records.extend(records)
        m_naif.update(shard_meta["naif_map"])
        m_failures.extend(failures)
        completed_shards += 1
        worst = max((r["max_node_error_km"] for r in records), default=0.0)
        print(f"  shard {sidx:03d} -> {kpath.name} ({kpath.stat().st_size/1024:.0f} KB), "
              f"{len(records)} bodies, worst {worst:.2e} km, {len(failures)} failed", flush=True)
        if (
            runtime_limit_s is not None
            and time.perf_counter() - run_started >= runtime_limit_s
        ):
            stopped_at_time_limit = True
            print(
                f"TIME LIMIT: stopped cleanly after shard {sidx:03d}; "
                "restart with the same command to resume",
                flush=True,
            )
            break

    master = {
        "requested": len(slice_targets), "built": len(m_records), "failed": len(m_failures),
        "window": WINDOW, "step_days": STEP_DAYS, "window_size": WINDOW_SIZE,
        "sampling_policy": _sampling_policy(),
        "family_catalog_source": ASTEROID_FAMILY_CATALOG_SOURCE,
        "completed_shards": completed_shards,
        "planned_shards": len(shards),
        "stopped_at_time_limit": stopped_at_time_limit,
        "seed_receipt": seed_receipt,
        "naif_map": m_naif, "records": m_records, "failures": m_failures,
    }
    (outdir / "unified_master.json").write_text(json.dumps(master, indent=2))
    _write_manifest(outdir, records=m_records)
    state = "PAUSED" if stopped_at_time_limit else "DONE"
    print(
        f"\n{state}: {len(m_records)} built, {len(m_failures)} failed, "
        f"{completed_shards}/{len(shards)} shards processed",
        flush=True,
    )
    if m_failures:
        raise SystemExit(1)


def _write_manifest(outdir: Path, *, records: list[dict]) -> None:
    """Emit the loader manifest for the shards built by this invocation."""
    existing_manifest: dict = {}
    existing_manifest_path = outdir / "manifest.json"
    if existing_manifest_path.exists():
        try:
            existing_manifest = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
        except Exception:
            existing_manifest = {}

    shard_entries: list[dict] = []
    for mpath in sorted(outdir.glob(f"{SHARD_PREFIX}_*.metadata.json")):
        meta = json.loads(mpath.read_text(encoding="utf-8"))
        if not _metadata_matches_build(
            meta,
            {int(record["number"]) for record in meta.get("records", ())},
        ):
            continue
        kpath = outdir / meta["kernel"]
        if not kpath.exists():
            continue
        bodies = [record["naif_id"] for record in meta["records"]]
        s_entry: dict[str, Any] = {
            "index": meta["shard"],
            "path": meta["kernel"],
            "body_count": len(bodies),
            "bodies": bodies,
        }
        s_entry["bytes"] = kpath.stat().st_size
        s_entry["sha256"] = _sha256_file(kpath)
        s_entry["metadata"] = {
            "path": mpath.name,
            "bytes": mpath.stat().st_size,
            "sha256": _sha256_file(mpath),
        }
        shard_entries.append(s_entry)

    coverage_records: list[dict] = list(records)
    for mpath in sorted(outdir.glob(f"{SHARD_PREFIX}_*.metadata.json")):
        meta = json.loads(mpath.read_text(encoding="utf-8"))
        coverage_records.extend(meta.get("records", ()))

    coverage_exceptions: list[dict] = []
    seen_exception_ids: set[int] = set()
    for record in coverage_records:
        naif_id = record.get("naif_id")
        if naif_id in seen_exception_ids:
            continue
        if "coverage_policy" in record:
            provenance = record["coverage_provenance"]
            exception = {
                "naif_id": record["naif_id"],
                "name": record["name"],
                "start_date": record["start"],
                "end_date": record["stop"],
                "policy": record["coverage_policy"],
                "authority": provenance["authority"],
                "orbit_id": provenance["orbit_id"],
                "solution_date": provenance["solution_date"],
            }
        elif record.get("clamped"):
            exception = {
                "naif_id": record["naif_id"],
                "name": record["name"],
                "start_date": record["start"],
                "end_date": record["stop"],
                "policy": "jpl_horizons_ephemeris_availability",
                "authority": "JPL Horizons API",
                "note": (
                    "conservative full-year bounds parsed from the Horizons "
                    "ephemeris-availability response"
                ),
            }
        else:
            continue
        seen_exception_ids.add(naif_id)
        coverage_exceptions.append(exception)

    shard_entries.sort(key=lambda shard: shard["index"])
    coverage_exceptions.sort(key=lambda exc: exc["naif_id"])

    manifest = {
        "manifest_schema": "moira.small-body-catalog/v1",
        "catalog_id": existing_manifest.get("catalog_id", "moira-asteroids"),
        "source": "MOIRA UNIFIED ASTEROID CATALOG (JPL Horizons)",
        "provenance": {
            "artifact_author": "Moira",
            "artifact_format": "DAF/SPK Type 13",
            "trajectory_source": "JPL Horizons VECTORS",
            "horizons_api": HORIZONS_URL,
            "horizons_file_api": HORIZONS_FILE_URL,
            "center": "Sun (500@10)",
            "reference_plane": "FRAME",
            "units": "km and km/s",
            "timescale": "JDTDB",
        },
        "coverage": {
            "start_date": WINDOW[0],
            "end_date": WINDOW[1],
            "note": "default DE441 small-body span; see coverage_exceptions",
        },
        "coverage_exceptions": coverage_exceptions,
        "sampling": _sampling_policy(),
        "body_count": sum(shard["body_count"] for shard in shard_entries),
        "shard_count": len(shard_entries),
        "shards": shard_entries,
    }
    if "catalog_version" in existing_manifest:
        manifest["catalog_version"] = existing_manifest["catalog_version"]
    if "release" in existing_manifest:
        manifest["release"] = existing_manifest["release"]

    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
