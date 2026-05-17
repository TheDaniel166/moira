"""
DAF Scribe - moira/daf_writer.py

Archetype: Scribe
Purpose: Writes JPL DAF/SPK binary files containing SPK type 13 (Hermite
         interpolation, unequal time steps) segments, enabling Moira to
         produce centaurs.bsp and minor_bodies.bsp without requiring NAIF's
         mkspk binary.

Boundary declaration
--------------------
Owns:
    - _build_file_record()    - 1024-byte DAF file record (header).
    - _build_summary_record() - 1024-byte summary record (segment index).
    - _build_name_record()    - 1024-byte name record (segment labels).
    - _build_type13_payload() - flat float64 array for one type 13 segment.
    - write_spk_type13()      - public entry point: writes a complete SPK file.
    - DAF layout constants (_RECORD_SIZE, _WORDS_PER_REC, _ND, _NI, etc.).
Delegates:
    - Nothing; all binary layout logic is self-contained using stdlib struct.

Import-time side effects: None.

External dependency assumptions:
    - stdlib struct and pathlib only; no external dependencies.
    - No Qt, no database, no OS threads.
    - The binary layout produced here is the exact inverse of the
      _Type13Segment reader in moira/asteroids.py - files written by this
      Scribe are read back transparently by that reader via jplephem.

Public surface / exports:
    write_spk_type13() - write a DAF/SPK file with type 13 segments

SPK type 13: Hermite Interpolation with Unequal Time Steps.

DAF file structure
------------------
Record 1  : File record (header)
Record 2  : Summary record  - one 40-byte entry per segment
Record 3  : Name record     - one padded name per segment
Records 4+ : Segment data   - type 13 payload, one body after another

All values are little-endian IEEE 754 floating-point (LTL-IEEE).
Word addresses (start_i, end_i, free) are 1-indexed double-precision words.
"""

from __future__ import annotations

import array as _array
import struct
import sys
import tempfile
from pathlib import Path

_BYTESWAP = sys.byteorder != "little"

_RECORD_SIZE = 1024
_WORDS_PER_REC = 128

_ND = 2
_NI = 6

_SUMMARY_BYTES = _ND * 8 + _NI * 4
_SUMMARY_STEP = ((_SUMMARY_BYTES + 7) // 8) * 8
_MAX_SUMMARIES = (_RECORD_SIZE - 24) // _SUMMARY_STEP

_T0 = 2451545.0
_S_PER_DAY = 86400.0

_FTPSTR = b"FTPSTR:\r:\n:\r\n:\r\x00:\x81:\x10\xce:ENDFTP"
assert len(_FTPSTR) == 28, "FTP string must be exactly 28 bytes"

_HEADER_RECORDS = 3
_FIRST_DATA_WORD = _HEADER_RECORDS * _WORDS_PER_REC + 1


def _build_file_record(locifn: str, fward: int, bward: int, free: int) -> bytes:
    """Build the 1024-byte DAF file record (record 1)."""
    locidw = b"DAF/SPK "
    locifn_b = locifn.encode("ascii", errors="replace")[:60].ljust(60, b"\x00")
    locfmt = b"LTL-IEEE"
    prenul = b"\x00" * 603
    pstnul = b"\x00" * 297

    packed = struct.pack(
        "<8sII60sIII8s603s28s297s",
        locidw, _ND, _NI, locifn_b,
        fward, bward, free,
        locfmt, prenul, _FTPSTR, pstnul,
    )
    assert len(packed) == _RECORD_SIZE
    return packed


def _build_summary_record(
    summaries: list[tuple[float, float, int, int, int, int, int, int]],
    next_rec: int = 0,
    prev_rec: int = 0,
) -> bytes:
    """Build a 1024-byte summary record."""
    if len(summaries) > _MAX_SUMMARIES:
        raise ValueError(
            f"Single summary record can hold at most {_MAX_SUMMARIES} segments, "
            f"got {len(summaries)}"
        )
    record = bytearray(_RECORD_SIZE)
    struct.pack_into("<ddd", record, 0, float(next_rec), float(prev_rec), float(len(summaries)))

    offset = 24
    for (start_s, end_s, center, target, frame, data_type, start_i, end_i) in summaries:
        struct.pack_into("<dd", record, offset, start_s, end_s)
        struct.pack_into(
            "<iiiiii", record, offset + 16, target, center, frame, data_type, start_i, end_i
        )
        offset += _SUMMARY_STEP

    return bytes(record)


def _build_name_record(names: list[str]) -> bytes:
    """Build a 1024-byte name record."""
    if len(names) > _MAX_SUMMARIES:
        raise ValueError(
            f"Single name record can hold at most {_MAX_SUMMARIES} names, got {len(names)}"
        )
    record = bytearray(_RECORD_SIZE)
    offset = 0
    for name in names:
        encoded = name.encode("ascii", errors="replace")[:_SUMMARY_STEP]
        encoded = encoded.ljust(_SUMMARY_STEP, b" ")
        record[offset:offset + _SUMMARY_STEP] = encoded
        offset += _SUMMARY_STEP
    return bytes(record)


def _build_type13_payload(
    states,
    epochs_jd,
    window_size: int = 7,
) -> list[float]:
    """
    Return a flat float64 array for a single type 13 segment.

    Layout (mirrors the reader in asteroids._Type13Segment):
        [0 .. 6N-1]          N state records, each (x,y,z,vx,vy,vz)
        [6N .. 7N-1]         N epochs in seconds from J2000 TDB
        [7N .. 7N+n_dir-1]   epoch directory (every 100th entry)
        [-2]                 window_size  (float)
        [-1]                 N            (float)
    """
    epochs = [float(v) for v in epochs_jd]
    count = len(epochs)
    if count == 0:
        raise ValueError("epochs_jd must contain at least one epoch")
    if window_size < 1:
        raise ValueError("window_size must be at least 1")
    if window_size % 2 == 0:
        raise ValueError("window_size must be odd for centered Hermite interpolation")
    if window_size > count:
        raise ValueError(
            f"window_size ({window_size}) cannot exceed number of epochs ({count})"
        )
    if any(epochs[idx] >= epochs[idx + 1] for idx in range(count - 1)):
        raise ValueError("epochs_jd must be strictly increasing")

    states_rows = [list(row) for row in states]
    if len(states_rows) != 6 or any(len(row) != count for row in states_rows):
        shape = (len(states_rows), len(states_rows[0]) if states_rows else 0)
        raise ValueError(f"states must be (6, {count}), got {shape}")

    states_flat: list[float] = []
    try:
        for row_idx in range(count):
            for axis in range(6):
                states_flat.append(float(states_rows[axis][row_idx]))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"states must be a numeric (6, {count}) array-like: {exc}"
        ) from exc

    epochs_sec = [(jd - _T0) * _S_PER_DAY for jd in epochs]
    directory_count = (count - 1) // 100
    directory = [
        epochs_sec[idx] for idx in range(99, 99 + 100 * directory_count, 100)
    ] if directory_count > 0 else []

    tail = [float(window_size), float(count)]
    return states_flat + epochs_sec + directory + tail


def write_spk_type13(
    path: Path | str,
    bodies: list[dict],
    locifn: str = "MOIRA CENTAUR KERNEL",
) -> None:
    """
    Write a DAF/SPK file containing one type 13 Hermite segment per body.

    Parameters
    ----------
    path   : output .bsp file path
    bodies : list of dicts, each containing:
                 naif_id    int      NAIF ID  (e.g. 2002060 for Chiron)
                 states     (6,N)   km / km*s^-1 - rows: x,y,z,vx,vy,vz
                 epochs_jd  (N,)   Julian dates TDB
                 center     int      reference body (default 10 = Sun)
                 name       str      human label for the name record
                 window_size int     Hermite window points (default 7)
    locifn : up to 60-char internal file identifier
    """
    path = Path(path)
    if len(bodies) > _MAX_SUMMARIES:
        raise ValueError(
            f"write_spk_type13() currently supports at most {_MAX_SUMMARIES} bodies "
            "because it emits a single summary record and a single name record"
        )

    for i, body in enumerate(bodies):
        for key in ("naif_id", "states", "epochs_jd"):
            if key not in body:
                raise ValueError(f"bodies[{i}] is missing required key {key!r}")

    summaries: list[tuple] = []
    names: list[str] = []
    payloads: list[bytes] = []
    current_word = _FIRST_DATA_WORD

    for body in bodies:
        naif_id = int(body["naif_id"])
        center = int(body.get("center", 10))
        frame = int(body.get("frame", 1))
        name = str(body.get("name", f"NAIF-{naif_id}"))
        states = body["states"]
        epochs_jd = body["epochs_jd"]
        window_size = int(body.get("window_size", 7))

        data = _build_type13_payload(states, epochs_jd, window_size)
        n_words = len(data)
        start_i = current_word
        end_i = current_word + n_words - 1

        start_s = float((float(epochs_jd[0]) - _T0) * _S_PER_DAY)
        end_s = float((float(epochs_jd[-1]) - _T0) * _S_PER_DAY)

        summaries.append((start_s, end_s, center, naif_id, frame, 13, start_i, end_i))
        names.append(name)

        buffer = _array.array("d", data)
        if _BYTESWAP:
            buffer.byteswap()
        payloads.append(buffer.tobytes())

        current_word += n_words

    free = current_word

    file_rec = _build_file_record(locifn, fward=2, bward=2, free=free)
    summary_rec = _build_summary_record(summaries)
    name_rec = _build_name_record(names)

    segment_bytes = b"".join(payloads)
    remainder = len(segment_bytes) % _RECORD_SIZE
    if remainder:
        segment_bytes += b"\x00" * (_RECORD_SIZE - remainder)

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.stem}.",
            suffix=path.suffix,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(file_rec)
            handle.write(summary_rec)
            handle.write(name_rec)
            handle.write(segment_bytes)
        temp_path.replace(path)
    except Exception:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
        raise
