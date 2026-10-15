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
            "2026.10.10.1",
            11_223,
            449,
            {
                "base_step_days": 10,
                "window_size": 7,
                "policy_version": "moira-small-body-type13-apsidal-adaptive-v4",
                "minimum_refinement_step_days": 0.0625,
                "adaptive_body_count": 59,
            },
        ),
        (
            "moira/kernels/comets/manifest.json",
            "moira/data/comet_catalog_naif.metadata.json",
            "moira-comets",
            "2026.10.10.1",
            497,
            20,
            {
                "base_step_days": 10,
                "window_size": 7,
                "policy_version": "moira-comet-type13-apsidal-adaptive-v5",
                "minimum_refinement_step_days": 0.0078125,
            },
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
    expected_sampling: dict[str, int | float | str],
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
    sampling = manifest["sampling"]
    assert {key: sampling[key] for key in expected_sampling} == expected_sampling
    assert sampling["mode"] == "certified_adaptive_radial_extrema"
    assert sampling["initial_refinement_step_days"] == 1.0
    assert sampling["time_tags"] == "nonuniform"
    assert sampling["certification"] == {
        "witness_step_ratio": 0.5,
        "distance_absolute_km": 0.1495978707,
        "event_time_absolute_seconds": 8.64,
        "failure_action": "halve_refinement_step_or_reject_body",
    }
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
    assert asteroid["catalog_version"] == "2026.10.10.1"
    assert asteroid["body_count"] == 11_223
    assert asteroid["shard_count"] == 449
    assert asteroid["sampling"]["base_step_days"] == 10
    assert asteroid["sampling"]["window_size"] == 7
    assert asteroid["sampling"]["adaptive_body_count"] == 59
    assert asteroid["manifest_sha256"] == (
        "3d6ef5dee648dad240ef9db4dfcc460a3ecbf0f1cb4b103d1d99f1056878319d"
    )

    comet = metrics["position_capable_periodic_comet_ephemeris"]
    assert comet["catalog_version"] == "2026.10.10.1"
    assert comet["body_count"] == 497
    assert comet["shard_count"] == 20
    assert comet["sampling"]["base_step_days"] == 10
    assert comet["sampling"]["window_size"] == 7
    assert comet["sampling"]["minimum_refinement_step_days"] == 0.0078125
    assert comet["manifest_sha256"] == (
        "2c147176c66ea1b3c007bb779357c6afcc23ace6fbe9cc18ce169980b3198671"
    )
