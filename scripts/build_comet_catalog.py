"""
Build the Moira numbered-periodic-comet catalog: one Type-13 shard set covering
every numbered periodic comet (1P..NP), sourced from JPL Horizons.

Reads targets from a JSON list ([{"number": N, "full_name": "1P/Halley"}, ...]),
fetches heliocentric states from Horizons via the periodic-comet designation
directive (DES=NP;NOFRAG;CAP -- one non-fragment apparition solution), writes
Type-13 shards (<= 25 bodies each), verifies node round-trip, and emits per-shard
+ master registration metadata. NAIF id = 1000000 + comet number.

ACCURACY NOTE (recorded in the manifest, surfaced in docs): comet orbits are
perturbed by non-gravitational outgassing forces, so positions are only reliable
NEAR observed apparitions and degrade far from them. Horizons returns the full
1600-2500 span for numbered comets, but fidelity is apparition-dependent, unlike
the uniform asteroid case. This is delivered honestly, not hidden.

RESUMABLE: a shard whose kernel + metadata already cover their bodies is skipped.
Per-comet window: 1600-2500 requested; a comet whose Horizons coverage is
narrower is clamped to its stated valid range.

Usage:
    python scripts/build_comet_catalog.py TARGETS.json START COUNT [OUTDIR]

Unit law: Horizons VECTORS OUT_UNITS=KM-S; Type-13 is seconds-based so velocities
stay km/s. Horizons epochs are JDTDB (kernel time), queried back as jd_tt with
center = 10 (Sun).
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._spk_body_kernel import SmallBodyKernel
from moira.daf_writer import write_spk_type13

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
WINDOW = ("1600-01-01", "2500-01-01")
STEP_DAYS = 30
WINDOW_SIZE = 5
SHARD_SIZE = 25
CENTER = 10
FRAME = 1
THROTTLE_S = 1.0
SHARD_PREFIX = "comet_shard"

_NAME_RE = re.compile(r"Target body name:\s*([^\{]+?)\s*\{")
_FLOOR_RE = re.compile(r"prior to A\.D\.\s*([0-9]{3,4})-([A-Za-z]{3})-([0-9]{2})")
_CEIL_RE = re.compile(r"after A\.D\.\s*([0-9]{3,4})-([A-Za-z]{3})-([0-9]{2})")


def _fetch_raw(command: str, start: str, stop: str) -> str:
    params = {
        "format": "text", "COMMAND": command, "OBJ_DATA": "NO", "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS", "CENTER": "500@10", "REF_PLANE": "FRAME",
        "START_TIME": start, "STOP_TIME": stop, "STEP_SIZE": f"{STEP_DAYS}d",
        "OUT_UNITS": "KM-S", "VEC_TABLE": "2", "VEC_LABELS": "YES",
        "CSV_FORMAT": "YES", "TIME_DIGITS": "FRACSEC",
    }
    url = f"{HORIZONS_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=300) as resp:
        return resp.read().decode("utf-8")


def _parse_name(raw: str, number: int) -> str:
    m = _NAME_RE.search(raw)
    return m.group(1).strip() if m else f"{number}P"


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
    start, stop, clamped = WINDOW[0], WINDOW[1], False
    try:
        epochs, states = _parse_vectors(raw)
    except RuntimeError:
        win = _clamped_window(raw)
        if win is None:
            head = "\n".join(raw.splitlines()[:40])
            raise RuntimeError(f"comet {number}P: no vectors and no parseable range:\n{head}")
        start, stop, clamped = win[0], win[1], True
        raw = _fetch_raw(command, start, stop)
        epochs, states = _parse_vectors(raw)
    return {
        "number": number, "naif_id": 1000000 + number, "name": _parse_name(raw, number),
        "center": CENTER, "frame": FRAME, "states": states, "epochs_jd": epochs,
        "window_size": WINDOW_SIZE, "clamped": clamped, "start": start, "stop": stop,
    }


def _verify(kernel: SmallBodyKernel, naif_id: int, epochs: list[float], states: list[list[float]]) -> float:
    max_err = 0.0
    for i, jd_tdb in enumerate(epochs):
        gx, gy, gz = kernel.position(CENTER, naif_id, jd_tdb)
        max_err = max(max_err, abs(gx - states[0][i]), abs(gy - states[1][i]), abs(gz - states[2][i]))
    return max_err


def _shard_cached(kpath: Path, mpath: Path) -> dict | None:
    if not (kpath.exists() and mpath.exists()):
        return None
    try:
        meta = json.loads(mpath.read_text())
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
    outdir = Path(sys.argv[4]) if len(sys.argv) > 4 else ROOT / "moira" / "kernels" / "comets"
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
        "accuracy_note": (
            "Comet positions are apparition-dependent due to non-gravitational "
            "outgassing forces; fidelity degrades far from observed apparitions."
        ),
        "naif_map": m_naif, "records": m_records, "failures": m_failures,
    }
    (outdir / "comet_master.json").write_text(json.dumps(master, indent=2))
    _write_manifest(outdir)
    print(f"\nDONE: {len(m_records)} built, {len(m_failures)} failed, {len(shards)} shards", flush=True)


def _write_manifest(outdir: Path) -> None:
    """Emit the loader manifest (same schema as the unified asteroid catalog).

    Rebuilt from the per-shard metadata files on disk so it is correct for
    resumed and partial runs alike; consumed by
    ``small_body_readers_from_manifest`` (reads ``shards[].path``).
    """
    shard_entries: list[dict] = []
    total_bodies = 0
    for mpath in sorted(outdir.glob(f"{SHARD_PREFIX}_*.metadata.json")):
        meta = json.loads(mpath.read_text())
        kpath = outdir / meta["kernel"]
        if not kpath.exists():
            continue
        bodies = [r["naif_id"] for r in meta["records"]]
        total_bodies += len(bodies)
        shard_entries.append({
            "index": meta["shard"], "path": meta["kernel"],
            "body_count": len(bodies), "bodies": bodies,
        })
    shard_entries.sort(key=lambda s: s["index"])
    manifest = {
        "source": "MOIRA NUMBERED PERIODIC COMET CATALOG (JPL Horizons)",
        "coverage": {
            "start_date": WINDOW[0], "end_date": WINDOW[1],
            "note": "requested DE441 span; per-comet coverage clamped to Horizons validity",
        },
        "sampling": {"step_days": STEP_DAYS, "window_size": WINDOW_SIZE},
        "accuracy_note": (
            "Comet positions are apparition-dependent due to non-gravitational "
            "outgassing forces; fidelity degrades far from observed apparitions."
        ),
        "body_count": total_bodies, "shard_count": len(shard_entries),
        "shards": shard_entries,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
