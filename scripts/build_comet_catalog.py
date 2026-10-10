"""
Build the Moira numbered-periodic-comet catalog: one Type-13 shard set covering
every numbered periodic comet (1P..NP), sourced from JPL Horizons.

Reads targets from a JSON list ([{"number": N, "full_name": "1P/Halley"}, ...]),
fetches heliocentric states from Horizons via the periodic-comet designation
directive (DES=NP;NOFRAG;CAP -- one non-fragment apparition solution), adds
certified adaptive Type-13 nodes around every base-grid radial-distance extremum, writes
Type-13 shards (<= 25 bodies each), verifies node round-trip, and emits per-shard
+ master registration metadata. NAIF id = 1000000 + comet number.

ACCURACY NOTE (recorded in the manifest, surfaced in docs): comet orbits are
perturbed by non-gravitational outgassing forces, so positions are only reliable
NEAR observed apparitions and degrade far from them. Horizons returns the full
1600-2500 span for numbered comets, but fidelity is apparition-dependent, unlike
the uniform asteroid case. This is delivered honestly, not hidden.

RESUMABLE: a shard whose kernel + metadata already cover their bodies under the
same sampling-policy version is skipped.
Per-comet window: 1600-2500 requested; a comet whose Horizons coverage is
narrower is clamped to its stated valid range.

Usage:
    python scripts/build_comet_catalog.py TARGETS.json START COUNT [OUTDIR]
        [--response-cache-dir PATH]

Unit law: Horizons VECTORS OUT_UNITS=KM-S; Type-13 is seconds-based so velocities
stay km/s. Horizons epochs are JDTDB (kernel time), queried back as jd_tt with
center = 10 (Sun).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._spk_body_kernel import SmallBodyKernel  # noqa: E402
from moira.daf_writer import write_spk_type13  # noqa: E402
from scripts.horizons_response_cache import cached_text_response  # noqa: E402
from scripts import type13_adaptive_sampling as adaptive  # noqa: E402

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
HORIZONS_FILE_URL = "https://ssd.jpl.nasa.gov/api/horizons_file.api"
WINDOW = ("1600-01-01", "2500-01-01")
STEP_DAYS = int(adaptive.BASE_STEP_DAYS)
WINDOW_SIZE = adaptive.WINDOW_SIZE
REFINEMENT_STEP_DAYS = adaptive.INITIAL_REFINEMENT_STEP_DAYS
REFINEMENT_PADDING_DAYS = adaptive.REFINEMENT_PADDING_DAYS
HORIZONS_TLIST_LIMIT = 10_000
REFINEMENT_REQUEST_MAX_SPAN_DAYS = 32 * 365.25
SAMPLING_POLICY_VERSION = "moira-comet-type13-apsidal-adaptive-v5"
MIN_REFINEMENT_STEP_DAYS = 1.0 / 128.0
# Exact-request construction is unchanged from shared v4. Keep this namespace
# stable so a v5 certification rebuild can reuse the audited Horizons replies.
HORIZONS_REQUEST_CACHE_VERSION = "moira-small-body-type13-apsidal-adaptive-v4"
SHARD_SIZE = 25
CENTER = 10
FRAME = 1
THROTTLE_S = 1.0
SHARD_PREFIX = "comet_shard"
RESPONSE_CACHE_DIR: Path | None = None
_TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}
_MAX_REQUEST_ATTEMPTS = 4

_NAME_RE = re.compile(r"Target body name:\s*([^\{]+?)\s*\{")
_SOLUTION_RE = re.compile(r"Target body name:.*?\{source:\s*([^}]+)\}")
_FLOOR_RE = re.compile(r"prior to A\.D\.\s*([0-9]{3,4})-([A-Za-z]{3})-([0-9]{2})")
_CEIL_RE = re.compile(r"after A\.D\.\s*([0-9]{3,4})-([A-Za-z]{3})-([0-9]{2})")


def _sampling_policy() -> dict[str, object]:
    """Return the frozen Type-13 sampling policy for release metadata."""

    return {
        **adaptive.sampling_policy(
            base_step_days=STEP_DAYS,
            window_size=WINDOW_SIZE,
            policy_version=SAMPLING_POLICY_VERSION,
            minimum_refinement_step_days=MIN_REFINEMENT_STEP_DAYS,
        ),
        "horizons_tlist_limit": HORIZONS_TLIST_LIMIT,
        "reserved_integration_anchor_epochs": 2,
        "refinement_request_max_span_days": REFINEMENT_REQUEST_MAX_SPAN_DAYS,
    }


def _catalog_provenance() -> dict[str, object]:
    """Return the explicit authority and query policy for this catalog."""
    return {
        "artifact_author": "Moira",
        "artifact_format": "DAF/SPK Type 13",
        "trajectory_authority": "NASA/JPL Horizons",
        "trajectory_source": "JPL Horizons VECTORS",
        "horizons_api": HORIZONS_URL,
        "horizons_file_api": HORIZONS_FILE_URL,
        "query_policy": {
            "command_template": "DES={number}P;NOFRAG;CAP",
            "object_data": False,
            "ephemeris_type": "VECTORS",
            "center": "500@10",
            "reference_plane": "FRAME",
            "output_units": "KM-S",
            "vector_table": 2,
            "csv_format": True,
            "time_digits": "FRACSEC",
            "timescale": "JDTDB",
            "sampling": _sampling_policy(),
        },
        "identity_source": (
            "Horizons target body name returned for each numbered "
            "periodic-comet query"
        ),
        "naif_convention": "1000000_plus_periodic_comet_number",
        "center": "Sun (500@10)",
        "reference_plane": "FRAME",
        "units": "km and km/s",
        "timescale": "JDTDB",
        "capture_limits": {
            "raw_horizons_responses_retained": False,
            "per_query_retrieval_timestamps_retained": False,
            "per_query_receipt_timestamps_retained": True,
            "per_query_response_hashes_retained": True,
            "statement": (
                "The build retains parsed state vectors plus receipt-generation "
                "timestamps and SHA-256 response hashes, not raw Horizons response "
                "bodies or authoritative retrieval timestamps."
            ),
        },
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


def _read_request(request: str | urllib.request.Request, *, timeout: int) -> str:
    for attempt in range(_MAX_REQUEST_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
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
    raise AssertionError("Horizons request retry loop exhausted")


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
            "policy_version": HORIZONS_REQUEST_CACHE_VERSION,
            "url": url,
        },
        fetch=lambda: _read_request(url, timeout=300),
    )
    return raw


def _fetch_tlist_raw(command: str, epochs_jd: list[float]) -> str:
    """Fetch exact irregular JDTDB states through the Horizons File API."""

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

    raw, _cached = cached_text_response(
        RESPONSE_CACHE_DIR,
        namespace="tlist-vectors",
        request_identity={
            "policy_version": HORIZONS_REQUEST_CACHE_VERSION,
            "command": command,
            "epochs_jd": [f"{epoch:.12f}" for epoch in epochs_jd],
        },
        fetch=lambda: _read_request(request, timeout=300),
    )
    return raw


def _parse_name(raw: str, number: int) -> str:
    m = _NAME_RE.search(raw)
    return m.group(1).strip() if m else f"{number}P"


def _parse_solution(raw: str) -> str | None:
    match = _SOLUTION_RE.search(raw)
    return None if match is None else match.group(1).strip()


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


def _extremum_refinement_epochs(
    epochs: list[float],
    states: list[list[float]],
) -> tuple[list[float], int]:
    """Return daily epochs around every base-grid radial-velocity crossing."""

    intervals, bracket_count = adaptive.extremum_refinement_intervals(
        epochs,
        states,
    )
    return (
        adaptive.epochs_for_intervals(
            intervals,
            step_days=REFINEMENT_STEP_DAYS,
        ),
        bracket_count,
    )


def _merge_vectors(
    base_epochs: list[float],
    base_states: list[list[float]],
    additions: list[tuple[list[float], list[list[float]]]],
) -> tuple[list[float], list[list[float]]]:
    """Merge base and exact refinement states into increasing Type-13 nodes."""

    return adaptive.merge_vectors(base_epochs, base_states, additions)


def _fetch_refinement_vectors(
    command: str,
    requested_epochs: list[float],
    *,
    query_kind: str = "extremum_refinement_tlist",
    coverage_anchor_epochs: tuple[float, float],
    expected_target_solution: str,
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
        actual_target_solution = _parse_solution(raw)
        if actual_target_solution != expected_target_solution:
            raise RuntimeError(
                "Horizons target solution changed within one comet build: "
                f"expected {expected_target_solution!r}, got "
                f"{actual_target_solution!r}"
            )
        epochs, states = _parse_vectors(raw)
        if len(epochs) != len(augmented_chunk):
            raise RuntimeError(
                "Horizons refinement response row count does not match TLIST request"
            )
        if any(
            abs(actual - expected) > 5.0e-10
            for actual, expected in zip(epochs, augmented_chunk)
        ):
            raise RuntimeError(
                "Horizons refinement response epochs do not match TLIST request"
            )
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
    return (*_merge_vectors(epochs, states, additions[1:]), receipts)


def _refinement_request_chunks(epochs: list[float]) -> list[list[float]]:
    """Bound TLIST count and span so Horizons does not integrate for centuries."""

    return adaptive.refinement_request_chunks(
        epochs,
        max_count=HORIZONS_TLIST_LIMIT - 2,
        max_span_days=REFINEMENT_REQUEST_MAX_SPAN_DAYS,
    )


def _clamped_window(raw: str) -> tuple[str, str] | None:
    fm = _FLOOR_RE.search(raw)
    cm = _CEIL_RE.search(raw)
    start, stop = WINDOW
    if fm:
        start = max(start, f"{int(fm.group(1)) + 1:04d}-01-01")
    if cm:
        stop = min(stop, f"{int(cm.group(1)) - 1:04d}-01-01")
    if not fm and not cm:
        return None
    if stop <= start:
        return None
    return start, stop


def _fetch_comet(number: int) -> dict:
    command = f"'DES={number}P;NOFRAG;CAP'"
    raw = _fetch_raw(command, WINDOW[0], WINDOW[1])
    base_receipt = _response_receipt(raw, query_kind="base_uniform_series")
    start, stop, clamped = WINDOW[0], WINDOW[1], False
    try:
        base_epochs, base_states = _parse_vectors(raw)
    except RuntimeError:
        win = _clamped_window(raw)
        if win is None:
            head = "\n".join(raw.splitlines()[:40])
            raise RuntimeError(f"comet {number}P: no vectors and no parseable range:\n{head}")
        start, stop, clamped = win[0], win[1], True
        raw = _fetch_raw(command, start, stop)
        base_receipt = _response_receipt(raw, query_kind="clamped_base_uniform_series")
        base_epochs, base_states = _parse_vectors(raw)
    adaptive.validate_uniform_cadence(
        base_epochs,
        expected_step_days=STEP_DAYS,
    )
    target_solution = _parse_solution(raw)
    if target_solution is None:
        raise RuntimeError(f"comet {number}P: Horizons did not declare a target solution")
    epochs, states, certificate, refinement_receipts = (
        adaptive.build_certified_adaptive_series(
            base_epochs,
            base_states,
            lambda requested, query_kind: _fetch_refinement_vectors(
                command,
                requested,
                query_kind=query_kind,
                coverage_anchor_epochs=(base_epochs[0], base_epochs[-1]),
                expected_target_solution=target_solution,
            ),
            window_size=WINDOW_SIZE,
            minimum_refinement_step_days=MIN_REFINEMENT_STEP_DAYS,
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
    _initial_refinement_epochs, extremum_brackets = _extremum_refinement_epochs(
        base_epochs,
        base_states,
    )
    return {
        "number": number, "naif_id": 1000000 + number, "name": _parse_name(raw, number),
        "center": CENTER, "frame": FRAME, "states": states, "epochs_jd": epochs,
        "window_size": WINDOW_SIZE, "clamped": clamped, "start": start, "stop": stop,
        "target_solution": target_solution,
        "sampling_policy": _sampling_policy(),
        "base_nodes": len(base_epochs),
        "adaptive_nodes": len(epochs) - len(base_epochs),
        "extremum_brackets": extremum_brackets,
        "apsidal_sampling_certificate": certificate,
        "response_receipts": {
            "base": base_receipt,
            "adaptive_chunks": refinement_receipts,
        },
    }


def _verify(kernel: SmallBodyKernel, naif_id: int, epochs: list[float], states: list[list[float]]) -> float:
    max_err = 0.0
    for i, jd_tdb in enumerate(epochs):
        gx, gy, gz = kernel.position_tdb(CENTER, naif_id, jd_tdb)
        max_err = max(max_err, abs(gx - states[0][i]), abs(gy - states[1][i]), abs(gz - states[2][i]))
    return max_err


def _shard_cached(
    kpath: Path,
    mpath: Path,
    *,
    expected_naif_ids: set[int] | None = None,
) -> dict | None:
    if not (kpath.exists() and mpath.exists()):
        return None
    try:
        meta = json.loads(mpath.read_text())
        if meta.get("sampling_policy") != _sampling_policy():
            return None
        want = {r["naif_id"] for r in meta["records"]}
        if not want:
            return None
        if meta.get("failures"):
            return None
        if expected_naif_ids is not None and want != expected_naif_ids:
            return None
        k = SmallBodyKernel(kpath)
        try:
            have = set(int(x) for x in k.covered_bodies())
        finally:
            k.close()
        return meta if want == have else None
    except Exception:  # noqa: BLE001
        return None


def _load_targets(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        targets = payload
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        targets = [
            {
                "number": record["number"],
                "full_name": record.get("full_name", record.get("name")),
            }
            for record in payload["records"]
        ]
    else:
        raise ValueError("comet targets must be a list or a master record object")
    numbers = [int(target["number"]) for target in targets]
    if len(numbers) != len(set(numbers)):
        raise ValueError("comet targets contain duplicate numbers")
    return targets


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", type=Path)
    parser.add_argument("start", type=int)
    parser.add_argument("count", type=int)
    parser.add_argument(
        "outdir",
        nargs="?",
        type=Path,
        default=ROOT / "moira" / "kernels" / "comets",
    )
    parser.add_argument(
        "--response-cache-dir",
        type=Path,
        help=(
            "exact Horizons response-cache directory to reuse; defaults to "
            "OUTDIR/.horizons-cache/<request-policy-version>"
        ),
    )
    args = parser.parse_args(argv)
    if args.start < 0:
        parser.error("START must be non-negative")
    if args.count < 1:
        parser.error("COUNT must be positive")
    return args


def main() -> None:
    global RESPONSE_CACHE_DIR

    args = _parse_args()
    targets_path = args.targets
    start_idx = args.start
    count = args.count
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    RESPONSE_CACHE_DIR = args.response_cache_dir or (
        outdir / ".horizons-cache" / HORIZONS_REQUEST_CACHE_VERSION
    )

    all_targets = _load_targets(targets_path)
    slice_targets = all_targets[start_idx : start_idx + count]
    if len(slice_targets) != count:
        raise ValueError(
            f"requested {count} targets from index {start_idx}, "
            f"but only {len(slice_targets)} are available"
        )
    shards: dict[int, list] = {}
    for local, t in enumerate(slice_targets):
        shards.setdefault((start_idx + local) // SHARD_SIZE, []).append(t)

    m_records: list[dict] = []
    m_naif: dict[str, int] = {}
    m_failures: list[dict] = []

    for sidx in sorted(shards):
        kpath = outdir / f"{SHARD_PREFIX}_{sidx:03d}.bsp"
        mpath = outdir / f"{SHARD_PREFIX}_{sidx:03d}.metadata.json"
        expected_naif_ids = {
            1_000_000 + int(target["number"])
            for target in shards[sidx]
        }
        cached = _shard_cached(
            kpath,
            mpath,
            expected_naif_ids=expected_naif_ids,
        )
        if cached is not None:
            m_records.extend(cached["records"])
            m_naif.update(cached["naif_map"])
            m_failures.extend(cached.get("failures", []))
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
                b = _fetch_comet(num)
            except Exception as e:  # noqa: BLE001
                failures.append({"number": num, "full_name": t.get("full_name"), "error": str(e)[:200]})
                print(f"  [SKIP] {num}P ({t.get('full_name')}): {str(e)[:60]}", flush=True)
                continue
            dt = time.perf_counter() - t0
            bodies.append(b)
            records.append({
                "number": num, "naif_id": b["naif_id"], "name": b["name"], "full_name": t.get("full_name"),
                "nodes": len(b["epochs_jd"]), "clamped": b["clamped"],
                "start": b["start"], "stop": b["stop"], "fetch_s": round(dt, 1),
                "target_solution": b["target_solution"],
                "sampling_policy": b["sampling_policy"],
                "base_nodes": b["base_nodes"],
                "adaptive_nodes": b["adaptive_nodes"],
                "extremum_brackets": b["extremum_brackets"],
                "apsidal_sampling_certificate": b["apsidal_sampling_certificate"],
                "response_receipts": b["response_receipts"],
            })
            tag = f"CLAMP {b['start'][:4]}-{b['stop'][:4]}" if b["clamped"] else "full"
            print(f"  [OK] {num:>4}P {b['name']:<26} nodes={len(b['epochs_jd']):>6} {tag:>13} {dt:4.1f}s", flush=True)
            time.sleep(THROTTLE_S)

        if not bodies:
            m_failures.extend(failures)
            continue

        writable = [{k: b[k] for k in ("naif_id", "name", "center", "frame", "states", "epochs_jd", "window_size")} for b in bodies]
        write_spk_type13(kpath, bodies=writable, locifn="MOIRA COMET CATALOG")
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
            "records": records, "failures": failures,
            "naif_map": {r["name"]: r["naif_id"] for r in records},
        }
        mpath.write_text(json.dumps(shard_meta, indent=2))
        m_records.extend(records)
        m_naif.update(shard_meta["naif_map"])
        m_failures.extend(failures)
        worst = max((r["max_node_error_km"] for r in records), default=0.0)
        print(f"  shard {sidx:03d} -> {kpath.name} ({kpath.stat().st_size/1024:.0f} KB), "
              f"{len(records)} comets, worst {worst:.2e} km, {len(failures)} failed", flush=True)

    master = {
        "requested": len(slice_targets), "built": len(m_records), "failed": len(m_failures),
        "window": WINDOW, "step_days": STEP_DAYS, "window_size": WINDOW_SIZE,
        "sampling_policy": _sampling_policy(),
        "accuracy_note": (
            "Comet positions are apparition-dependent due to non-gravitational "
            "outgassing forces; fidelity degrades far from observed apparitions."
        ),
        "naif_map": m_naif, "records": m_records, "failures": m_failures,
    }
    (outdir / "comet_master.json").write_text(json.dumps(master, indent=2))
    _write_manifest(outdir)
    print(f"\nDONE: {len(m_records)} built, {len(m_failures)} failed, {len(shards)} shards", flush=True)
    if m_failures:
        raise SystemExit(1)


def _write_manifest(outdir: Path) -> None:
    """Emit the loader manifest (same schema as the unified asteroid catalog).

    Rebuilt from the per-shard metadata files on disk so it is correct for
    resumed and partial runs alike; consumed by
    ``small_body_readers_from_manifest`` (reads ``shards[].path``).
    """
    shard_entries: list[dict] = []
    total_bodies = 0
    for mpath in sorted(outdir.glob(f"{SHARD_PREFIX}_*.metadata.json")):
        meta = json.loads(mpath.read_text(encoding="utf-8"))
        if (
            meta.get("sampling_policy") != _sampling_policy()
            or meta.get("failures")
            or not meta.get("records")
        ):
            continue
        kpath = outdir / meta["kernel"]
        if not kpath.exists():
            continue
        bodies = [r["naif_id"] for r in meta["records"]]
        total_bodies += len(bodies)
        shard_entries.append(
            {
                "index": meta["shard"],
                "path": meta["kernel"],
                "body_count": len(bodies),
                "bodies": bodies,
                "bytes": kpath.stat().st_size,
                "sha256": _sha256_file(kpath),
                "metadata": {
                    "path": mpath.name,
                    "bytes": mpath.stat().st_size,
                    "sha256": _sha256_file(mpath),
                },
            }
        )
    shard_entries.sort(key=lambda s: s["index"])
    manifest = {
        "manifest_schema": "moira.small-body-catalog/v1",
        "catalog_id": "moira-comets",
        "source": "MOIRA NUMBERED PERIODIC COMET CATALOG (JPL Horizons)",
        "provenance": _catalog_provenance(),
        "coverage": {
            "start_date": WINDOW[0], "end_date": WINDOW[1],
            "note": "requested DE441 span; per-comet coverage clamped to Horizons validity",
        },
        "sampling": {
            "step_days": STEP_DAYS,
            "window_size": WINDOW_SIZE,
            **_sampling_policy(),
        },
        "accuracy_note": (
            "Comet positions are apparition-dependent due to non-gravitational "
            "outgassing forces; fidelity degrades far from observed apparitions."
        ),
        "body_count": total_bodies, "shard_count": len(shard_entries),
        "shards": shard_entries,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
