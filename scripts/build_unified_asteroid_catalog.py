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

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._spk_body_kernel import SmallBodyKernel
from moira.daf_writer import write_spk_type13

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
SBDB_URL = "https://ssd-api.jpl.nasa.gov/sbdb.api"
WINDOW = ("1600-01-01", "2500-01-01")  # uniform DE441 small-body span (inside 1599..2501)
STEP_DAYS = 30
WINDOW_SIZE = 5
SHARD_SIZE = 25
CENTER = 10
FRAME = 1
THROTTLE_S = 1.0
SHARD_PREFIX = "asteroid_shard"

# These near-Earth asteroids have chaotic solutions whose long extrapolations
# depend materially on the requested Horizons interval.  Their Type-13 records
# therefore cover only the observational arc reported by JPL SBDB.  This is a
# source-owned coverage policy, not an interpolation exception.
OBSERVATION_ARC_LIMITED_BODIES = frozenset({1566, 1862})  # Icarus, Apollo

_NAME_RE = re.compile(r"Target body name:\s*(\d+)\s+([^\(]+?)\s*[\(\{]")
_FLOOR_RE = re.compile(r"prior to A\.D\.\s*([0-9]{3,4})-([A-Za-z]{3})-([0-9]{2})")
_CEIL_RE = re.compile(r"after A\.D\.\s*([0-9]{3,4})-([A-Za-z]{3})-([0-9]{2})")
_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], start=1)}
_TRANSIENT_HTTP_CODES = frozenset({429, 502, 503, 504})
_MAX_REQUEST_ATTEMPTS = 4


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
        "START_TIME": start, "STOP_TIME": stop, "STEP_SIZE": f"{STEP_DAYS}d",
        "OUT_UNITS": "KM-S", "VEC_TABLE": "2", "VEC_LABELS": "YES",
        "CSV_FORMAT": "YES", "TIME_DIGITS": "FRACSEC",
    }
    url = f"{HORIZONS_URL}?{urllib.parse.urlencode(params)}"
    return _read_url(url, timeout=300)


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

    raw = _fetch_raw(command, start, stop)
    try:
        epochs, states = _parse_vectors(raw)
    except RuntimeError:
        win = _clamped_window(raw)
        if win is None:
            head = "\n".join(raw.splitlines()[:40])
            raise RuntimeError(f"body {number}: no vectors and no parseable range:\n{head}")
        start, stop, clamped = win[0], win[1], True
        raw = _fetch_raw(command, start, stop)
        epochs, states = _parse_vectors(raw)
    result = {
        "number": number, "naif_id": 2000000 + number, "name": _parse_name(raw, number),
        "center": CENTER, "frame": FRAME, "states": states, "epochs_jd": epochs,
        "window_size": WINDOW_SIZE, "clamped": clamped, "start": start, "stop": stop,
    }
    if coverage_provenance is not None:
        result["coverage_policy"] = "jpl_sbdb_observation_arc"
        result["coverage_provenance"] = coverage_provenance
    return result


def _verify(kernel: SmallBodyKernel, naif_id: int, epochs: list[float], states: list[list[float]]) -> float:
    max_err = 0.0
    for i, jd_tdb in enumerate(epochs):
        gx, gy, gz = kernel.position(CENTER, naif_id, jd_tdb)
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


def _shard_cached(kpath: Path, mpath: Path) -> dict | None:
    if not (kpath.exists() and mpath.exists()):
        return None
    try:
        meta = json.loads(mpath.read_text())
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
        return meta if want <= have else None
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    targets_path = Path(sys.argv[1])
    start_idx = int(sys.argv[2])
    count = int(sys.argv[3])
    outdir = Path(sys.argv[4]) if len(sys.argv) > 4 else ROOT / "moira" / "kernels" / "asteroids"
    outdir.mkdir(parents=True, exist_ok=True)

    slice_targets = json.loads(targets_path.read_text())[start_idx : start_idx + count]
    shards: dict[int, list] = {}
    for local, t in enumerate(slice_targets):
        shards.setdefault((start_idx + local) // SHARD_SIZE, []).append(t)

    m_records: list[dict] = []
    m_naif: dict[str, int] = {}
    m_failures: list[dict] = []

    for sidx in sorted(shards):
        kpath = outdir / f"{SHARD_PREFIX}_{sidx:03d}.bsp"
        mpath = outdir / f"{SHARD_PREFIX}_{sidx:03d}.metadata.json"
        cached = _shard_cached(kpath, mpath)
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
                b = _fetch_body(num)
            except Exception as e:  # noqa: BLE001
                failures.append({"number": num, "family": t.get("family"), "error": str(e)[:200]})
                print(f"  [SKIP] {num} ({t.get('family')}): {str(e)[:70]}", flush=True)
                continue
            dt = time.perf_counter() - t0
            bodies.append(b)
            records.append({
                "number": num, "naif_id": b["naif_id"], "name": b["name"], "family": t.get("family"),
                "nodes": len(b["epochs_jd"]), "clamped": b["clamped"],
                "start": b["start"], "stop": b["stop"], "fetch_s": round(dt, 1),
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
            "records": records, "failures": failures,
            "naif_map": {r["name"]: r["naif_id"] for r in records},
        }
        mpath.write_text(json.dumps(shard_meta, indent=2))
        m_records.extend(records)
        m_naif.update(shard_meta["naif_map"])
        m_failures.extend(failures)
        worst = max((r["max_node_error_km"] for r in records), default=0.0)
        print(f"  shard {sidx:03d} -> {kpath.name} ({kpath.stat().st_size/1024:.0f} KB), "
              f"{len(records)} bodies, worst {worst:.2e} km, {len(failures)} failed", flush=True)

    master = {
        "requested": len(slice_targets), "built": len(m_records), "failed": len(m_failures),
        "window": WINDOW, "step_days": STEP_DAYS, "window_size": WINDOW_SIZE,
        "naif_map": m_naif, "records": m_records, "failures": m_failures,
    }
    (outdir / "unified_master.json").write_text(json.dumps(master, indent=2))
    print(f"\nDONE: {len(m_records)} built, {len(m_failures)} failed, {len(shards)} shards", flush=True)


if __name__ == "__main__":
    main()
