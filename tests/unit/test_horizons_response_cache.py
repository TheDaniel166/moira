from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from scripts.horizons_response_cache import cached_text_response


def test_response_cache_fetches_once_and_reuses_exact_identity(tmp_path: Path) -> None:
    calls = 0

    def fetch() -> str:
        nonlocal calls
        calls += 1
        return "Horizons response"

    first, first_cached = cached_text_response(
        tmp_path,
        namespace="vectors",
        request_identity={"command": "3200;", "epochs": [1.0, 2.0]},
        fetch=fetch,
    )
    second, second_cached = cached_text_response(
        tmp_path,
        namespace="vectors",
        request_identity={"command": "3200;", "epochs": [1.0, 2.0]},
        fetch=fetch,
    )

    assert first == second == "Horizons response"
    assert first_cached is False
    assert second_cached is True
    assert calls == 1


def test_response_cache_rejects_tampering(tmp_path: Path) -> None:
    cached_text_response(
        tmp_path,
        namespace="vectors",
        request_identity={"command": "1P"},
        fetch=lambda: "original",
    )
    path = next(tmp_path.rglob("*.json.gz"))
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["response"] = "tampered"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle)

    with pytest.raises(RuntimeError, match="response hash mismatch"):
        cached_text_response(
            tmp_path,
            namespace="vectors",
            request_identity={"command": "1P"},
            fetch=lambda: "unused",
        )
