"""Atomic, content-addressed cache for external Horizons builder responses."""

from __future__ import annotations

from collections.abc import Callable
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any


def cached_text_response(
    cache_dir: Path | None,
    *,
    namespace: str,
    request_identity: dict[str, Any],
    fetch: Callable[[], str],
) -> tuple[str, bool]:
    """Return a response and whether it came from a validated cache entry."""

    if cache_dir is None:
        return fetch(), False
    identity = {
        "namespace": namespace,
        "request": request_identity,
    }
    encoded_identity = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded_identity).hexdigest()
    directory = cache_dir / namespace
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest}.json.gz"
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("request_identity_sha256") != digest:
            raise RuntimeError(f"Horizons cache identity mismatch: {path}")
        raw = str(payload["response"])
        if hashlib.sha256(raw.encode("utf-8")).hexdigest() != payload.get(
            "response_sha256"
        ):
            raise RuntimeError(f"Horizons cache response hash mismatch: {path}")
        return raw, True

    raw = fetch()
    payload = {
        "request_identity_sha256": digest,
        "request_identity": identity,
        "response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "response": raw,
    }
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=directory,
            prefix=f".{digest}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        with gzip.open(temporary, "wt", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"))
        temporary.replace(path)
    except Exception:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        raise
    return raw, False
