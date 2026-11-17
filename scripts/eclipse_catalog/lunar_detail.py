"""Generate a resumable, native-model lunar circumstances research catalog.

This executable is validation tooling, not a scientific oracle. It consumes a
fresh discovery index and records errors and policies rather than asserting
that numerical searches are complete. Outputs must be outside the checkout.
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
from pathlib import Path

os.environ["MOIRA_NO_DOWNLOAD"] = "1"
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import discovery
import moira
from moira import _moira_native
from moira._kernel_paths import find_planetary_kernel
from moira.eclipse import EclipseCalculator
from moira.eclipse_geometry import EARTH_RADIUS_KM
from moira.spk_reader import SpkReader

ROOT = Path(__file__).resolve().parents[2]
FIELDS = (
    "catalog_index", "calendar_date_tt", "time_tt", "jd_tt", "jd_ut1",
    "delta_t_seconds", "eclipse_type", "saros_series", "lunation_number",
    "gamma_earth_radii", "penumbral_magnitude", "umbral_magnitude",
    "penumbral_duration_seconds", "partial_duration_seconds",
    "total_duration_seconds", "lunar_mode", "source_model", "shadow_model",
    "ephemeris", "time_policy", "penumbral_margin_earth_radii",
    "umbral_margin_earth_radii", "total_margin_earth_radii", "p1_jd_ut1",
    "u1_jd_ut1", "u2_jd_ut1", "u3_jd_ut1", "u4_jd_ut1", "p4_jd_ut1",
    "status", "error",
)


def sha256(path: Path) -> str:
    """Hash the full file contents, including kernels."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_digest(root: Path = ROOT) -> str:
    """Fingerprint source, native build inputs, extension, and package data.

    Separately supplied kernels and Python caches are excluded; the active
    planetary kernel has its own full-content digest in the run receipt.
    """
    roots = (root / "moira", root / "src" / "native")
    files = []
    for directory in roots:
        for path in directory.rglob("*"):
            if (not path.is_file() or "__pycache__" in path.parts
                    or path.suffix.lower() in (".pyc", ".pyo")
                    or (directory.name == "moira" and "kernels" in path.relative_to(directory).parts)):
                continue
            files.append(path)
    files.extend(path for path in (root / "pyproject.toml", root / "setup.py", Path(__file__).resolve()) if path.is_file())
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def read_index(path: Path, shard_index: int, shard_count: int) -> list[dict]:
    """Validate a discovery index and select deterministic index shards."""
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise ValueError("shard index must be in [0, shard count)")
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("discovery index is empty")
    seen = set()
    previous_tt = -math.inf
    selected = []
    for i, row in enumerate(rows):
        lunation = int(row["lunation_number"])
        if lunation in seen:
            raise ValueError(f"duplicate lunar lunation {lunation}")
        seen.add(lunation)
        if row.get("family", "lunar").lower() != "lunar":
            raise ValueError("index contains a non-lunar record")
        jd_tt, jd_ut = float(row["jd_tt"]), float(row["jd_ut1"])
        if not math.isfinite(jd_tt) or not math.isfinite(jd_ut) or jd_tt <= previous_tt:
            raise ValueError("index epochs must be finite and strictly increasing")
        previous_tt = jd_tt
        if i % shard_count == shard_index:
            selected.append({**row, "_catalog_index": i + 1})
    return selected


def mixed_calendar(jd: float) -> tuple[str, str]:
    """Format a TT epoch to nearest second on NASA's historical calendar."""
    value = jd + 0.5 + 0.5 / 86400.0
    z = math.floor(value)
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
    second = min(86399, math.floor((value - z) * 86400))
    return f"{year:+05d}-{month:02d}-{day:02d}", f"{second // 3600:02d}:{second // 60 % 60:02d}:{second % 60:02d}"


def calculate_row(calculator, entry: dict) -> dict:
    """Compute native circumstances at the native greatest-axis epoch.

    Signed phase margins are native radius combinations at that same epoch,
    not separately optimized maximum overlaps. Missing contacts or durations
    describe the solver's output and do not certify phase absence.
    """
    seed = float(entry["jd_ut1"])
    result = calculator.lunar_global_circumstances(seed - 1.0, mode="native")
    event = result.analysis.event
    if int(event.data.saros_lunation_number) != int(entry["lunation_number"]):
        raise ValueError("detailed event lunation differs from discovery")
    if abs(event.jd_ut - seed) > 0.02:
        raise ValueError("detailed event epoch differs from discovery by more than 0.02 days")
    date, clock = mixed_calendar(result.greatest.jd_tt)
    shadow = result.shadow
    r = shadow.axis_distance_km / EARTH_RADIUS_KM
    contacts = result.analysis.contacts
    values = {
        "catalog_index": entry["_catalog_index"], "calendar_date_tt": date,
        "time_tt": clock, "jd_tt": result.greatest.jd_tt,
        "jd_ut1": result.greatest.jd_ut1,
        "delta_t_seconds": result.greatest.delta_t_seconds,
        "eclipse_type": str(event.data.eclipse_type), "saros_series": event.data.saros_series,
        "lunation_number": int(entry["lunation_number"]),
        "gamma_earth_radii": shadow.gamma_earth_radii,
        "penumbral_magnitude": shadow.penumbral_magnitude,
        "umbral_magnitude": shadow.umbral_magnitude,
        "penumbral_duration_seconds": result.penumbral_duration_seconds,
        "partial_duration_seconds": result.partial_duration_seconds,
        "total_duration_seconds": result.total_duration_seconds,
        "lunar_mode": result.mode, "source_model": result.source_model,
        "shadow_model": shadow.shadow_model, "ephemeris": result.ephemeris,
        "time_policy": result.greatest.time_policy,
        "penumbral_margin_earth_radii": shadow.penumbra_radius_earth_radii + shadow.moon_radius_earth_radii - r,
        "umbral_margin_earth_radii": shadow.umbra_radius_earth_radii + shadow.moon_radius_earth_radii - r,
        "total_margin_earth_radii": shadow.umbra_radius_earth_radii - shadow.moon_radius_earth_radii - r,
        "status": "ok", "error": "",
    }
    for name in ("p1", "u1", "u2", "u3", "u4", "p4"):
        values[name + "_jd_ut1"] = getattr(contacts, name)
    return values


def load_journal(path: Path, allowed: set[int]) -> dict[int, dict]:
    """Read every durable attempt, retaining the latest attempt per identity."""
    latest: dict[int, dict] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            key = int(record["lunation_number"])
            if key not in allowed or record.get("status") not in ("ok", "error"):
                raise ValueError("journal contains an invalid identity or status")
            if key in latest and latest[key]["status"] == "ok":
                raise ValueError("journal repeats an already successful identity")
            latest[key] = record
    return latest


def write_catalog(path: Path, rows: list[dict]) -> None:
    """Materialize the last attempt per index row without partial replacement."""
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--index-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kernel-sha256", required=True)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    output, index = args.output.resolve(), args.index.resolve()
    if output.is_relative_to(ROOT):
        parser.error("bulk catalog outputs must be outside the repository checkout")
    if output == index or output == args.index_receipt.resolve():
        parser.error("output must differ from all input files")
    if not output.parent.is_dir():
        parser.error("output parent directory must already exist")
    meta, journal, finish = (output.with_suffix(output.suffix + suffix) for suffix in (".metadata.json", ".journal.jsonl", ".receipt.json"))
    owned = {output, meta, journal, finish, output.with_name(output.name + ".tmp"),
             finish.with_name(finish.name + ".tmp")}
    if {index, args.index_receipt.resolve()} & owned:
        parser.error("an output or associated file would overwrite an input")
    kernel_value = find_planetary_kernel()
    if kernel_value is None:
        raise RuntimeError("no planetary kernel is available with downloads disabled")
    kernel = Path(kernel_value).resolve()
    if ROOT not in Path(_moira_native.__file__).resolve().parents:
        raise RuntimeError("native extension is outside the isolated checkout")
    kernel_hash = sha256(kernel)
    if kernel_hash.lower() != args.kernel_sha256.lower():
        raise ValueError("kernel does not match the supplied SHA-256")
    selected = read_index(index, args.shard_index, args.shard_count)
    source_hash = source_digest()
    index_receipt = json.loads(args.index_receipt.read_text(encoding="utf-8"))
    discovery_hash = discovery.source_fingerprint()
    if (index_receipt.get("status") != "provisional" or index_receipt.get("family") != "lunar"
            or index_receipt.get("merged_sha256") != sha256(index)
            or index_receipt.get("kernel_sha256") != kernel_hash
            or index_receipt.get("source_fingerprint_sha256") != discovery_hash):
        raise ValueError("discovery receipt does not match the lunar index, kernel and source")
    with index.open(encoding="utf-8", newline="") as stream:
        if sum(1 for _ in csv.DictReader(stream)) != index_receipt.get("row_count"):
            raise ValueError("discovery receipt row count differs from the index")
    receipt = {
        "schema": "moira-native-lunar-detailed-shard-v1", "provisional": True,
        "moira_version": moira.__version__, "source_root": str(ROOT),
        "source_sha256": source_hash, "runner_sha256": sha256(Path(__file__)),
        "index": str(index), "index_sha256": sha256(index),
        "index_receipt": str(args.index_receipt.resolve()),
        "index_receipt_sha256": sha256(args.index_receipt),
        "discovery_source_sha256": discovery_hash,
        "kernel": str(kernel), "kernel_sha256": kernel_hash,
        "shard_index": args.shard_index, "shard_count": args.shard_count,
        "selected_rows": len(selected), "python": sys.version, "platform": platform.platform(),
        "policy": "native lunar global circumstances; retarded Sun, same-epoch geometric Moon; Moira Danjon-style shadow",
        "time_scales": "TT and UT1; historical calendar; neither is UTC",
        "limits": "Provisional model outputs; index membership is not certified. Missing contact/phase means the native solver returned none, not proven absence. Signed phase margins are radius combinations at native greatest-axis epoch, not separately optimized overlap. No NASA parity claim.",
    }
    if args.resume:
        if not meta.is_file() or not journal.is_file():
            raise ValueError("resume requires both matching metadata and journal")
        if json.loads(meta.read_text(encoding="utf-8")) != receipt:
            raise ValueError("resume metadata differs from current inputs or source")
    else:
        if any(p.exists() for p in (output, meta, journal, finish, output.with_name(output.name + ".tmp"))):
            raise FileExistsError("output or associated files already exist")
        with meta.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
        with journal.open("x", encoding="utf-8"):
            pass
    allowed = {int(row["lunation_number"]) for row in selected}
    latest = load_journal(journal, allowed)
    with SpkReader(kernel) as reader, journal.open("a", encoding="utf-8") as ledger:
        calculator = EclipseCalculator(reader=reader)
        for entry in selected:
            key = int(entry["lunation_number"])
            if key in latest and latest[key]["status"] == "ok":
                continue
            try:
                row = calculate_row(calculator, entry)
            except Exception as exc:
                row = {"catalog_index": entry["_catalog_index"], "lunation_number": key,
                       "status": "error", "error": f"{type(exc).__name__}: {exc}"}
            ledger.write(json.dumps(row, allow_nan=False) + "\n")
            ledger.flush()
            os.fsync(ledger.fileno())
            latest[key] = row
            print(json.dumps({"lunation": key, "status": row["status"]}), flush=True)
    if (sha256(kernel) != kernel_hash or sha256(index) != receipt["index_sha256"]
            or source_digest() != source_hash
            or sha256(args.index_receipt) != receipt["index_receipt_sha256"]
            or discovery.source_fingerprint() != discovery_hash):
        raise RuntimeError("source or an input changed during generation; output not finalized")
    if set(latest) != allowed:
        raise RuntimeError("journal does not account for every selected identity")
    ordered = [latest[int(entry["lunation_number"])] for entry in selected]
    write_catalog(output, ordered)
    errors = [int(row["lunation_number"]) for row in ordered if row["status"] != "ok"]
    result = {"complete_without_row_errors": not errors, "row_count": len(ordered),
              "error_lunations": errors, "output_sha256": sha256(output),
              "journal_sha256": sha256(journal), "source_sha256": source_hash,
              "kernel_sha256": kernel_hash, "provisional": True}
    # A completion receipt is replaced only after an explicit resume.
    temporary_receipt = finish.with_name(finish.name + ".tmp")
    with temporary_receipt.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    os.replace(temporary_receipt, finish)
    print(json.dumps(result), flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
