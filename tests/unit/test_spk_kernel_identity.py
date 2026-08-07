"""Content-derived planetary SPK identity and structural admission tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from moira import spk_reader


def _catalog(
    *labels: str,
    locidw: str = "DAF/SPK",
    descriptor: tuple = (0.0, 86400.0, 10, 0, 1, 2, 100, 200),
) -> dict:
    return {
        "locidw": locidw,
        "locfmt": "LTL-IEEE",
        "nd": 2,
        "ni": 6,
        "little_endian": True,
        "summaries": [
            {"name": label.encode("ascii"), "descriptor": descriptor}
            for label in labels
        ],
    }


class _FakeKernel:
    def __init__(self, catalog: dict) -> None:
        self.catalog = catalog
        self.segments = [SimpleNamespace(center=0, target=10)]
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _open_reader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    filename: str,
    catalog: dict,
) -> spk_reader.SpkReader:
    path = tmp_path / filename
    path.write_bytes(b"synthetic catalog holder")
    kernel = _FakeKernel(catalog)
    monkeypatch.setattr(spk_reader, "_open_kernel", lambda _path: kernel)
    return spk_reader.SpkReader(path)


@pytest.mark.parametrize(
    ("filename", "label", "planetary", "lunar", "tidal_acceleration"),
    (
        ("renamed-kernel.bsp", "DE-0441LE-0441", "DE441", "LE441", -25.936),
        ("de440.bsp", "DE-0440LE-0440", "DE440", "LE440", -25.936),
        ("de441.bsp", "DE-0430LE-0430", "DE430", "LE430", -25.85),
    ),
)
@pytest.mark.validation_contract("MOIRA-SPK-CONTENT-IDENTITY-V1")
@pytest.mark.parallel(reason="isolated_resources")
def test_spk_reader_identity_comes_from_summary_content_not_filename(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    filename: str,
    label: str,
    planetary: str,
    lunar: str,
    tidal_acceleration: float,
) -> None:
    reader = _open_reader(monkeypatch, tmp_path, filename, _catalog(label))
    try:
        identity = reader._kernel_identity
        assert identity.summary_label == label
        assert identity.planetary_ephemeris == planetary
        assert identity.lunar_ephemeris == lunar
        assert (
            identity.lunar_tidal_acceleration_arcsec_per_cy2
            == tidal_acceleration
        )
        with pytest.raises(FrozenInstanceError):
            identity.summary_label = "DE-9999LE-9999"
    finally:
        reader.close()


def test_coherent_unmapped_de_le_identity_remains_representable() -> None:
    identity = spk_reader._ephemeris_kernel_identity_from_catalog(
        _catalog("DE-0431LE-0431")
    )

    assert identity.summary_label == "DE-0431LE-0431"
    assert identity.planetary_ephemeris == "DE431"
    assert identity.lunar_ephemeris == "LE431"
    assert identity.lunar_tidal_acceleration_arcsec_per_cy2 is None


def test_unrecognized_coherent_summary_label_remains_unknown() -> None:
    identity = spk_reader._ephemeris_kernel_identity_from_catalog(
        _catalog("CUSTOM PLANETARY KERNEL")
    )

    assert identity.summary_label == "CUSTOM PLANETARY KERNEL"
    assert identity.planetary_ephemeris is None
    assert identity.lunar_ephemeris is None
    assert identity.lunar_tidal_acceleration_arcsec_per_cy2 is None


@pytest.mark.validation_contract("MOIRA-SPK-CONTENT-IDENTITY-V1")
@pytest.mark.parallel(reason="isolated_resources")
def test_mixed_summary_identities_fail_closed_and_release_kernel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "mixed-labels.bsp"
    path.write_bytes(b"synthetic catalog holder")
    kernel = _FakeKernel(_catalog("DE-0441LE-0441", "DE-0430LE-0430"))
    monkeypatch.setattr(spk_reader, "_open_kernel", lambda _path: kernel)

    with pytest.raises(ValueError, match="mixed ephemeris identity labels"):
        spk_reader.SpkReader(path)
    assert kernel.closed


def test_empty_catalog_is_not_vacuously_native_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_DAF", True)
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_SEGMENTS", True)

    assert not spk_reader._planetary_kernel_native_supported(_catalog())


def test_non_spk_catalog_is_not_native_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_DAF", True)
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_SEGMENTS", True)

    assert not spk_reader._planetary_kernel_native_supported(
        _catalog("DE-0441LE-0441", locidw="DAF/PCK")
    )


@pytest.mark.parametrize(
    "descriptor",
    (
        (0.0, 86400.0, 10, 0, 1, 2, 100),
        (0.0, 86400.0, 10, 0, 1, 13, 100, 200),
    ),
)
def test_malformed_or_unsupported_descriptor_is_not_native_supported(
    monkeypatch: pytest.MonkeyPatch,
    descriptor: tuple,
) -> None:
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_DAF", True)
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_SEGMENTS", True)

    assert not spk_reader._planetary_kernel_native_supported(
        _catalog("DE-0441LE-0441", descriptor=descriptor)
    )


def test_kernel_pool_resolves_content_identified_primary_without_path_guessing() -> None:
    identity = spk_reader._ephemeris_kernel_identity_from_catalog(
        _catalog("DE-0441LE-0441")
    )
    supplemental_identity = spk_reader._ephemeris_kernel_identity_from_catalog(
        _catalog("CERES SUPPLEMENT")
    )
    filename_spoof = SimpleNamespace(path=Path("de441.bsp"))
    supplemental = SimpleNamespace(
        path=Path("small-bodies.bsp"),
        _kernel_identity=supplemental_identity,
    )
    primary = SimpleNamespace(
        path=Path("renamed-kernel.bsp"),
        _kernel_identity=identity,
    )
    pool = spk_reader.KernelPool((filename_spoof, supplemental, primary))

    assert pool._primary_planetary_reader() is primary
    assert pool._kernel_identity is identity
