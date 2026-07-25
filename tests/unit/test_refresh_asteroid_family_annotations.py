from __future__ import annotations

import json

from scripts import refresh_asteroid_family_annotations as refresh


def test_refresh_updates_json_annotations_without_touching_bsp(
    tmp_path,
    monkeypatch,
) -> None:
    targets_path = tmp_path / "unified_targets.json"
    targets_path.write_text(
        json.dumps(
            [
                {"number": 8, "family": "old"},
                {"number": 1, "family": "old"},
            ]
        ),
        encoding="utf-8",
    )
    metadata_path = tmp_path / "asteroid_shard_000.metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "records": [
                    {"number": 8, "family": "old"},
                    {"number": 1, "family": "old"},
                ]
            }
        ),
        encoding="utf-8",
    )
    bsp_path = tmp_path / "asteroid_shard_000.bsp"
    bsp_path.write_bytes(b"unaltered kernel bytes")
    receipt_path = tmp_path / "receipt.json"

    monkeypatch.setattr(
        refresh,
        "asteroid_families",
        lambda number: ["Flora", "Baptistina"] if number == 8 else [],
    )

    refresh.refresh(targets_path, tmp_path, receipt_path)

    targets = json.loads(targets_path.read_text(encoding="utf-8"))
    assert targets == [
        {"number": 8, "family": "Flora", "families": ["Flora", "Baptistina"]},
        {"number": 1, "family": None, "families": []},
    ]
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["records"] == targets
    assert bsp_path.read_bytes() == b"unaltered kernel bytes"

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["targets_with_membership"] == 1
    assert receipt["targets_without_membership"] == 1
    assert receipt["targets_with_multiple_memberships"] == 1
    assert receipt["metadata_files_updated"] == 1
    assert receipt["metadata_records_updated"] == 2
    assert receipt["bsp_files_touched"] == 0
