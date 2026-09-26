from __future__ import annotations

import struct
from pathlib import Path

import pytest

from moira import moira_native


def _write_type2_pck(
    path: Path,
    *,
    endian: str = "<",
    ni: int = 5,
    data_type: int = 2,
    truncate: bool = False,
) -> None:
    records = [bytearray(1024) for _ in range(6)]
    records[0][0:8] = b"DAF/PCK "
    struct.pack_into(f"{endian}I", records[0], 8, 2)
    struct.pack_into(f"{endian}I", records[0], 12, ni)
    records[0][16:76] = b"MOIRA SYNTHETIC PCK".ljust(60)
    struct.pack_into(f"{endian}I", records[0], 76, 4)
    struct.pack_into(f"{endian}I", records[0], 80, 4)
    struct.pack_into(f"{endian}I", records[0], 84, 650)
    records[0][88:96] = (b"LTL-IEEE" if endian == "<" else b"BIG-IEEE")

    struct.pack_into(f"{endian}ddd", records[3], 0, 0.0, 0.0, 1.0)
    struct.pack_into(f"{endian}dd", records[3], 24, 0.0, 86400.0)
    integers = [31008, 1, data_type, 641, 649]
    if ni == 6:
        integers.append(0)
    for index, value in enumerate(integers):
        struct.pack_into(f"{endian}i", records[3], 40 + index * 4, value)
    summary_step = 8 * (2 + (ni + 1) // 2)
    records[4][0:summary_step] = b"SYNTHETIC TYPE 2".ljust(summary_step)

    words = [43200.0, 43200.0, 0.0, 0.0, 0.0, 0.0, 86400.0, 5.0, 1.0]
    for index, value in enumerate(words):
        struct.pack_into(f"{endian}d", records[5], index * 8, value)
    payload = b"".join(records)
    path.write_bytes(payload[: 648 * 8] if truncate else payload)


@pytest.mark.parametrize("endian", ["<", ">"])
def test_synthetic_pck_decodes_ni5_for_both_daf_byte_orders(tmp_path: Path, endian: str) -> None:
    path = tmp_path / f"synthetic_{'little' if endian == '<' else 'big'}.bpc"
    _write_type2_pck(path, endian=endian)
    catalog = moira_native.read_daf_catalog(str(path))
    assert catalog["nd"] == 2
    assert catalog["ni"] == 5
    assert tuple(catalog["summaries"][0]["descriptor"]) == (
        0.0,
        86400.0,
        31008,
        1,
        2,
        641,
        649,
    )
    handle = moira_native.open_pck_kernel(str(path))
    try:
        assert handle.rotation_matrix(2451545.0) == (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        )
    finally:
        handle.close()


def test_pck_handle_rejects_spk_shaped_ni6_summary(tmp_path: Path) -> None:
    path = tmp_path / "wrong_ni.bpc"
    _write_type2_pck(path, ni=6)
    with pytest.raises(RuntimeError, match="ND=2 NI=5"):
        moira_native.open_pck_kernel(str(path))


def test_pck_handle_rejects_unsupported_segment_type(tmp_path: Path) -> None:
    path = tmp_path / "type3.bpc"
    _write_type2_pck(path, data_type=3)
    with pytest.raises(RuntimeError, match="only PCK type 2"):
        moira_native.open_pck_kernel(str(path))


def test_pck_handle_rejects_truncated_payload_on_first_evaluation(tmp_path: Path) -> None:
    path = tmp_path / "truncated.bpc"
    _write_type2_pck(path, truncate=True)
    handle = moira_native.open_pck_kernel(str(path))
    try:
        with pytest.raises(RuntimeError, match="failed to read SPK segment metadata"):
            handle.rotation_matrix(2451545.0)
    finally:
        handle.close()
