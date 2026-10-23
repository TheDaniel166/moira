"""The bounded Lilly packet must reject invalid data in optimized Python too."""
from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import sys

import pytest


PACKET = Path(__file__).resolve().parents[2] / "wiki/05_research/horary/lilly_core_2026"


@pytest.mark.parametrize("optimization", [[], ["-O"], ["-OO"]])
@pytest.mark.parametrize("damage", [None, "count", "reference", "admission"])
def test_packet_validation_cannot_be_optimized_away(tmp_path, optimization, damage):
    packet_dir = tmp_path / "packet"
    shutil.copytree(PACKET, packet_dir)
    packet_path = packet_dir / "packet.json"
    data = json.loads(packet_path.read_text(encoding="utf-8"))
    if damage == "count":
        data["counts"]["rule_families"] += 1
    elif damage == "reference":
        data["cases"][0]["figure_page_id"] = "missing-page"
    elif damage == "admission":
        data["new_predictive_admission"] = True
    packet_path.write_text(json.dumps(data), encoding="utf-8")
    script = (PACKET if damage is None else packet_dir) / "validate_packet.py"
    result = subprocess.run(
        [sys.executable, *optimization, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    if damage is None:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["unique_ids"] == 203
    else:
        assert result.returncode != 0
        assert "ValueError" in result.stderr
        assert not result.stdout


def test_research_sequence_prose_does_not_identify_kalachakra_route():
    script = PACKET.parents[3] / "scripts/generate_lightbox_calculation_inventory.py"
    spec = importlib.util.spec_from_file_location("lilly_inventory_reference_check", script)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    row = {
        "surface_id": "rest:POST:/v1/dasha/kalachakra/sequence",
        "path": "/v1/dasha/kalachakra/sequence",
        "operation_id": "kalachakra_sequence_v1",
        "handler_qualname": "kalachakra.sequence",
    }
    references = generator._route_reference_index([row], [
        ("research.md", "The event sequence determines the research sequence."),
        ("route.md", "POST /v1/dasha/kalachakra/sequence"),
        ("operation.md", "kalachakra_sequence_v1"),
    ])
    assert references[row["surface_id"]] == ["operation.md", "route.md"]
