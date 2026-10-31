"""Check this research packet's references, counts and optional cached witnesses.

This read-only check does not validate historical interpretation or engine output.
Use the project's .venv interpreter; --cache additionally checks acquired bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


def _require(condition: object, message: object) -> None:
    if not condition:
        raise ValueError(str(message))


def validate(packet_dir: Path, cache: Path | None) -> dict[str, int]:
    data = json.loads((packet_dir / "packet.json").read_text(encoding="utf-8"))
    groups = ("sources", "source_units", "source_assets", "page_images",
              "rule_families", "ambiguities", "cases", "erection_exercises",
              "didactic_examples")
    records = {name: {r["id"]: r for r in data[name]} for name in groups}
    for name in groups:
        _require(len(records[name]) == len(data[name]), f"duplicate ID in {name}")
    all_ids = [r["id"] for name in groups for r in data[name]]
    _require(len(set(all_ids)) == len(all_ids), "IDs overlap across record groups")
    reference_groups = {"source_id": "sources", "source_unit_ids": "source_units",
                        "page_ids": "page_images", "record_page_ids": "page_images",
                        "figure_page_id": "page_images", "rule_ids": "rule_families",
                        "ambiguity_ids": "ambiguities", "shared_figure_case_id": "cases"}
    references = 0
    for name in groups:
        for record in data[name]:
            for field, target in reference_groups.items():
                value = record.get(field)
                if value is None:
                    continue
                values = value if isinstance(value, list) else [value]
                for identifier in values:
                    _require(identifier in records[target], (record["id"], field, identifier))
                    references += 1
    for rule in data["rule_families"]:
        _require(rule["executable_admitted"] is False, 'rule["executable_admitted"] is False')
        for identifier in rule["ambiguity_ids"]:
            _require(rule["id"] in records["ambiguities"][identifier]["rule_ids"], 'rule["id"] in records["ambiguities"][identifier]["rule_ids"]')
    for ambiguity in data["ambiguities"]:
        for identifier in ambiguity["rule_ids"]:
            _require(ambiguity["id"] in records["rule_families"][identifier]["ambiguity_ids"], 'ambiguity["id"] in records["rule_families"][identifier]["ambiguity_ids"]')
    states = {"resolved", "resolved_by_named_readings", "source_handling_resolved",
              "partly_resolved", "open"}
    register = (packet_dir / "RULES_AND_AMBIGUITIES.md").read_text(encoding="utf-8")
    current = register.partition("## Current state after P2-P4")[2].partition("\n## ")[0]
    for ambiguity in data["ambiguities"]:
        _require(ambiguity["current_state"] in states, (ambiguity["id"], ambiguity["current_state"]))
        _require(ambiguity["current_disposition"], (ambiguity["id"], "current_disposition"))
        residue = ambiguity["current_residue"]
        if ambiguity["current_state"] in {"open", "partly_resolved"}:
            _require(residue, (ambiguity["id"], "an open entry names its residue"))
        elif ambiguity["current_state"] in {"resolved", "source_handling_resolved"}:
            _require(residue is None, (ambiguity["id"], "a resolved entry has no residue"))
        _require(ambiguity["current_documents"], (ambiguity["id"], "current_documents"))
        for document in ambiguity["current_documents"]:
            _require((packet_dir / document).is_file(), (ambiguity["id"], document))
        _require(f"| {ambiguity['id']} | `{ambiguity['current_state']}` |" in current,
                 (ambiguity["id"], "register table matches packet.json"))
    _require(current.count("\n| A") == len(data["ambiguities"]), "register table row count")
    for case in data["cases"]:
        _require(case["normalized_epoch"] is None, 'case["normalized_epoch"] is None')
        _require(case["numeric_transcription_complete"] is False, 'case["numeric_transcription_complete"] is False')
        _require(case["reconstruction_verified"] is False, 'case["reconstruction_verified"] is False')
        _require(case["executable_admitted"] is False, 'case["executable_admitted"] is False')
        _require(case["predictive_admitted"] is False, 'case["predictive_admitted"] is False')
        _require(case["independently_verified_outcome"] is None, 'case["independently_verified_outcome"] is None')
        if not case["new_printed_figure"]:
            other = records["cases"][case["shared_figure_case_id"]]
            _require(case["figure_page_id"] == other["figure_page_id"], 'case["figure_page_id"] == other["figure_page_id"]')
    _require(data["new_executable_admission"] is False, 'data["new_executable_admission"] is False')
    _require(data["new_predictive_admission"] is False, 'data["new_predictive_admission"] is False')
    counts = data["counts"]
    _require(counts["rule_families"] == len(data["rule_families"]) == 30, 'counts["rule_families"] == len(data["rule_families"]) == 30')
    _require(counts["ambiguities"] == len(data["ambiguities"]) == 25, 'counts["ambiguities"] == len(data["ambiguities"]) == 25')
    _require(counts["book_ii_case_groups"] == len(data["cases"]) == 36, 'counts["book_ii_case_groups"] == len(data["cases"]) == 36')
    distinct = [c for c in data["cases"] if c["new_printed_figure"]]
    _require(counts["book_ii_distinct_printed_figures"] == len(distinct) == 35, 'counts["book_ii_distinct_printed_figures"] == len(distinct) == 35')
    _require(len({c["figure_page_id"] for c in distinct}) == len(distinct), 'len({c["figure_page_id"] for c in distinct}) == len(distinct)')
    _require(counts["book_i_erection_exercises"] == len(data["erection_exercises"]) == 3, 'counts["book_i_erection_exercises"] == len(data["erection_exercises"]) == 3')
    _require(counts["books_i_ii_distinct_filled_figures"] == len(distinct) + sum(
        e["new_printed_figure"] for e in data["erection_exercises"]) == 36, 'counts["books_i_ii_distinct_filled_figures"] == len(distinct) + sum(\n        e["new_printed_figure"] for e in data["erection_exercises"]) == 36')
    _require(counts["didactic_example_groups"] == len(data["didactic_examples"]) == 8, 'counts["didactic_example_groups"] == len(data["didactic_examples"]) == 8')
    _require(records["cases"]["C36"]["case_kind"] == "inception_event", 'records["cases"]["C36"]["case_kind"] == "inception_event"')
    _require(records["cases"]["C35"]["outcome_qualification"], 'records["cases"]["C35"]["outcome_qualification"]')
    _require(records["cases"]["C18"]["raw_date_variants"], 'records["cases"]["C18"]["raw_date_variants"]')
    acquisition = data["acquisition"]
    _require(not acquisition["errors"], 'not acquisition["errors"]')
    _require(acquisition["source_file_count"] == len(data["source_assets"]) == 8, 'acquisition["source_file_count"] == len(data["source_assets"]) == 8')
    _require(acquisition["selected_image_count"] == len(data["page_images"]) == 79, 'acquisition["selected_image_count"] == len(data["page_images"]) == 79')
    for page in data["page_images"]:
        _require(page["id"] == f"P{page['printed_page']:03d}", 'page["id"] == f"P{page[\'printed_page\']:03d}"')
        _require(page["canvas_index_zero_based"] >= 0, 'page["canvas_index_zero_based"] >= 0')
        _require(page["canvas_id"].startswith("https://iiif.wellcomecollection.org/"), 'page["canvas_id"].startswith("https://iiif.wellcomecollection.org/")')
        _require(page["image_url"].startswith("https://iiif.wellcomecollection.org/"), 'page["image_url"].startswith("https://iiif.wellcomecollection.org/")')
    links = 0
    for document in packet_dir.glob("*.md"):
        text = document.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in target:
                continue
            path, _, anchor = target.partition("#")
            destination = (document.parent / path).resolve() if path else document
            _require(destination.is_file(), (document.name, target))
            if anchor:
                headings = re.findall(r"^#+ (.+)$", destination.read_text(encoding="utf-8"), re.M)
                slugs = {re.sub(r"[^\w -]", "", h.lower()).replace(" ", "-") for h in headings}
                _require(anchor in slugs, (document.name, target))
            links += 1
    assets = data["source_assets"] + data["page_images"]
    verified = 0
    for asset in assets:
        _require(re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]), 're.fullmatch(r"[0-9a-f]{64}", asset["sha256"])')
        _require(asset["bytes"] > 0, 'asset["bytes"] > 0')
        if cache is not None:
            path = (cache / asset["cache_path"]).resolve()
            _require(cache.resolve() in path.parents, "cache path escaped root")
            content = path.read_bytes()
            _require(len(content) == asset["bytes"], str(path))
            _require(hashlib.sha256(content).hexdigest() == asset["sha256"], str(path))
            verified += 1
    return {"unique_ids": len(all_ids), "references": references,
            "local_markdown_links": links, "cached_hashes_verified": verified,
            **counts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, help="Optional acquisition cache root; no downloads")
    arguments = parser.parse_args()
    print(json.dumps(validate(Path(__file__).resolve().parent, arguments.cache), sort_keys=True))
