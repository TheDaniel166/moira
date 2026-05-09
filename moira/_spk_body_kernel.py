"""
Native-owned small-body SPK reader infrastructure.

This module provides:
    - _Type13Segment: SPK type 13 (Hermite) segment reader
    - SmallBodyKernel: thin wrapper around a native DAF/SPK segment catalog

The public surface intentionally preserves the existing shape used by
``moira.asteroids`` and ``moira.comets`` while removing mandatory runtime
dependence on ``jplephem``.
"""

from __future__ import annotations

from bisect import bisect_left
from pathlib import Path

from .coordinates import Vec3
from .spk_reader import (
    _coeff_record,
    _coeff_tensor_shape,
    _eval_chebyshev_record_scalar,
    _eval_chebyshev_record_with_derivative_scalar,
)

try:
    from . import moira_native as _moira_native
except ImportError:  # pragma: no cover
    _moira_native = None

T0 = 2451545.0
S_PER_DAY = 86400.0


def _jd(seconds: float) -> float:
    return T0 + seconds / S_PER_DAY


def compute_calendar_date(jd_integer: float, julian_before=None):
    jd_integer = int(jd_integer)
    use_gregorian = (julian_before is None) or (jd_integer >= julian_before)
    f = jd_integer + 1401
    f += use_gregorian * ((4 * jd_integer + 274277) // 146097 * 3 // 4 - 38)
    e = 4 * f + 3
    g = e % 1461 // 4
    h = 5 * g + 2
    day = h % 153 // 5 + 1
    month = (h // 153 + 2) % 12 + 1
    year = e // 1461 - 4716 + (12 + 2 - month) // 12
    return year, month, day


class OutOfRangeError(ValueError):
    def __init__(self, message, out_of_range_times):
        self.args = (message,)
        self.out_of_range_times = out_of_range_times


_HAS_NATIVE_DAF = _moira_native is not None and hasattr(_moira_native, "read_daf_catalog")
_HAS_NATIVE_SEGMENTS = (
    _moira_native is not None
    and hasattr(_moira_native, "read_spk_chebyshev_segment_payload")
)
_HAS_NATIVE_TYPE13 = _moira_native is not None and hasattr(
    _moira_native, "read_spk_type13_segment_payload"
)


def _hermite_eval_3d(
    t: float,
    ti: list[float],
    pos: list[list[float]],
    vel: list[list[float]],
) -> tuple[float, float, float]:
    """Hermite divided-difference interpolation in R^3."""
    n = len(pos[0])
    m = 2 * n

    z = [0.0] * m
    for i, value in enumerate(ti):
        z[2 * i] = value
        z[2 * i + 1] = value

    prev = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        for i in range(n):
            prev[axis][2 * i] = pos[axis][i]
            prev[axis][2 * i + 1] = pos[axis][i]

    coeffs = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        coeffs[axis][0] = prev[axis][0]

    curr = [[0.0] * (m - 1) for _ in range(3)]
    for i in range(m - 1):
        if i % 2 == 0:
            for axis in range(3):
                curr[axis][i] = vel[axis][i // 2]
        else:
            denom = z[i + 1] - z[i]
            for axis in range(3):
                curr[axis][i] = (prev[axis][i + 1] - prev[axis][i]) / denom
    for axis in range(3):
        coeffs[axis][1] = curr[axis][0]
    prev = curr

    for j in range(2, m):
        curr = [[0.0] * (m - j) for _ in range(3)]
        for i in range(m - j):
            denom = z[i + j] - z[i]
            for axis in range(3):
                curr[axis][i] = (prev[axis][i + 1] - prev[axis][i]) / denom
        for axis in range(3):
            coeffs[axis][j] = curr[axis][0]
        prev = curr

    result = [coeffs[axis][m - 1] for axis in range(3)]
    for j in range(m - 2, -1, -1):
        delta = t - z[j]
        for axis in range(3):
            result[axis] = coeffs[axis][j] + delta * result[axis]

    return (result[0], result[1], result[2])


class _NativeKernelHandle:
    def __init__(self, segments) -> None:
        self.segments = list(segments)

    def close(self) -> None:
        for segment in self.segments:
            if hasattr(segment, "_release"):
                segment._release()


class _NativeChebyshevSegment:
    """Native-backed type-2/type-3 SPK segment used by ``sb441-n373s.bsp``."""

    def __init__(self, path: Path, source: bytes, descriptor, little_endian: bool) -> None:
        self.path = path
        self.source = source
        self._little_endian = bool(little_endian)
        (
            self.start_second,
            self.end_second,
            self.target,
            self.center,
            self.frame,
            self.data_type,
            self.start_i,
            self.end_i,
        ) = descriptor
        self.start_jd = _jd(self.start_second)
        self.end_jd = _jd(self.end_second)
        self._data = None

    def _release(self) -> None:
        self._data = None

    def _load_data(self):
        if self._data is None:
            payload = _moira_native.read_spk_chebyshev_segment_payload(
                str(self.path),
                int(self.start_i),
                int(self.end_i),
                self._little_endian,
                int(self.data_type),
            )
            self._data = (
                float(payload["init"]),
                float(payload["intlen"]),
                payload["coefficients"],
            )
        return self._data

    def _evaluate(self, tdb: float, tdb2: float, need_rates: bool):
        init, intlen, coefficients = self._load_data()
        record_count, component_count, coefficient_count = _coeff_tensor_shape(coefficients)

        index1, offset1 = divmod((tdb - T0) * S_PER_DAY - init, intlen)
        index2, offset2 = divmod(tdb2 * S_PER_DAY, intlen)
        index3, offset = divmod(offset1 + offset2, intlen)
        index = int(index1 + index2 + index3)
        if index < 0 or index > record_count:
            raise OutOfRangeError(
                "segment only covers dates %d-%02d-%02d through %d-%02d-%02d"
                % (
                    compute_calendar_date(self.start_jd + 0.5)
                    + compute_calendar_date(self.end_jd + 0.5)
                ),
                out_of_range_times=True,
            )
        if index == record_count:
            index -= 1
            offset += intlen

        coeff_record = _coeff_record(coefficients, index)
        s = 2.0 * offset / intlen - 1.0
        derivative_scale = 2.0 * S_PER_DAY / intlen

        if need_rates:
            values, rates = _eval_chebyshev_record_with_derivative_scalar(
                coeff_record, s, derivative_scale
            )
            return values, rates

        values = _eval_chebyshev_record_scalar(coeff_record, s)
        return values, None

    def compute(self, tdb, tdb2=0.0):
        values, _rates = self._evaluate(float(tdb), float(tdb2), need_rates=False)
        return (float(values[0]), float(values[1]), float(values[2]))

    def compute_and_differentiate(self, tdb, tdb2=0.0):
        values, rates = self._evaluate(float(tdb), float(tdb2), need_rates=True)
        return (
            (float(values[0]), float(values[1]), float(values[2])),
            (float(rates[0]), float(rates[1]), float(rates[2])),
        )


class _Type13Segment:
    """Moira-native SPK type 13 segment object."""

    def __init__(self, path: Path, source: bytes, descriptor, little_endian: bool) -> None:
        self.path = path
        self.source = source
        self._little_endian = bool(little_endian)
        (
            self.start_second,
            self.end_second,
            self.target,
            self.center,
            self.frame,
            self.data_type,
            self.start_i,
            self.end_i,
        ) = descriptor
        self.start_jd = _jd(self.start_second)
        self.end_jd = _jd(self.end_second)
        self.__data = None

    def _release(self) -> None:
        self.__data = None

    @property
    def _data(self):
        if self.__data is None:
            payload = _moira_native.read_spk_type13_segment_payload(
                str(self.path),
                int(self.start_i),
                int(self.end_i),
                self._little_endian,
            )
            states = [list(axis) for axis in payload["states"]]
            epochs_jd = list(payload["epochs_jd"])
            self.__data = (states, epochs_jd, int(payload["window_size"]))
        return self.__data

    def compute(self, tdb, tdb2=0.0):
        states, epochs_jd, ws = self._data
        t = float(tdb) + float(tdb2)

        idx = bisect_left(epochs_jd, t)
        half = ws // 2
        start = max(0, min(idx - half, len(epochs_jd) - ws))

        win_jd = epochs_jd[start:start + ws]
        win_t = [(jd - T0) * S_PER_DAY for jd in win_jd]
        t_sec = (t - T0) * S_PER_DAY

        pos = [axis[start:start + ws] for axis in states[:3]]
        vel = [axis[start:start + ws] for axis in states[3:]]

        return _hermite_eval_3d(t_sec, win_t, pos, vel)

    def compute_and_differentiate(self, tdb, tdb2=0.0):
        dt = 1.0
        p0 = self.compute(tdb - dt * 0.5, tdb2)
        p1 = self.compute(tdb + dt * 0.5, tdb2)
        pos = self.compute(tdb, tdb2)
        vel = tuple((b - a) / dt for a, b in zip(p0, p1))
        return pos, vel


def _native_catalog_is_fully_supported(catalog: dict) -> bool:
    if not _HAS_NATIVE_DAF:
        return False
    for item in catalog["summaries"]:
        data_type = int(item["descriptor"][5])
        if data_type == 13:
            if not _HAS_NATIVE_TYPE13:
                return False
        elif data_type in (2, 3):
            if not _HAS_NATIVE_SEGMENTS:
                return False
        else:
            return False
    return True


def _native_segment_for(path: Path, descriptor, source: bytes, little_endian: bool):
    data_type = int(descriptor[5])
    if data_type == 13:
        return _Type13Segment(path, source, descriptor, little_endian)
    if data_type in (2, 3):
        return _NativeChebyshevSegment(path, source, descriptor, little_endian)
    raise RuntimeError(f"unsupported small-body SPK segment type {data_type}")


class SmallBodyKernel:
    """Thin wrapper around a native-owned SPK small-body kernel."""

    def __init__(self, path: Path) -> None:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"SPK kernel not found at {path}")
        if not _HAS_NATIVE_DAF:
            raise ImportError(
                "Moira small-body kernels require the native extension module."
            )

        catalog = _moira_native.read_daf_catalog(str(path))
        if not _native_catalog_is_fully_supported(catalog):
            unsupported = sorted(
                {int(item["descriptor"][5]) for item in catalog["summaries"]}
                - {2, 3, 13}
            )
            raise RuntimeError(
                "SmallBodyKernel only supports native SPK segment types 2, 3, and 13; "
                f"found unsupported types {unsupported!r} in {path.name}"
            )

        self._path = path
        self._catalog = catalog
        self._kernel = _NativeKernelHandle(
            [
                _native_segment_for(path, item["descriptor"], item["name"], catalog["little_endian"])
                for item in catalog["summaries"]
            ]
        )

        self._available: set[int] = set()
        self._center: dict[int, int] = {}
        for seg in self._kernel.segments:
            self._available.add(seg.target)
            self._center.setdefault(seg.target, seg.center)

    def has_body(self, naif_id: int) -> bool:
        return naif_id in self._available

    def segment_center(self, naif_id: int) -> int:
        return self._center.get(naif_id, 0)

    def position(self, naif_id: int, jd_tt: float) -> Vec3:
        for seg in self._kernel.segments:
            if seg.target == naif_id and seg.start_jd <= jd_tt <= seg.end_jd:
                pos = seg.compute(jd_tt)
                return (float(pos[0]), float(pos[1]), float(pos[2]))
        raise KeyError(
            f"No segment covers NAIF {naif_id} at JD {jd_tt:.2f}. "
            "The date may be outside the kernel's coverage."
        )

    def list_naif_ids(self) -> list[int]:
        return sorted(self._available)

    def has_segment_at(self, center: int, target: int, jd: float) -> bool:
        for seg in self._kernel.segments:
            if seg.target == target and seg.center == center and seg.start_jd <= jd <= seg.end_jd:
                return True
        return False

    def coverage(self) -> dict[tuple[int, int], tuple[float, float]]:
        result: dict[tuple[int, int], tuple[float, float]] = {}
        for seg in self._kernel.segments:
            key = (seg.center, seg.target)
            if key in result:
                result[key] = (
                    min(result[key][0], seg.start_jd),
                    max(result[key][1], seg.end_jd),
                )
            else:
                result[key] = (seg.start_jd, seg.end_jd)
        return result

    def close(self) -> None:
        try:
            self._kernel.close()
        except Exception:
            pass
