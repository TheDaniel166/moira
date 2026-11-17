"""Generate opt-in, provisional lunar shadow candidate rows for a discovery index.

The index is the native model's known event set, not an enumeration of all
lunations or model-specific discoveries. A local non-detection is unresolved,
not an absent eclipse. Candidate type, extrema and contacts are uncertified and
never replace native or external catalog event classifications.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import sys
from pathlib import Path

os.environ["MOIRA_NO_DOWNLOAD"] = "1"
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import discovery
import lunar_detail as lunar
import moira
from moira import _moira_native
from moira.eclipse import EclipseCalculator
from moira.lunar_shadow_events import LunarShadowWindowError, inspect_lunar_shadow_candidate
from moira.lunar_shadow_models import LunarShadowDomainError
from moira.spk_reader import SpkReader

POLICIES = ("danjon_angular", "static_finite_cone")
FIELDS = (
    "lunation_number", "catalog_index", "policy", "status", "reason", "complete",
    "candidate_type", "threshold_status", "penumbral_max_jd_ut1",
    "umbral_max_jd_ut1", "total_max_jd_ut1", "axis_min_jd_ut1",
    "opposition_min_jd_ut1", "margin_unit", "penumbral_margin_at_pmax",
    "umbral_margin_at_pmax", "total_margin_at_pmax", "axis_distance_km_at_pmax",
    "gamma_unsigned_at_pmax", "p1_jd_ut1", "u1_jd_ut1", "u2_jd_ut1",
    "u3_jd_ut1", "u4_jd_ut1", "p4_jd_ut1",
)


def calculate_candidate(calculator, entry: dict, policy: str) -> dict:
    """Evaluate one selected policy; a missing candidate stays unresolved."""
    key = int(entry["lunation_number"])
    row = {"lunation_number": key, "catalog_index": entry["_catalog_index"],
           "policy": policy, "complete": False}
    try:
        result = inspect_lunar_shadow_candidate(
            calculator, float(entry["jd_ut1"]), policy=policy,
            earth_radius_scale=1.0, window_days=0.3, coarse_step_seconds=120.0,
        )
    except (LunarShadowWindowError, LunarShadowDomainError) as exc:
        return {**row, "status": "unresolved", "reason": f"{type(exc).__name__}: {exc}"}
    if result.complete or result.status not in ("detected", "unresolved"):
        raise ValueError("unexpected candidate completeness or status")
    if result.status == "unresolved":
        if result.event is not None:
            raise ValueError("unresolved candidate unexpectedly has an event")
        return {**row, "status": "unresolved", "reason": result.reason or "numerical search unresolved"}
    event = result.event
    if event is None or event.policy != policy or event.completeness_certified:
        raise ValueError("invalid detected candidate or policy")
    geometry = event.geometry_at_greatest
    row.update(status="detected", reason="", candidate_type=event.candidate_type,
               threshold_status=event.threshold_status, penumbral_max_jd_ut1=event.greatest_jd_ut,
               umbral_max_jd_ut1=event.umbral_maximum_jd_ut,
               total_max_jd_ut1=event.total_maximum_jd_ut,
               axis_min_jd_ut1=event.axis_distance_minimum_jd_ut,
               opposition_min_jd_ut1=event.angular_opposition_minimum_jd_ut,
               margin_unit=geometry.margin_unit, penumbral_margin_at_pmax=geometry.penumbral_margin,
               umbral_margin_at_pmax=geometry.umbral_margin, total_margin_at_pmax=geometry.total_margin,
               axis_distance_km_at_pmax=geometry.axis_distance_km, gamma_unsigned_at_pmax=geometry.gamma)
    for name in ("p1", "u1", "u2", "u3", "u4", "p4"):
        row[name + "_jd_ut1"] = getattr(event.contacts, name)
    return row


def load_journal(path: Path, allowed: set[tuple[int, str]]) -> dict[tuple[int, str], dict]:
    """Retain latest attempt; successful or unresolved attempts are final."""
    latest = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            key = (int(row["lunation_number"]), row["policy"])
            if key not in allowed or row.get("complete") is not False or row.get("status") not in ("detected", "unresolved", "error"):
                raise ValueError("invalid candidate journal record")
            if key in latest and latest[key]["status"] != "error":
                raise ValueError("journal repeats a completed candidate")
            latest[key] = row
    return latest


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
    index, index_receipt, output = (p.resolve() for p in (args.index, args.index_receipt, args.output))
    if output.is_relative_to(lunar.ROOT) or not output.parent.is_dir():
        parser.error("output parent must exist outside the checkout")
    meta, journal, finish = (output.with_suffix(output.suffix + suffix) for suffix in
                             (".metadata.json", ".journal.jsonl", ".receipt.json"))
    output_tmp = output.with_name(output.name + ".tmp")
    receipt_tmp = finish.with_name(finish.name + ".tmp")
    if {index, index_receipt} & {output, meta, journal, finish, output_tmp, receipt_tmp}:
        parser.error("an output or sidecar would overwrite an input")
    kernel_value = lunar.find_planetary_kernel()
    if kernel_value is None:
        raise RuntimeError("planetary kernel unavailable")
    kernel = Path(kernel_value).resolve()
    if lunar.ROOT not in Path(_moira_native.__file__).resolve().parents:
        raise RuntimeError("native extension is outside the isolated checkout")
    kernel_hash = lunar.sha256(kernel)
    if kernel_hash.lower() != args.kernel_sha256.lower():
        raise ValueError("kernel SHA-256 mismatch")
    selected = lunar.read_index(index, args.shard_index, args.shard_count)
    index_hash, index_receipt_hash = lunar.sha256(index), lunar.sha256(index_receipt)
    source_hash, discovery_hash = lunar.source_digest(), discovery.source_fingerprint()
    runner_hash = lunar.sha256(Path(__file__))
    ref = json.loads(index_receipt.read_text(encoding="utf-8"))
    with index.open(encoding="utf-8", newline="") as stream:
        row_count = sum(1 for _ in csv.DictReader(stream))
    if (ref.get("status") != "provisional" or ref.get("family") != "lunar"
            or ref.get("merged_sha256") != index_hash or ref.get("row_count") != row_count
            or ref.get("kernel_sha256") != kernel_hash
            or ref.get("source_fingerprint_sha256") != discovery_hash):
        raise ValueError("discovery receipt does not match input, kernel and source")
    metadata = {
        "schema": "moira-lunar-candidate-supplement-shard-v1", "provisional": True,
        "moira_version": moira.__version__, "source_root": str(lunar.ROOT),
        "source_sha256": source_hash, "discovery_source_sha256": discovery_hash,
        "runner_sha256": runner_hash, "index": str(index), "index_sha256": index_hash,
        "index_receipt": str(index_receipt), "index_receipt_sha256": index_receipt_hash,
        "kernel": str(kernel), "kernel_sha256": kernel_hash,
        "shard_index": args.shard_index, "shard_count": args.shard_count,
        "selected_events": len(selected), "expected_rows": len(selected) * len(POLICIES),
        "policies": list(POLICIES), "earth_radius_scale": 1.0, "window_days": 0.3,
        "coarse_step_seconds": 120.0, "python": sys.version, "platform": platform.platform(),
        "vector_policy": "incoming retarded Sun, simultaneous geocentric Moon; no annual aberration",
        "time_scale": "UT1", "limits": (
            "Native-discovered input events only; no independent enumeration or negative event proof. "
            "Candidate types, extrema, and contacts are incomplete; missing phases are not certified absent. "
            "Margins in the selected model's stated unit are evaluated at the candidate penumbral-overlap "
            "maximum, not phase-specific maximum; the finite cone is a static sensitivity model. "
            "These outputs do not replace native or external catalog types and do not establish NASA parity."
        ),
    }
    if args.resume:
        if not meta.is_file() or not journal.is_file():
            raise ValueError("resume requires both metadata and journal")
        if json.loads(meta.read_text(encoding="utf-8")) != metadata:
            raise ValueError("resume metadata differs from current inputs or source")
    else:
        if any(path.exists() for path in (output, meta, journal, finish, output_tmp, receipt_tmp)):
            raise FileExistsError("output or a sidecar already exists")
        with meta.open("x", encoding="utf-8") as stream:
            json.dump(metadata, stream, indent=2)
            stream.write("\n")
        with journal.open("x", encoding="utf-8"):
            pass
    allowed = {(int(entry["lunation_number"]), policy) for entry in selected for policy in POLICIES}
    latest = load_journal(journal, allowed)
    with SpkReader(kernel) as reader, journal.open("a", encoding="utf-8") as ledger:
        calculator = EclipseCalculator(reader=reader)
        for entry in selected:
            for policy in POLICIES:
                key = int(entry["lunation_number"]), policy
                if key in latest and latest[key]["status"] != "error":
                    continue
                try:
                    row = calculate_candidate(calculator, entry, policy)
                except Exception as exc:
                    row = {"lunation_number": key[0], "catalog_index": entry["_catalog_index"],
                           "policy": policy, "complete": False, "status": "error",
                           "reason": f"{type(exc).__name__}: {exc}"}
                ledger.write(json.dumps(row, allow_nan=False) + "\n")
                ledger.flush()
                os.fsync(ledger.fileno())
                latest[key] = row
                print(json.dumps({"lunation": key[0], "policy": policy, "status": row["status"]}), flush=True)
    if (lunar.sha256(kernel) != kernel_hash or lunar.sha256(index) != index_hash
            or lunar.sha256(index_receipt) != index_receipt_hash or lunar.source_digest() != source_hash
            or discovery.source_fingerprint() != discovery_hash or lunar.sha256(Path(__file__)) != runner_hash):
        raise RuntimeError("source or an input changed; no output finalized")
    if set(latest) != allowed:
        raise RuntimeError("journal does not account for every requested candidate")
    ordered = [latest[(int(entry["lunation_number"]), policy)] for entry in selected for policy in POLICIES]
    with output_tmp.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(ordered)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(output_tmp, output)
    statuses = {name: sum(row["status"] == name for row in ordered) for name in ("detected", "unresolved", "error")}
    result = {"schema": "moira-lunar-candidate-supplement-shard-receipt-v1", "provisional": True,
              "complete_without_errors": statuses["error"] == 0, "row_count": len(ordered),
              "status_counts": statuses, "output_sha256": lunar.sha256(output),
              "journal_sha256": lunar.sha256(journal), "source_sha256": source_hash,
              "discovery_source_sha256": discovery_hash, "runner_sha256": runner_hash,
              "kernel_sha256": kernel_hash, "limits": metadata["limits"]}
    with receipt_tmp.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    os.replace(receipt_tmp, finish)
    print(json.dumps(result), flush=True)
    return 1 if statuses["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
