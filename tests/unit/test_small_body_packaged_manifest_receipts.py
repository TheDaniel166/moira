"""Immutable receipt gates for wheel-packaged small-body manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_website_docs_bundle import _catalog_metrics


_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    (
        "manifest_relative",
        "identity_relative",
        "expected_catalog_id",
        "expected_version",
        "expected_body_count",
        "expected_shard_count",
        "expected_sampling",
    ),
    [
        (
            "moira/kernels/asteroids/manifest.json",
            "moira/data/asteroid_catalog_naif.metadata.json",
            "moira-asteroids",
            "2026.07.27.1",
            9_974,
            399,
            {"step_days": 10, "window_size": 7},
        ),
        (
            "moira/kernels/comets/manifest.json",
            "moira/data/comet_catalog_naif.metadata.json",
            "moira-comets",
            "2026.07.28.1",
            497,
            20,
            {"step_days": 30, "window_size": 5},
        ),
    ],
)
def test_packaged_manifest_matches_immutable_identity_receipt(
    manifest_relative: str,
    identity_relative: str,
    expected_catalog_id: str,
    expected_version: str,
    expected_body_count: int,
    expected_shard_count: int,
    expected_sampling: dict[str, int],
) -> None:
    manifest_path = _ROOT / manifest_relative
    identity_path = _ROOT / identity_relative
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    identity = json.loads(identity_path.read_bytes())

    assert hashlib.sha256(manifest_bytes).hexdigest() == (
        identity["source"]["release_manifest_sha256"]
    )
    assert manifest["catalog_id"] == identity["catalog_id"] == expected_catalog_id
    assert (
        manifest["catalog_version"]
        == identity["catalog_version"]
        == expected_version
    )
    assert manifest["body_count"] == expected_body_count
    assert manifest["shard_count"] == expected_shard_count
    assert manifest["sampling"] == expected_sampling
    assert manifest["release"]["released_utc"] == identity["source"]["released_utc"]
    assert manifest["release"]["source_revision"] == (
        identity["source"]["release_source_revision"]
    )
    assert manifest["release"]["integrity"] == {
        "algorithm": "sha256",
        "receipt": "SHA256SUMS",
        "receipt_scope": (
            "manifest, kernels, per-shard metadata, and included support files; "
            "the receipt itself is excluded"
        ),
    }

    shards = manifest["shards"]
    assert len(shards) == expected_shard_count
    assert sum(shard["body_count"] for shard in shards) == expected_body_count
    bodies = [body for shard in shards for body in shard["bodies"]]
    assert len(bodies) == len(set(bodies)) == expected_body_count
    assert all(shard["bytes"] > 0 for shard in shards)
    assert all(len(shard["sha256"]) == 64 for shard in shards)
    assert all(shard["metadata"]["bytes"] > 0 for shard in shards)
    assert all(len(shard["metadata"]["sha256"]) == 64 for shard in shards)


def test_website_catalog_metrics_publish_release_identity() -> None:
    metrics = _catalog_metrics()

    asteroid = metrics["position_capable_asteroid_ephemeris"]
    assert asteroid["catalog_version"] == "2026.07.27.1"
    assert asteroid["body_count"] == 9_974
    assert asteroid["shard_count"] == 399
    assert asteroid["sampling"] == {"step_days": 10, "window_size": 7}
    assert asteroid["manifest_sha256"] == (
        "0560302f877a46cebc550376ae70665fefab84801078181cf3c4199ce86d49d0"
    )

    comet = metrics["position_capable_periodic_comet_ephemeris"]
    assert comet["catalog_version"] == "2026.07.28.1"
    assert comet["body_count"] == 497
    assert comet["shard_count"] == 20
    assert comet["sampling"] == {"step_days": 30, "window_size": 5}
    assert comet["manifest_sha256"] == (
        "31fbbedbb3ea7ba276fa9d49d52211ae41d90f76c74fb49ec0a6bafb014f07a1"
    )
