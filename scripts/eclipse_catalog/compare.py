"""Join provisional native eclipse results to preserved catalog references.

The output is an audit of model outputs, not a physical accuracy measurement.
All records are retained, including unmatched and ambiguous reference events.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MONTHS = {name: i for i, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
IGNORED_FIELDS = {"catalog_index", "elapsed_seconds"}


def digest(path: Path) -> str:
    """Hash an input or output file."""
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def table(path: Path, delimiter: str = ",") -> list[dict]:
    """Read a delimited table without dropping empty fields."""
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def by_key(rows: list[dict], key: str, source: str) -> dict[int, dict]:
    """Require a present unique lunation identity in every record."""
    result = {}
    for row in rows:
        try:
            lunation = int(row[key])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"invalid lunation in {source}: {row!r}") from exc
        if lunation in result:
            raise ValueError(f"duplicate lunation {lunation} in {source}")
        result[lunation] = row
    return result


def historical_jd(year: int, month: int, day: int, clock: str) -> float:
    """Convert a NASA historical-calendar TD/TT second to Julian day."""
    gregorian = (year, month, day) >= (1582, 10, 15)
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    correction = 2 - a + math.floor(a / 4) if gregorian else 0
    h, m, s = (int(value) for value in clock.split(":"))
    return (math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1))
            + day + correction - 1524.5 + (h * 3600 + m * 60 + s) / 86400)


def load_nasa(path: Path, family: str) -> dict[int, dict]:
    """Read NASA's extracted solar JSON or lunar TSV and retain raw records."""
    if family == "solar":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = [{"catalog_number": r[0], "year": r[1], "month": r[2], "day": r[3],
                 "clock_tt": r[4], "delta_t_seconds": r[5], "lunation": r[6],
                 "saros": r[7], "type": r[8]} for r in payload["rows"]]
    else:
        rows = [{**r, "year": int(r["astro_year"]), "clock_tt": r["tt"]}
                for r in table(path, "\t")]
    for row in rows:
        row["jd_tt"] = historical_jd(int(row["year"]), MONTHS[row["month"]],
                                     int(row["day"]), row["clock_tt"])
    return by_key(rows, "lunation", "NASA")


def broad_type(value: str | None, family: str) -> str | None:
    """Normalize broad types only; preserve original subtype separately."""
    if not value:
        return None
    text = value.lower()
    named = {"partial": "P", "total": "T", "annular": "A", "hybrid": "H", "penumbral": "N"}
    if text in named:
        return named[text]
    first = value[0].upper()
    allowed = "PATH" if family == "solar" else "NPT"
    if first not in allowed:
        raise ValueError(f"unknown {family} eclipse type: {value!r}")
    return first


def finite(value) -> float | None:
    """Parse an optional finite number, retaining missing values as None."""
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) else None


def compare_fields(old: dict | None, new: dict | None) -> dict:
    """Report every unequal shared field except operational row counters."""
    if old is None or new is None:
        return {}
    changes = {}
    for key in sorted((old.keys() & new.keys()) - IGNORED_FIELDS):
        a, b = old[key], new[key]
        if str(a) == str(b):
            continue
        x, y = finite(a), finite(b)
        if x is not None and y is not None and x == y:
            continue
        item = {"old": a, "new": b}
        if x is not None and y is not None:
            item["delta"] = y - x
            if key in {"jd_tt", "jd_ut1"} or key.endswith(("_jd_tt", "_jd_ut1")):
                item["delta_seconds"] = (y - x) * 86400
        changes[key] = item
    return changes


def assign_skyfield(rows: list[dict], anchors: dict[int, list[float]],
                    threshold_days: float = 2.0) -> tuple[dict[int, dict], list[dict]]:
    """Uniquely associate each Skyfield epoch; retain unmatched/ambiguous rows.

    A candidate event is any anchor within the threshold. No result is assigned
    when either an epoch has multiple candidates or multiple epochs compete
    for the same event. Prior CSV lunations are preserved only as provenance.
    """
    timeline = sorted((jd, key) for key, values in anchors.items() for jd in values)
    times = [value[0] for value in timeline]
    candidates = []
    seen_epochs = set()
    for row in rows:
        if row.get("skyfield_present", "").lower() != "true":
            continue
        epoch = finite(row.get("skyfield_jd_tt"))
        if epoch is None:
            raise ValueError("present Skyfield row lacks a finite TT epoch")
        if epoch in seen_epochs:
            raise ValueError(f"duplicate Skyfield epoch {epoch}")
        seen_epochs.add(epoch)
        lo = bisect_left(times, epoch - threshold_days)
        hi = bisect_right(times, epoch + threshold_days)
        # Historical matching used a strict less-than two-day criterion.
        keys = sorted({key for jd, key in timeline[lo:hi] if abs(jd - epoch) < threshold_days})
        candidates.append((row, epoch, keys))
    claims = Counter(keys[0] for _, _, keys in candidates if len(keys) == 1)
    assigned, unresolved = {}, []
    for row, epoch, keys in candidates:
        if len(keys) == 1 and claims[keys[0]] == 1:
            assigned[keys[0]] = row
        else:
            unresolved.append({"status": "unmatched" if not keys else "ambiguous",
                               "jd_tt": epoch, "candidate_lunations": keys,
                               "prior_lunation": row.get("lunation_number") or None,
                               "skyfield": row})
    return assigned, unresolved


def read_detail(paths: list[Path], receipts: list[Path], discovery_hash: str,
                discovery_receipt_hash: str, discovery_source_hash: str,
                family: str, kernel_hash: str) -> dict[int, dict]:
    """Validate separately receipted detail shards, then require unique IDs."""
    if len(paths) != len(receipts):
        raise ValueError("each detailed CSV requires its own receipt")
    result = {}
    for path, receipt_path in zip(paths, receipts):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        actual = digest(path)
        if actual != receipt.get("merged_sha256", receipt.get("output_sha256")):
            raise ValueError(f"detailed CSV digest mismatch: {path}")
        if receipt.get("kernel_sha256") != kernel_hash:
            raise ValueError(f"detailed kernel mismatch: {receipt_path}")
        # The solar merged receipt contains its discovery hash. Lunar keeps
        # this link in its shard metadata, read beside the receipt below.
        if family == "solar":
            metadata = receipt.get("common", {})
            index_hash = metadata.get("event_index_sha256")
            index_receipt_hash = metadata.get("event_index_receipt_sha256")
        else:
            if receipt.get("schema") == "moira-native-lunar-detail-merge-v1":
                metadata = receipt
                if receipt.get("provisional") is not True or not receipt.get("shards"):
                    raise ValueError(f"incomplete lunar merge receipt: {receipt_path}")
            else:
                meta_path = path.with_name(path.name + ".metadata.json")
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                if not receipt.get("complete_without_row_errors"):
                    raise ValueError(f"lunar shard has errors: {receipt_path}")
            index_hash = metadata.get("discovery_sha256", metadata.get("index_sha256"))
            index_receipt_hash = metadata.get("index_receipt_sha256")
            if metadata.get("discovery_source_sha256") != discovery_source_hash:
                raise ValueError(f"detailed discovery source mismatch: {receipt_path}")
        if index_hash != discovery_hash:
            raise ValueError(f"detailed discovery index mismatch: {receipt_path}")
        if index_receipt_hash != discovery_receipt_hash:
            raise ValueError(f"detailed discovery receipt mismatch: {receipt_path}")
        rows = table(path)
        if receipt.get("row_count") != len(rows):
            raise ValueError(f"detail row count mismatch: {path}")
        if any(row.get("status") != "ok" for row in rows):
            raise ValueError(f"detailed output contains errors: {path}")
        for key, row in by_key(rows, "lunation_number", str(path)).items():
            if key in result:
                raise ValueError(f"duplicate detail lunation {key}")
            result[key] = row
    return result


def read_lunar_candidates(paths: list[Path], receipts: list[Path], index_hash: str,
                          index_receipt_hash: str, source_hash: str,
                          kernel_hash: str, expected_ids: set[int]) -> dict[int, dict]:
    """Read both named models, retaining candidate and unresolved states."""
    if len(paths) != len(receipts):
        raise ValueError("each lunar candidate supplement requires a receipt")
    policies = {"danjon_angular", "static_finite_cone"}
    candidates = defaultdict(dict)
    for path, receipt_path in zip(paths, receipts):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("schema") == "moira-lunar-candidate-supplement-merge-v1":
            metadata = receipt
            if not receipt.get("shards"):
                raise ValueError("lunar candidate merge has no shard receipts")
        elif receipt.get("schema") == "moira-lunar-candidate-supplement-shard-receipt-v1":
            metadata = json.loads(path.with_name(path.name + ".metadata.json").read_text(encoding="utf-8"))
            if not receipt.get("complete_without_errors"):
                raise ValueError("lunar candidate shard contains errors")
        else:
            raise ValueError("unknown lunar candidate supplement receipt schema")
        if (receipt.get("provisional") is not True or receipt.get("output_sha256") != digest(path)
                or receipt.get("kernel_sha256") != kernel_hash
                or metadata.get("index_sha256") != index_hash
                or metadata.get("index_receipt_sha256") != index_receipt_hash
                or metadata.get("discovery_source_sha256") != source_hash):
            raise ValueError("lunar candidate supplement provenance mismatch")
        rows = table(path)
        if receipt.get("row_count") != len(rows):
            raise ValueError("lunar candidate supplement count mismatch")
        for row in rows:
            key = int(row["lunation_number"])
            policy = row.get("policy")
            if key not in expected_ids or policy not in policies or policy in candidates[key]:
                raise ValueError("invalid or repeated lunar candidate identity/policy")
            if row.get("complete", "").lower() != "false" or row.get("status") not in ("detected", "unresolved"):
                raise ValueError("lunar candidate is erroneous or improperly asserts completeness")
            candidates[key][policy] = row
    if paths and (set(candidates) != expected_ids or any(set(row) != policies for row in candidates.values())):
        raise ValueError("lunar candidate supplement does not cover both policies for the discovery index")
    return dict(candidates)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("solar", "lunar"), required=True)
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--discovery-receipt", type=Path, required=True)
    parser.add_argument("--baseline-index", type=Path, required=True)
    parser.add_argument("--baseline-detail", type=Path, required=True)
    parser.add_argument("--nasa", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True,
                        help="EclipseWise CSV (solar) or preserved Skyfield joined CSV (lunar)")
    parser.add_argument("--detail", type=Path, action="append", default=[])
    parser.add_argument("--detail-receipt", type=Path, action="append", default=[])
    parser.add_argument("--supplement", type=Path,
                        help="optional solar instantaneous/path-witness JSONL")
    parser.add_argument("--supplement-receipt", type=Path)
    parser.add_argument("--lunar-candidate-supplement", type=Path, action="append", default=[])
    parser.add_argument("--lunar-candidate-receipt", type=Path, action="append", default=[])
    parser.add_argument("--compat-discovery", type=Path,
                        help="optional NASA-compatible lunar discovery index")
    parser.add_argument("--compat-discovery-receipt", type=Path)
    parser.add_argument("--compat-detail", type=Path,
                        help="optional merged NASA-compatible lunar detail")
    parser.add_argument("--compat-detail-receipt", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if len(args.detail) != len(args.detail_receipt):
        parser.error("provide one --detail-receipt for each --detail")
    if bool(args.supplement) != bool(args.supplement_receipt):
        parser.error("--supplement and --supplement-receipt must be supplied together")
    if args.supplement and (args.family != "solar" or len(args.detail) != 1):
        parser.error("solar supplement requires exactly one matching detailed solar catalog")
    if len(args.lunar_candidate_supplement) != len(args.lunar_candidate_receipt):
        parser.error("each lunar candidate supplement requires a matching receipt")
    if args.lunar_candidate_supplement and args.family != "lunar":
        parser.error("lunar candidate supplements require the lunar family")
    if bool(args.compat_discovery) != bool(args.compat_discovery_receipt):
        parser.error("compatibility discovery and receipt must be supplied together")
    if args.compat_discovery and args.family != "lunar":
        parser.error("NASA compatibility comparison currently supports the lunar family")
    if bool(args.compat_detail) != bool(args.compat_detail_receipt):
        parser.error("compatibility detail and receipt must be supplied together")
    if args.compat_detail and not args.compat_discovery:
        parser.error("compatibility detail requires compatibility discovery")
    output = args.output_dir.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("output must be outside the repository")
    input_paths = [args.discovery, args.discovery_receipt, args.baseline_index,
                   args.baseline_detail, args.nasa, args.reference, *args.detail, *args.detail_receipt]
    if args.supplement:
        input_paths.extend((args.supplement, args.supplement_receipt))
    if args.compat_discovery:
        input_paths.extend((args.compat_discovery, args.compat_discovery_receipt))
    if args.compat_detail:
        input_paths.extend((args.compat_detail, args.compat_detail_receipt))
    input_paths += [*args.lunar_candidate_supplement, *args.lunar_candidate_receipt]
    for p, r in zip(args.lunar_candidate_supplement, args.lunar_candidate_receipt):
        if json.loads(r.read_text(encoding="utf-8")).get("schema") != "moira-lunar-candidate-supplement-merge-v1":
            input_paths.append(p.with_name(p.name + ".metadata.json"))
    if args.family == "lunar":
        for p, r in zip(args.detail, args.detail_receipt):
            if json.loads(r.read_text(encoding="utf-8")).get("schema") != "moira-native-lunar-detail-merge-v1":
                input_paths.append(p.with_name(p.name + ".metadata.json"))
    hashes = {str(path.resolve()): digest(path) for path in input_paths}
    runner_hash = digest(Path(__file__))
    receipt = json.loads(args.discovery_receipt.read_text(encoding="utf-8"))
    index_hash = digest(args.discovery)
    if receipt.get("status") != "provisional" or receipt.get("family") != args.family:
        raise ValueError("unexpected discovery receipt status or family")
    if receipt.get("merged_sha256") != index_hash:
        raise ValueError("discovery CSV digest does not match its receipt")
    current = by_key(table(args.discovery), "lunation_number", "current discovery")
    if receipt.get("row_count") != len(current):
        raise ValueError("discovery row count mismatch")
    compat = {}
    compat_detail = {}
    if args.compat_discovery:
        compat_receipt = json.loads(args.compat_discovery_receipt.read_text(encoding="utf-8"))
        if (compat_receipt.get("status") != "provisional" or compat_receipt.get("mode") != "nasa_compat"
                or compat_receipt.get("family") != "lunar"
                or compat_receipt.get("merged_sha256") != digest(args.compat_discovery)
                or compat_receipt.get("source_fingerprint_sha256") != receipt["source_fingerprint_sha256"]
                or compat_receipt.get("kernel_sha256") != receipt["kernel_sha256"]):
            raise ValueError("NASA-compatible discovery receipt or source mismatch")
        compat = by_key(table(args.compat_discovery), "lunation_number", "compatibility discovery")
        if compat_receipt.get("row_count") != len(compat):
            raise ValueError("NASA-compatible discovery row count mismatch")
    if args.compat_detail:
        compat_detail_receipt = json.loads(args.compat_detail_receipt.read_text(encoding="utf-8"))
        if (compat_detail_receipt.get("schema") != "moira-nasa-compat-lunar-detail-merge-v1"
                or compat_detail_receipt.get("mode") != "nasa_compat"
                or compat_detail_receipt.get("provisional") is not True
                or compat_detail_receipt.get("output_sha256") != digest(args.compat_detail)
                or compat_detail_receipt.get("index_sha256") != digest(args.compat_discovery)
                or compat_detail_receipt.get("index_receipt_sha256") != digest(args.compat_discovery_receipt)
                or compat_detail_receipt.get("discovery_source_sha256") != receipt["source_fingerprint_sha256"]
                or compat_detail_receipt.get("kernel_sha256") != receipt["kernel_sha256"]
                or not compat_detail_receipt.get("shards")):
            raise ValueError("NASA-compatible detail receipt or source mismatch")
        compat_detail = by_key(table(args.compat_detail), "lunation_number", "compatibility detail")
        if (len(compat_detail) != compat_detail_receipt.get("row_count")
                or set(compat_detail) != set(compat)
                or any(row.get("status") != "ok" for row in compat_detail.values())):
            raise ValueError("NASA-compatible detail has missing identities or errors")
    old_index = by_key(table(args.baseline_index), "lunation_number", "baseline index")
    old_detail = by_key(table(args.baseline_detail), "lunation_number", "baseline detail")
    nasa = load_nasa(args.nasa, args.family)
    details = read_detail(args.detail, args.detail_receipt, index_hash,
                          digest(args.discovery_receipt), receipt["source_fingerprint_sha256"],
                          args.family, receipt["kernel_sha256"])
    if args.detail and set(details) != set(current):
        raise ValueError("detailed output does not cover precisely the discovery identities")
    supplements = {}
    if args.supplement:
        supplemental_receipt = json.loads(args.supplement_receipt.read_text(encoding="utf-8"))
        if (supplemental_receipt.get("status") != "provisional"
                or supplemental_receipt.get("merged_sha256") != digest(args.supplement)
                or supplemental_receipt.get("detail_sha256") != digest(args.detail[0])
                or supplemental_receipt.get("kernel_sha256") != receipt["kernel_sha256"]):
            raise ValueError("solar supplement receipt does not match inputs")
        with args.supplement.open(encoding="utf-8") as stream:
            supplement_rows = [json.loads(line) for line in stream]
        if len(supplement_rows) != supplemental_receipt.get("row_count"):
            raise ValueError("solar supplement row count mismatch")
        supplements = by_key(supplement_rows, "lunation_number", "solar supplement")
        if set(supplements) != set(current):
            raise ValueError("solar supplement identities differ from discovery")
        if any(row.get("status") != "ok" for row in supplements.values()):
            raise ValueError("solar supplement contains computation errors")
    lunar_candidates = read_lunar_candidates(args.lunar_candidate_supplement, args.lunar_candidate_receipt,
        index_hash, digest(args.discovery_receipt), receipt["source_fingerprint_sha256"],
        receipt["kernel_sha256"], set(current))
    ref_rows = table(args.reference)
    if args.family == "solar":
        other = by_key(ref_rows, "lunation", "EclipseWise")
        unresolved = []
    else:
        anchors = defaultdict(list)
        for source in (current, compat, old_index, old_detail, nasa):
            for key, row in source.items():
                epoch = finite(row.get("jd_tt"))
                if epoch is not None:
                    anchors[key].append(epoch)
        other, unresolved = assign_skyfield(ref_rows, anchors)
    all_keys = sorted(set(current) | set(compat) | set(old_index) | set(old_detail) | set(nasa) | set(other) | set(details))
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("comparison output directory must be new and empty")
    counts = Counter()
    with (output / "rows.jsonl").open("x", encoding="utf-8", newline="") as stream:
        for key in all_keys:
            cur, comp, c_detail, prev, before, n, ref, detail = (s.get(key) for s in
                (current, compat, compat_detail, old_index, old_detail, nasa, other, details))
            matched = {"current": cur is not None, "baseline_index": prev is not None,
                       "baseline_detail": before is not None, "nasa": n is not None,
                       "other": ref is not None,
                       "compat": (comp is not None) if args.compat_discovery else None,
                       "compat_detail": (c_detail is not None) if args.compat_detail else None,
                       "detail": (detail is not None) if args.detail else None}
            for name, present in matched.items():
                if present is not None:
                    counts[f"{name}_present"] += int(present)
            old_type = broad_type(prev.get("eclipse_type") if prev else None, args.family)
            current_type = broad_type(cur.get("eclipse_type") if cur else None, args.family)
            nasa_type = broad_type(n.get("type") if n else None, args.family)
            ref_type = broad_type((ref.get("type") if args.family == "solar" else ref.get("skyfield_type"))
                                  if ref else None, args.family)
            compat_type = broad_type(comp.get("eclipse_type") if comp else None, args.family)
            identity_changed = (cur is None) != (prev is None)
            if identity_changed:
                counts["current_baseline_membership_difference"] += 1
            if cur and prev and current_type != old_type:
                counts["current_baseline_type_difference"] += 1
            if cur and n and current_type != nasa_type:
                counts["current_nasa_type_difference"] += 1
            if cur and ref and current_type != ref_type:
                counts["current_other_type_difference"] += 1
            if cur and n and int(cur["saros_series"]) != int(n["saros"]):
                counts["current_nasa_saros_difference"] += 1
            if args.compat_discovery and ((cur is None) != (comp is None)):
                counts["native_compat_membership_difference"] += 1
            if comp and n and compat_type != nasa_type:
                counts["compat_nasa_type_difference"] += 1
            if comp and cur and compat_type != current_type:
                counts["native_compat_type_difference"] += 1
            if comp and n and int(comp["saros_series"]) != int(n["saros"]):
                counts["compat_nasa_saros_difference"] += 1
            cur_epoch = finite(cur.get("jd_tt")) if cur else None
            epoch_offsets = {}
            for name, value in (("baseline", prev.get("jd_tt") if prev else None),
                                ("nasa", n.get("jd_tt") if n else None),
                                ("compat", comp.get("jd_tt") if comp else None),
                                ("other", ref.get("skyfield_jd_tt") if ref and args.family == "lunar" else None)):
                reference_epoch = finite(value)
                if cur_epoch is not None and reference_epoch is not None:
                    epoch_offsets[name] = (cur_epoch - reference_epoch) * 86400
            record = {"lunation_number": key, "presence": matched,
                      "broad_types": {"current": current_type, "baseline": old_type,
                                      "compat": compat_type, "nasa": nasa_type, "other": ref_type},
                      "index_changes": compare_fields(prev, cur),
                      "detail_changes": compare_fields(before, detail),
                      "epoch_offsets_tt_seconds": epoch_offsets,
                      "current_discovery": cur, "compat_discovery": comp, "baseline_index": prev,
                      "current_detail": detail, "baseline_detail": before,
                      "compat_detail": c_detail,
                      "native_to_compat_detail_differences": compare_fields(detail, c_detail),
                      "nasa": n, "other_reference": ref,
                      "solar_supplement": supplements.get(key),
                      "lunar_candidate_supplement": lunar_candidates.get(key)}
            if key in supplements:
                for product in ("hybrid", "cap"):
                    status = supplements[key].get(product + "_status")
                    if status is None:
                        raise ValueError(f"solar supplement lacks {product} status for {key}")
                    counts[f"supplement_{product}_{status}"] += 1
            for policy, candidate in lunar_candidates.get(key, {}).items():
                counts[f"lunar_candidate_{policy}_{candidate['status']}"] += 1
            stream.write(json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n")
    with (output / "unmatched_reference.jsonl").open("x", encoding="utf-8") as stream:
        for item in unresolved:
            stream.write(json.dumps(item, allow_nan=False, separators=(",", ":")) + "\n")
    if (any(digest(Path(path)) != expected for path, expected in hashes.items())
            or digest(Path(__file__)) != runner_hash):
        raise RuntimeError("one or more comparison inputs changed during execution")
    summary = {"status": "provisional", "family": args.family,
               "discovery_source_fingerprint_sha256": receipt["source_fingerprint_sha256"],
               "kernel_sha256": receipt["kernel_sha256"], "input_sha256": hashes,
               "comparison_runner_sha256": runner_hash, "counts": dict(counts),
               "rows": len(all_keys), "unmatched_or_ambiguous_reference_count": len(unresolved),
               "output_sha256": {"rows.jsonl": digest(output / "rows.jsonl"),
                                  "unmatched_reference.jsonl": digest(output / "unmatched_reference.jsonl")},
               "reference": "NASA and EclipseWise share authorship" if args.family == "solar"
                            else "Skyfield uses the same DE441 ephemeris",
               "solar_supplement_supplied": bool(args.supplement),
               "lunar_candidate_supplement_supplied": bool(args.lunar_candidate_supplement),
               "compat_discovery_supplied": bool(args.compat_discovery),
               "compat_detail_supplied": bool(args.compat_detail),
               "limits": ["Model and epoch definitions differ; residuals are not physical error bounds.",
                          "Unknown or unavailable components are not zero.",
                          "When no detailed catalog was supplied, its presence field is null, not false.",
                          "Lunar candidate classifications are model-local and are not certified event presence or absence.",
                          "Native-versus-compatibility detail differences compare distinct model policies.",
                          "Absence from a catalog is not proof of physical absence."]}
    with (output / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"family": args.family, "rows": len(all_keys), "counts": dict(counts),
                      "unmatched_or_ambiguous": len(unresolved)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
