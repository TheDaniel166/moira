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


def validate(packet_dir: Path, cache: Path | None) -> dict[str, int]:
    data = json.loads((packet_dir / "packet.json").read_text(encoding="utf-8"))
    groups = ("sources", "source_units", "source_assets", "page_images",
              "rule_families", "ambiguities", "cases", "erection_exercises",
              "didactic_examples")
    records = {name: {r["id"]: r for r in data[name]} for name in groups}
    for name in groups:
        assert len(records[name]) == len(data[name]), f"duplicate ID in {name}"
    all_ids = [r["id"] for name in groups for r in data[name]]
    assert len(set(all_ids)) == len(all_ids), "IDs overlap across record groups"
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
                    assert identifier in records[target], (record["id"], field, identifier)
                    references += 1
    for rule in data["rule_families"]:
        assert rule["executable_admitted"] is False
        for identifier in rule["ambiguity_ids"]:
            assert rule["id"] in records["ambiguities"][identifier]["rule_ids"]
    for ambiguity in data["ambiguities"]:
        for identifier in ambiguity["rule_ids"]:
            assert ambiguity["id"] in records["rule_families"][identifier]["ambiguity_ids"]
    for case in data["cases"]:
        assert case["normalized_epoch"] is None
        assert case["numeric_transcription_complete"] is False
        assert case["reconstruction_verified"] is False
        assert case["executable_admitted"] is False
        assert case["predictive_admitted"] is False
        assert case["independently_verified_outcome"] is None
        if not case["new_printed_figure"]:
            other = records["cases"][case["shared_figure_case_id"]]
            assert case["figure_page_id"] == other["figure_page_id"]
    assert data["new_executable_admission"] is False
    assert data["new_predictive_admission"] is False
    counts = data["counts"]
    assert counts["rule_families"] == len(data["rule_families"]) == 30
    assert counts["ambiguities"] == len(data["ambiguities"]) == 25
    assert counts["book_ii_case_groups"] == len(data["cases"]) == 36
    distinct = [c for c in data["cases"] if c["new_printed_figure"]]
    assert counts["book_ii_distinct_printed_figures"] == len(distinct) == 35
    assert len({c["figure_page_id"] for c in distinct}) == len(distinct)
    assert counts["book_i_erection_exercises"] == len(data["erection_exercises"]) == 3
    assert counts["books_i_ii_distinct_filled_figures"] == len(distinct) + sum(
        e["new_printed_figure"] for e in data["erection_exercises"]) == 36
    assert counts["didactic_example_groups"] == len(data["didactic_examples"]) == 8
    assert records["cases"]["C36"]["case_kind"] == "inception_event"
    assert records["cases"]["C35"]["outcome_qualification"]
    assert records["cases"]["C18"]["raw_date_variants"]
    acquisition = data["acquisition"]
    assert not acquisition["errors"]
    assert acquisition["source_file_count"] == len(data["source_assets"]) == 8
    assert acquisition["selected_image_count"] == len(data["page_images"]) == 79
    for page in data["page_images"]:
        assert page["id"] == f"P{page['printed_page']:03d}"
        assert page["canvas_index_zero_based"] >= 0
        assert page["canvas_id"].startswith("https://iiif.wellcomecollection.org/")
        assert page["image_url"].startswith("https://iiif.wellcomecollection.org/")
    links = 0
    for document in packet_dir.glob("*.md"):
        text = document.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in target:
                continue
            path, _, anchor = target.partition("#")
            destination = (document.parent / path).resolve() if path else document
            assert destination.is_file(), (document.name, target)
            if anchor:
                headings = re.findall(r"^#+ (.+)$", destination.read_text(encoding="utf-8"), re.M)
                slugs = {re.sub(r"[^\w -]", "", h.lower()).replace(" ", "-") for h in headings}
                assert anchor in slugs, (document.name, target)
            links += 1
    assets = data["source_assets"] + data["page_images"]
    verified = 0
    for asset in assets:
        assert re.fullmatch(r"[0-9a-f]{64}", asset["sha256"])
        assert asset["bytes"] > 0
        if cache is not None:
            path = (cache / asset["cache_path"]).resolve()
            assert cache.resolve() in path.parents, "cache path escaped root"
            content = path.read_bytes()
            assert len(content) == asset["bytes"], str(path)
            assert hashlib.sha256(content).hexdigest() == asset["sha256"], str(path)
            verified += 1
    return {"unique_ids": len(all_ids), "references": references,
            "local_markdown_links": links, "cached_hashes_verified": verified,
            **counts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, help="Optional acquisition cache root; no downloads")
    arguments = parser.parse_args()
    print(json.dumps(validate(Path(__file__).resolve().parent, arguments.cache), sort_keys=True))
