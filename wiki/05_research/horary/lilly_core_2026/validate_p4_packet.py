"""Read-only integrity checks for the finite Lilly P4 source/fixture packet.

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


FIXTURE_NAME = "lilly_p4_perfection_routes_2026_10_30.json"
PAGES = {110, 111, 112, 113, 124, 125, 126, 127}
DECISIONS = ({f"P0{i}" for i in range(1, 10)} | {f"B0{i}" for i in range(1, 6)}
             | {f"K0{i}" for i in range(1, 8)} | {"H01", "E01", "Q01", "Q02", "T01"})
FAMILIES = {
    "conjunction", "sextile_trine", "square", "opposition", "translation", "collection",
    "prohibition", "refranation", "frustration", "reception_route", "dwelling",
    "heaviness", "continuation", "multi_route", "condition_epoch",
}
PLANETS = {"Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"}
ROUTE_STATES = {"complete", "blocked", "condition_unmet", "absent", "not_evaluable"}
WITNESS_STATES = {"present", "absent", "not_evaluable"}
COVERAGE = {"complete", "partial"}
BLOCKERS = {"prohibition_bodily", "prohibition_aspect", "refranation", "frustration"}
ASPECTS = {"conjunction", "sextile", "square", "trine", "opposition"}


def require(condition: object, message: str) -> None:
    """Raise an explicit error even under optimized Python."""
    if not condition:
        raise ValueError(message)


def number(value: object, name: str) -> None:
    """Reject nonfinite and boolean numerical evidence."""
    require(type(value) in (int, float), f"{name}: finite number required")
    require(math.isfinite(value), f"{name}: finite number required")


def truth(value: object, name: str) -> None:
    """A missing proposition is null, never an arbitrary truthy value."""
    require(value is None or type(value) is bool, f"{name}: bool or null required")


def event(value: object, name: str, *, optional: bool = False) -> None:
    """A synthetic event: identifier, relative time and nonnegative envelope."""
    if optional and value is None:
        return
    require(isinstance(value, dict) and isinstance(value.get("id"), str) and value["id"], f"{name}: event id")
    number(value["t_s"], f"{name}.t_s")
    number(value["uncertainty_s"], f"{name}.uncertainty_s")
    require(value["uncertainty_s"] >= 0, f"{name}: negative uncertainty")


def bases(value: object, name: str) -> None:
    require(value is None or (isinstance(value, list) and all(b in {"house", "exaltation", "triplicity", "term", "face"}
                                                              for b in value)), f"{name}: invalid dignity bases")


def check_inputs(family: str, x: dict) -> None:
    """Family-specific input shape; expectations are checked by the reference test."""
    if family not in {"heaviness", "reception_route", "dwelling", "multi_route", "condition_epoch", "continuation"}:
        require(x["clock"] == "synthetic_relative_seconds", "fixture clock changed")
        require(x["coverage"] in COVERAGE, "invalid coverage")
    if family in {"conjunction", "square", "opposition", "translation", "collection"}:
        for b in x["blockers"]:
            event(b, "blocker")
            require(b["kind"] in BLOCKERS, "unknown blocker kind")
    if family == "conjunction":
        event(x["contact"], "contact", optional=True)
        require(x["house_class"] in {None, "angular", "succedent", "cadent"}, "invalid house class")
        for i in x["ingresses"]:
            event(i, "ingress")
    elif family == "sextile_trine":
        event(x["contact"], "contact", optional=True)
        require(x["aspect"] in {"sextile", "trine"}, "invalid easy aspect")
        truth(x["good_houses"], "good_houses")
        truth(x["well_dignified"], "well_dignified")
        for i in x["interventions"]:
            event(i, "intervention")
            require(type(i["from_malefic"]) is bool and i["aspect"] in ASPECTS - {"conjunction"}, "invalid intervention")
    elif family == "square":
        event(x["contact"], "contact", optional=True)
        truth(x["degree_dignity"]["querent"], "querent degree dignity")
        truth(x["degree_dignity"]["quesited"], "quesited degree dignity")
        truth(x["proper_good_houses"], "proper_good_houses")
    elif family == "opposition":
        event(x["contact"], "contact", optional=True)
        for key in ("mutual_house_reception", "friendly_houses", "moon_separates_from_quesited_applies_to_ascendant_lord"):
            truth(x[key], key)
    elif family == "translation":
        require({x["translator"], x["from_principal"], x["to_principal"]} <= PLANETS, "unknown planet")
        event(x["separation_from_source"], "separation")
        event(x["second_leg"], "second leg", optional=True)
        truth(x["translator_lighter_than_both"], "translator_lighter_than_both")
        truth(x["principals_prior_separation"], "principals_prior_separation")
        bases(x["reception_bases"], "reception_bases")
        for i in x["intervening_contacts"]:
            event(i, "intervening contact")
    elif family == "collection":
        for key in ("principals_behold_by_sign", "principals_current_aspect", "collector_heavier_than_both"):
            truth(x[key], key)
        bases(x["reception_by_querent"], "reception_by_querent")
        bases(x["reception_by_quesited"], "reception_by_quesited")
        event(x["leg_querent"], "leg_querent", optional=True)
        event(x["leg_quesited"], "leg_quesited", optional=True)
        for b in x["blockers"]:
            require(b["leg"] in {"querent", "quesited"}, "collection blocker needs its leg")
    elif family == "prohibition":
        event(x["intended_contact"], "intended contact")
        require(x["third_initial_relation_to_applying"] in {None, "applying", "separating"}, "invalid initial relation")
        for c in x["third_contacts"]:
            event(c, "third contact")
            require(c["principal"] in {"applying", "heavier"} and c["mode"] in {"body", "aspect"}, "invalid third contact")
    elif family == "refranation":
        truth(x["application_established"], "application_established")
        event(x["station"], "station", optional=True)
        require(x["station"] is None or x["station"]["body_role"] in {"applying", "heavier"}, "invalid station role")
        event(x["exact_contact"], "exact contact", optional=True)
    elif family == "frustration":
        require(x["intended_aspect"] in ASPECTS, "invalid intended aspect")
        truth(x["application_established"], "application_established")
        event(x["heavier_contact_with_third"], "heavier contact", optional=True)
        require(x["heavier_contact_with_third"] is None or x["heavier_contact_with_third"]["aspect"] in ASPECTS, "invalid third aspect")
        event(x["intended_contact"], "intended contact", optional=True)
    elif family == "reception_route":
        bases(x["querent_in_quesited_dignity"], "querent dignity")
        bases(x["quesited_in_querent_dignity"], "quesited dignity")
        require(x["direct_route_status"] in ROUTE_STATES, "invalid direct route status")
    elif family == "dwelling":
        truth(x["quesited_significator_in_ascendant"], "placement")
        require(x["moon_translation_status"] in ROUTE_STATES, "invalid Moon translation status")
    elif family == "heaviness":
        require(x["body_a"] in PLANETS and x["body_b"] in PLANETS and x["body_a"] != x["body_b"], "invalid bodies")
        for key in ("abs_speed_a_deg_per_day", "abs_speed_b_deg_per_day"):
            number(x[key], key)
            require(x[key] >= 0, "absolute speed must be nonnegative")
    elif family == "continuation":
        require(x["first_window_coverage"] in COVERAGE and x["second_window_coverage"] in COVERAGE, "invalid window coverage")
        require(x["separation_window"] == 1 and x["contact_window"] in {1, 2}, "invalid window index")
        require(type(x["state_carried"]) is bool, "state_carried must be bool")
    elif family == "multi_route":
        ids = [r["id"] for r in x["routes"]]
        require(len(ids) == len(set(ids)), "duplicate route id")
        for r in x["routes"]:
            require(r["status"] in ROUTE_STATES, "invalid route status")
            require((r["status"] == "complete") == (r["completion_t_s"] is not None), "completion time only for complete routes")
    elif family == "condition_epoch":
        require(set(x["values_by_epoch"]) <= {"question", "leg_start", "contact"}, "unknown epoch")
        for v in x["values_by_epoch"].values():
            truth(v, "epoch value")
        require(x["required_epoch"] in {"question", "leg_start", "contact"}, "unknown required epoch")


def validate(data: dict, cache: Path | None = None) -> dict[str, int]:
    """Validate one parsed bundle, optionally checking its acquired image bytes."""
    require(data["schema"] == "moira.research.lilly_p4_perfection_routes.v1", "P4 schema mismatch")
    for flag in ("runtime_admitted", "predictive_admitted", "complete_judgement_admitted"):
        require(data[flag] is False, f"P4 {flag} must remain false")
    require(re.fullmatch(r"[0-9a-f]{40}", data["baseline_commit"]), "invalid baseline commit")
    require(data["rights"] == "http://creativecommons.org/publicdomain/mark/1.0/", "source rights changed")
    groups = {k: data[k] for k in ("source_locations", "decisions", "source_claims", "fixtures")}
    all_ids = [r["id"] for group in groups.values() for r in group]
    require(len(all_ids) == len(set(all_ids)), "duplicate ID in P4 packet")
    require(all(isinstance(i, str) and i for i in all_ids), "nonempty string IDs required")
    sources = {r["id"]: r for r in groups["source_locations"]}
    decisions = {r["id"]: r for r in groups["decisions"]}
    require(set(decisions) == DECISIONS, "decision set incomplete")
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
    p = data["policies"]
    for key in ("translation_default", "prohibition_default", "malevolent_intervention_default", "beholding_default",
                "heaviness_default", "route_aggregation", "timing_unit_conversion", "condition_epoch_default"):
        require(p[key] is None, f"{key} must remain unselected")
    require(p["translation_variants"] == ["p111_structural", "p126_full"], "translation readings changed")
    require(p["prohibition_variants"] == ["interposition_to_either", "successive_to_both"], "prohibition readings changed")
    require(p["heaviness_variants"] == ["traditional_order", "instantaneous_speed", "superior_inferior"], "heaviness readings changed")
    require(p["traditional_order_heaviest_first"] == ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"], "planet order changed")
    require(p["p06_reception_bases"] == ["house", "triplicity", "term"], "p.126 reception bases changed")
    require(p["ingress_policy"] == "recorded_not_blocking" and p["tie_policy"] == "envelope_overlap_unresolved", "chronology policy changed")
    require(p["fixture_timescale"] == "synthetic_relative_seconds", "fixture clock changed")
    for fixture in groups["fixtures"]:
        require(fixture["family"] in FAMILIES, "unknown fixture family")
        require(fixture["origin"] in {"synthetic_control", "source_teaching_example"}, "fixture origin missing")
        require(fixture["complete_judgement_admitted"] is False, "fixture judgement admission changed")
        require(fixture["decision_ids"] and set(fixture["decision_ids"]) <= decisions.keys(), "unknown decision reference")
        references += len(fixture["decision_ids"])
        require(isinstance(fixture["inputs"], dict) and isinstance(fixture["expected"], dict), "fixture input/expectation objects required")
        if fixture["origin"] == "source_teaching_example":
            require(fixture["inputs"].get("time_basis") == "source_asserted_ordering", "teaching example must not claim computed times")
        check_inputs(fixture["family"], fixture["inputs"])
    require({f["family"] for f in groups["fixtures"]} == FAMILIES, "fixture family missing")
    actual = {"source_images": len(sources), "printed_pages": len(PAGES),
              "decisions": len(decisions), "source_claims": len(groups["source_claims"]),
              "fixtures": len(groups["fixtures"]), "fixture_families": len(FAMILIES)}
    require(data["counts"] == actual, "P4 recorded counts mismatch")
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
