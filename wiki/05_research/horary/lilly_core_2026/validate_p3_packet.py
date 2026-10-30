"""Read-only integrity checks for the finite Lilly P3 source/fixture packet.

This validates structure, references and optional cached source bytes. It does
not import the engine, fetch remote data, validate astronomy or admit doctrine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit


FIXTURE_NAME = "lilly_p3_moon_considerations_2026_10_23.json"
PAGES = {107, 108, 109, 110, 112, 113, 114, 121, 122, 123, 124}
FAMILIES = {
    "voc", "early_ascendant", "late_ascendant", "via_combusta", "voc_qualification",
    "late_moon", "artist_warning", "saturn_warning", "solar_geometry",
    "hour_source_example", "lunar_orientation", "role_attribution", "testimony_balance",
}
SIGNS = {"Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"}


def require(condition: object, message: str) -> None:
    """Raise an explicit error even under optimized Python."""
    if not condition:
        raise ValueError(message)


def number(value: object, name: str) -> None:
    """Reject nonfinite and boolean numerical evidence."""
    require(type(value) in (int, float), f"{name}: finite number required")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    require(finite, f"{name}: finite number required")


def optional_truth(value: object) -> None:
    """A missing qualitative proposition is not an arbitrary truthy value."""
    require(value is None or type(value) is bool, "qualitative evidence must be bool or null")


def bounded_number(value: object, upper: int, name: str) -> None:
    """Require a continuous coordinate inside its explicitly stated interval."""
    number(value, name)
    require(0 <= value < upper, f"{name}: coordinate outside declared interval")


def validate(data: dict, cache: Path | None = None) -> dict[str, int]:
    """Validate one parsed bundle, optionally checking its acquired image bytes."""
    require(data["schema"] == "moira.research.lilly_p3_moon_considerations.v1", "P3 schema mismatch")
    for flag in ("runtime_admitted", "predictive_admitted", "complete_judgement_admitted"):
        require(data[flag] is False, f"P3 {flag} must remain false")
    require(re.fullmatch(r"[0-9a-f]{40}", data["baseline_commit"]), "invalid baseline commit")
    require(data["rights"] == "http://creativecommons.org/publicdomain/mark/1.0/", "source rights changed")
    groups = {k: data[k] for k in ("source_locations", "decisions", "source_claims", "fixtures")}
    all_ids = [r["id"] for group in groups.values() for r in group]
    require(len(all_ids) == len(set(all_ids)), "duplicate ID in P3 packet")
    require(all(isinstance(i, str) and i for i in all_ids), "nonempty string IDs required")
    sources = {r["id"]: r for r in groups["source_locations"]}
    decisions = {r["id"]: r for r in groups["decisions"]}
    require(set(decisions) == {f"{p}{i:02}" for p in ("M", "C") for i in range(1, 9)}, "decision set incomplete")
    require({(s["witness"], s["printed_page"]) for s in sources.values()}
            == {(s, p) for s in ("S01", "S02") for p in PAGES}, "source page pairs incomplete")
    require(len(sources) == 2 * len(PAGES), "duplicate source page pairs")
    hashes = 0
    cache_root = cache.resolve() if cache is not None else None
    for source in sources.values():
        uri = urlsplit(source["url"])
        require(uri.scheme == "https" and bool(uri.hostname), "HTTPS source URL required")
        require(re.fullmatch(r"[0-9a-f]{64}", source["sha256"]), "invalid source hash")
        require(type(source["bytes"]) is int and source["bytes"] > 0, "invalid source byte count")
        require(source["visual_status"] == "printed_page_and_selected_passages_checked", "uninspected source image")
        relative = Path(source["cache_path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe cache path")
        if source["witness"] == "S01":
            require(source["canvas_id"].startswith("https://iiif.wellcomecollection.org/"), "S01 canvas missing")
            require(type(source["canvas_index_zero_based"]) is int, "S01 canvas index missing")
        else:
            require(type(source["leaf_index"]) is int and isinstance(source["metadata_page_label"], str), "S02 leaf locator missing")
        if cache_root is not None:
            path = (cache_root / relative).resolve()
            require(path.is_relative_to(cache_root), "source path escapes cache")
            raw = path.read_bytes()
            require(len(raw) == source["bytes"], f"source byte count mismatch: {source['id']}")
            require(hashlib.sha256(raw).hexdigest() == source["sha256"], f"source hash mismatch: {source['id']}")
            hashes += 1
    references = 0
    for name in ("decisions", "source_claims", "fixtures"):
        for record in groups[name]:
            require(record["source_ids"] and set(record["source_ids"]) <= sources.keys(), "unknown source reference")
            require(len(record["source_ids"]) == len(set(record["source_ids"])), "duplicate source reference")
            references += len(record["source_ids"])
            if name == "decisions":
                require(record["runtime_admitted"] is False, "decision admitted at runtime")
            else:
                require(record["historical_epoch"] is None and record["predictive_admitted"] is False,
                        "historical or predictive admission changed")
    policies = data["policies"]
    require(policies["voc_default"] is None, "VOC candidate selection must remain explicit")
    require(policies["voc_variants"] == ["exact_before_ingress_candidate", "application_in_remaining_sign_candidate"], "VOC variants changed")
    require(policies["very_strong_numeric_cutoff"] is None and policies["late_moon_numeric_cutoff"] is None, "unsupported numeric cutoff")
    require(set(policies["body_universe"]) == {"Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}, "classical body universe changed")
    require(policies["directed_aspect_targets_deg"] == [0, 60, 90, 120, 180, 240, 270, 300], "directed aspect universe changed")
    require(policies["application_episode_preconditions"] == ["decreasing_target_residual", "strictly_inside_selected_moiety", "signs_behold_by_target_aspect"], "application premises changed")
    require(policies["fixture_timescale"] == "synthetic_relative_seconds", "fixture clock changed")
    for fixture in groups["fixtures"]:
        require(fixture["family"] in FAMILIES, "unknown fixture family")
        require(fixture["origin"] in {"synthetic_control", "source_proposition", "source_teaching_example"}, "fixture origin missing")
        require(fixture["complete_judgement_admitted"] is False, "fixture judgement admission changed")
        require(fixture["decision_ids"] and set(fixture["decision_ids"]) <= decisions.keys(), "unknown decision reference")
        references += len(fixture["decision_ids"])
        require(isinstance(fixture["inputs"], dict) and isinstance(fixture["expected"], dict), "fixture input/expectation objects required")
        x = fixture["inputs"]
        family = fixture["family"]
        if family in {"early_ascendant", "late_ascendant", "late_moon"}:
            bounded_number(x["degree"], 30, "degree in sign")
        if family == "early_ascendant":
            optional_truth(x["very_young"])
            optional_truth(x["description_matches"])
        elif family == "late_ascendant":
            optional_truth(x["age_corresponds"])
            optional_truth(x["certain_event_time"])
            require(x["figure_kind"] in {None, "question", "timed_event"}, "invalid figure purpose")
        elif family == "late_moon":
            require(x["sign"] in SIGNS, "invalid lunar sign")
            optional_truth(x["qualitative_late_assessment"])
        elif family == "via_combusta":
            bounded_number(x["longitude_deg"], 360, "longitude")
        elif family == "voc_qualification":
            require(x["sign"] in SIGNS and x["raw_voc"] in {"present", "absent", "not_evaluable"}, "invalid qualification inputs")
            optional_truth(x["principals_very_strong"])
            require(x["principals_very_strong"] is None or bool(x["strength_provenance"]), "strength provenance missing")
        elif family == "artist_warning":
            for key in ("matter_concerns_seventh", "cusp_afflicted", "lord_retrograde", "lord_impeded"):
                optional_truth(x[key])
        elif family == "saturn_warning":
            require(type(x["house"]) is int and 1 <= x["house"] <= 12, "invalid Saturn house")
            optional_truth(x["matter_concerns_seventh"])
            optional_truth(x["retrograde"])
        elif family == "solar_geometry":
            for key in ("sun_longitude_arcseconds", "planet_longitude_arcseconds"):
                bounded_number(x[key], 1296000, key)
        elif family == "lunar_orientation":
            bounded_number(x["moon_minus_sun_deg"], 360, "directed elongation")
        elif family == "hour_source_example":
            require(x["asserted_hour_lord"] == "Mars" and x["ascendant_sign"] in SIGNS, "hour example changed")
            require(x["calculated_hour_jd"] is x["calculated_hour_location"] is None, "fabricated hour calculation")
        if fixture["family"] != "voc":
            continue
        require(x["clock"] == "synthetic_relative_seconds", "VOC fixture clock mismatch")
        require(x["prior_separation"] is None or type(x["prior_separation"]) is bool, "invalid separation evidence")
        for key in ("exact_coverage", "application_coverage"):
            require(x[key] in {"complete", "partial", "unavailable"}, "invalid coverage state")
        for key in ("query_s", "sign_exit_s", "exit_uncertainty_s"):
            number(x[key], key)
        require(x["exit_uncertainty_s"] >= 0 and x["query_s"] < x["sign_exit_s"] - x["exit_uncertainty_s"], "invalid remaining sign interval")
        event_ids = []
        for c in x["exact_contacts"]:
            event_ids.append(c["id"])
            number(c["t_s"], "contact time")
            number(c["uncertainty_s"], "contact uncertainty")
            require(c["uncertainty_s"] >= 0, "negative contact uncertainty")
            number(c["directed_angle_deg"], "contact angle")
            require(isinstance(c["body"], str) and c["body"], "contact body missing")
        for a in x["application_intervals"]:
            event_ids.append(a["id"])
            for key in ("start_s", "end_s", "directed_angle_deg"):
                number(a[key], key)
            require(a["start_s"] < a["end_s"], "application interval must have interior")
            require(isinstance(a["body"], str) and a["body"], "application body missing")
            require(a["basis"] == "approaching_strictly_inside_selected_moiety", "application premise missing")
        require(len(event_ids) == len(set(event_ids)) and all(isinstance(i, str) and i for i in event_ids), "duplicate or empty event IDs")
    require({f["family"] for f in groups["fixtures"]} == FAMILIES, "fixture family missing")
    actual = {"source_images": len(sources), "printed_pages": len(PAGES),
              "decisions": len(decisions), "source_claims": len(groups["source_claims"]),
              "fixtures": len(groups["fixtures"]), "fixture_families": len(FAMILIES)}
    require(data["counts"] == actual, "P3 recorded counts mismatch")
    return {**actual, "references": references, "cached_hashes_verified": hashes}


def main() -> None:
    """Check the repository bundle or an explicitly supplied copy."""
    parser = argparse.ArgumentParser(description=__doc__)
    repo = Path(__file__).resolve().parents[4]
    parser.add_argument("--fixture", type=Path, default=repo / "tests/fixtures/horary" / FIXTURE_NAME)
    parser.add_argument("--cache", type=Path)
    args = parser.parse_args()
    result = validate(json.loads(args.fixture.read_text(encoding="utf-8")), args.cache)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
