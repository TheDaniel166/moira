import json
from pathlib import Path

from moira import _spk_body_kernel
from moira import small_body_catalog_release


class _DummyKernel:
    def __init__(self, path: Path) -> None:
        self.path = path


def _write_manifest(path: Path, *, finalized: bool) -> None:
    payload = {
        "shards": [{"path": "shard.bsp"}],
    }
    if finalized:
        payload["release"] = {"integrity": {"algorithm": "sha256"}}
    path.write_text(json.dumps(payload), encoding="utf-8")
    (path.parent / "shard.bsp").write_bytes(b"kernel")


def test_finalized_manifest_is_verified_before_kernel_open(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, finalized=True)
    events: list[str] = []

    monkeypatch.setattr(
        small_body_catalog_release,
        "verify_release",
        lambda root: events.append(f"verify:{Path(root).resolve()}"),
    )

    class _OrderedKernel(_DummyKernel):
        def __init__(self, path: Path) -> None:
            events.append(f"open:{Path(path).resolve()}")
            super().__init__(path)

    monkeypatch.setattr(_spk_body_kernel, "SmallBodyKernel", _OrderedKernel)

    readers = _spk_body_kernel.small_body_readers_from_manifest(manifest_path)

    assert len(readers) == 1
    assert events == [
        f"verify:{tmp_path.resolve()}",
        f"open:{(tmp_path / 'shard.bsp').resolve()}",
    ]


def test_legacy_manifest_does_not_claim_release_verification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, finalized=False)
    monkeypatch.setattr(
        small_body_catalog_release,
        "verify_release",
        lambda root: (_ for _ in ()).throw(
            AssertionError("legacy manifests do not carry release receipts")
        ),
    )
    monkeypatch.setattr(_spk_body_kernel, "SmallBodyKernel", _DummyKernel)

    readers = _spk_body_kernel.small_body_readers_from_manifest(manifest_path)

    assert [reader.path for reader in readers] == [
        (tmp_path / "shard.bsp").resolve()
    ]
