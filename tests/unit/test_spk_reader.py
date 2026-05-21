import threading
import time
from pathlib import Path

import numpy as np
import pytest
import moira.spk_reader as spk_reader
from moira.spk_reader import KernelPool, KernelReader, SpkReader

try:
    from jplephem.daf import DAF as JplDaf
except ImportError:  # pragma: no cover
    JplDaf = None


class _FakeSegment:
    def __init__(self, center: int, target: int, start_jd: float, end_jd: float) -> None:
        self.center = center
        self.target = target
        self.start_jd = start_jd
        self.end_jd = end_jd

    def compute(self, jd):
        return (1.0, 2.0, 3.0)

    def compute_and_differentiate(self, jd):
        return (1.0, 2.0, 3.0), (4.0, 5.0, 6.0)


class _FakeType2Segment(_FakeSegment):
    data_type = 2

    def __init__(self, center: int, target: int, start_jd: float, end_jd: float, coeff_record=None) -> None:
        super().__init__(center=center, target=target, start_jd=start_jd, end_jd=end_jd)
        if coeff_record is None:
            coeff_record = np.array(
                [
                    [1.0, 2.0, 3.0],
                    [0.5, -0.25, 0.75],
                    [10.0, 20.0, 30.0],
                ],
                dtype=float,
            )
        self._data = (0.0, 1000.0, coeff_record[:, :, np.newaxis])


class _FakeKernel:
    def __init__(self, segments) -> None:
        self.segments = segments


def _reader_with_segments(*segments: _FakeSegment) -> SpkReader:
    reader = SpkReader.__new__(SpkReader)
    reader._kernel = _FakeKernel(list(segments))
    reader._path = None
    reader._closed = False
    reader._segments_by_pair = {}
    for segment in segments:
        key = (segment.center, segment.target)
        reader._segments_by_pair.setdefault(key, []).append(segment)
    reader._segments_by_pair = {
        key: tuple(value) for key, value in reader._segments_by_pair.items()
    }
    return reader


def test_has_segment_checks_pair_existence_without_kernel_direct_indexing() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )

    assert reader.has_segment(0, 10) is True
    assert reader.has_segment(0, 11) is False


def test_has_segment_at_is_epoch_aware_across_split_segments() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
        _FakeSegment(center=0, target=10, start_jd=3000.0, end_jd=4000.0),
    )

    assert reader.has_segment(0, 10) is True
    assert reader.has_segment_at(0, 10, 1500.0) is True
    assert reader.has_segment_at(0, 10, 3500.0) is True
    assert reader.has_segment_at(0, 10, 2500.0) is False
    assert reader.has_segment_at(0, 11, 1500.0) is False


def test_position_raises_when_no_segment_covers_requested_jd() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )

    try:
        reader.position(0, 10, 2500.0)
    except ValueError as exc:
        assert "Segments exist" in str(exc)
    else:
        raise AssertionError("Expected ValueError for uncovered JD")


def test_native_position_path_is_used_for_supported_type2_segments(monkeypatch) -> None:
    segment = _FakeType2Segment(center=0, target=10, start_jd=2451544.0, end_jd=2451546.0)
    reader = _reader_with_segments(segment)

    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_SPK", True)
    monkeypatch.setattr(segment, "compute", lambda _jd: (_ for _ in ()).throw(AssertionError("fallback compute should not run")))

    assert reader.position(0, 10, 2451545.0) == (10.5, 22.25, 32.25)


def test_native_position_and_velocity_path_is_used_for_supported_type2_segments(monkeypatch) -> None:
    segment = _FakeType2Segment(center=0, target=10, start_jd=2451544.0, end_jd=2451546.0)
    reader = _reader_with_segments(segment)

    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_SPK", True)
    monkeypatch.setattr(
        segment,
        "compute_and_differentiate",
        lambda _jd: (_ for _ in ()).throw(AssertionError("fallback state compute should not run")),
    )

    pos, vel = reader.position_and_velocity(0, 10, 2451545.0)
    assert pos == (10.5, 22.25, 32.25)
    assert vel == (-604.8000000000001, -1425.6000000000001, -1944.0000000000002)


def test_native_helpers_fall_back_for_unsupported_segments(monkeypatch) -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_SPK", True)

    assert reader.position(0, 10, 1500.0) == (1.0, 2.0, 3.0)
    assert reader.position_and_velocity(0, 10, 1500.0) == (
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
    )


def test_open_kernel_uses_fully_native_path_without_jplephem_open(monkeypatch, tmp_path: Path) -> None:
    kernel_path = tmp_path / "native_only.bsp"
    kernel_path.write_bytes(b"placeholder")

    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_DAF", True)
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_SEGMENTS", True)
    monkeypatch.setattr(spk_reader, "_HAS_JPLEPHEM", False)
    monkeypatch.setattr(spk_reader, "_SPK", None)

    class _NativeStub:
        @staticmethod
        def read_daf_catalog(_path):
            return {
                "little_endian": True,
                "summaries": [
                    {
                        "name": b"SEGMENT",
                        "descriptor": (0.0, 86400.0, 10, 0, 1, 2, 100, 200),
                    }
                ],
            }

        @staticmethod
        def read_spk_chebyshev_segment_payload(_path, _start_i, _end_i, _little_endian, _data_type):
            return {
                "init": 0.0,
                "intlen": 86400.0,
                "record_size": 11,
                "record_count": 1,
                "component_count": 3,
                "coefficient_count": 3,
                "coefficients": np.zeros((3, 3, 1), dtype=float),
            }

        @staticmethod
        def spk_chebyshev_record(_coeff_record, _s):
            return np.array([0.0, 0.0, 0.0], dtype=float)

        @staticmethod
        def spk_chebyshev_record_with_derivative(_coeff_record, _s, _scale):
            return np.zeros(3, dtype=float), np.zeros(3, dtype=float)

    monkeypatch.setattr(spk_reader, "_moira_native", _NativeStub())

    kernel = spk_reader._open_kernel(kernel_path)
    assert type(kernel).__name__ == "_NativeSpkKernel"
    assert len(kernel.segments) == 1


def test_open_kernel_falls_back_when_catalog_contains_unsupported_type(monkeypatch, tmp_path: Path) -> None:
    kernel_path = tmp_path / "fallback.bsp"
    kernel_path.write_bytes(b"placeholder")

    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_DAF", True)
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_SEGMENTS", True)
    monkeypatch.setattr(spk_reader, "_HAS_JPLEPHEM", True)

    class _NativeStub:
        @staticmethod
        def read_daf_catalog(_path):
            return {
                "little_endian": True,
                "summaries": [
                    {
                        "name": b"SEGMENT",
                        "descriptor": (0.0, 86400.0, 10, 0, 1, 9, 100, 200),
                    }
                ],
            }

    monkeypatch.setattr(spk_reader, "_moira_native", _NativeStub())

    sentinel = object()
    monkeypatch.setattr(spk_reader._SPK, "open", lambda _path: sentinel)
    assert spk_reader._open_kernel(kernel_path) is sentinel


def test_open_kernel_raises_plainly_when_unsupported_and_jplephem_missing(monkeypatch, tmp_path: Path) -> None:
    kernel_path = tmp_path / "unsupported.bsp"
    kernel_path.write_bytes(b"placeholder")

    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_DAF", True)
    monkeypatch.setattr(spk_reader, "_HAS_NATIVE_SEGMENTS", True)
    monkeypatch.setattr(spk_reader, "_HAS_JPLEPHEM", False)
    monkeypatch.setattr(spk_reader, "_SPK", None)

    class _NativeStub:
        @staticmethod
        def read_daf_catalog(_path):
            return {
                "little_endian": True,
                "summaries": [
                    {
                        "name": b"SEGMENT",
                        "descriptor": (0.0, 86400.0, 10, 0, 1, 9, 100, 200),
                    }
                ],
            }

    monkeypatch.setattr(spk_reader, "_moira_native", _NativeStub())

    with pytest.raises(RuntimeError, match="requires jplephem"):
        spk_reader._open_kernel(kernel_path)


def test_native_daf_catalog_matches_jplephem_on_moira_written_kernel(tmp_path: Path) -> None:
    if not spk_reader._HAS_NATIVE_DAF:
        pytest.skip("native DAF catalog reader is unavailable")
    if JplDaf is None:
        pytest.skip("jplephem is unavailable for parity comparison")

    from moira.daf_writer import write_spk_type13

    path = tmp_path / "sample_type13.bsp"
    write_spk_type13(
        path,
        bodies=[
            {
                "naif_id": 2000433,
                "center": 10,
                "frame": 1,
                "name": "EROS SAMPLE",
                "window_size": 3,
                "epochs_jd": [2451545.0, 2451546.0, 2451547.0],
                "states": [
                    [1.0, 2.0, 3.0],
                    [4.0, 5.0, 6.0],
                    [7.0, 8.0, 9.0],
                    [0.01, 0.01, 0.01],
                    [0.02, 0.02, 0.02],
                    [0.03, 0.03, 0.03],
                ],
            }
        ],
        locifn="MOIRA TEST KERNEL",
    )

    native_catalog = spk_reader._moira_native.read_daf_catalog(str(path))
    with path.open("rb") as fh:
        daf = JplDaf(fh)
        jpl_summaries = list(daf.summaries())

    assert native_catalog["locidw"] == "DAF/SPK"
    assert native_catalog["locfmt"] == "LTL-IEEE"
    assert native_catalog["nd"] == 2
    assert native_catalog["ni"] == 6
    assert len(native_catalog["summaries"]) == len(jpl_summaries) == 1

    native_summary = native_catalog["summaries"][0]
    jpl_name, jpl_descriptor = jpl_summaries[0]
    assert native_summary["name"] == jpl_name
    assert tuple(native_summary["descriptor"]) == tuple(jpl_descriptor)


def test_native_type13_payload_is_plain_python_owned(tmp_path: Path) -> None:
    if not spk_reader._HAS_NATIVE_DAF:
        pytest.skip("native DAF reader is unavailable")

    from moira.daf_writer import write_spk_type13

    path = tmp_path / "sample_type13_payload.bsp"
    write_spk_type13(
        path,
        bodies=[
            {
                "naif_id": 2000433,
                "center": 10,
                "frame": 1,
                "name": "EROS SAMPLE",
                "window_size": 3,
                "epochs_jd": [2451545.0, 2451546.0, 2451547.0],
                "states": [
                    [1.0, 2.0, 3.0],
                    [4.0, 5.0, 6.0],
                    [7.0, 8.0, 9.0],
                    [0.01, 0.01, 0.01],
                    [0.02, 0.02, 0.02],
                    [0.03, 0.03, 0.03],
                ],
            }
        ],
        locifn="MOIRA TEST TYPE13 PAYLOAD",
    )

    native_catalog = spk_reader._moira_native.read_daf_catalog(str(path))
    descriptor = native_catalog["summaries"][0]["descriptor"]
    payload = spk_reader._moira_native.read_spk_type13_segment_payload(
        str(path),
        int(descriptor[6]),
        int(descriptor[7]),
        True,
    )

    assert set(payload.keys()) == {"epochs_jd", "states", "window_size"}
    assert isinstance(payload["epochs_jd"], tuple)
    assert isinstance(payload["states"], list)
    assert len(payload["states"]) == 6
    assert all(isinstance(axis, tuple) for axis in payload["states"])
    assert payload["epochs_jd"][0] == 2451545.0
    assert payload["states"][0][0] == 1.0
    assert payload["window_size"] == 3


@pytest.mark.requires_ephemeris
def test_native_chebyshev_payload_matches_live_jplephem_segment_data() -> None:
    if not spk_reader._HAS_NATIVE_SEGMENTS:
        pytest.skip("native Chebyshev payload reader is unavailable")
    if not spk_reader._HAS_JPLEPHEM:
        pytest.skip("jplephem is unavailable for payload parity comparison")

    from moira._kernel_paths import find_planetary_kernel

    path = find_planetary_kernel()
    with SpkReader(path) as reader:
        kernel = spk_reader._SPK.open(str(path))
        try:
            native_segment = reader._segment_for(0, 10, 2451545.0)
            jpl_segment = kernel[0, 10]
            payload = spk_reader._moira_native.read_spk_chebyshev_segment_payload(
                str(path),
                int(jpl_segment.start_i),
                int(jpl_segment.end_i),
                True,
                int(jpl_segment.data_type),
            )
            assert payload["init"] == jpl_segment._data[0]
            assert payload["intlen"] == jpl_segment._data[1]
            native_coeffs_jpl_shape = np.array(payload["coefficients"], dtype=float).transpose(2, 1, 0)
            np.testing.assert_allclose(native_coeffs_jpl_shape, jpl_segment._data[2], rtol=0.0, atol=1e-12)
            assert type(native_segment).__name__ == "_NativeChebyshevSegment"
        finally:
            kernel.close()


def test_closed_reader_fails_deterministically() -> None:
    class _ClosableKernel(_FakeKernel):
        def __init__(self, segments) -> None:
            super().__init__(segments)
            self.closed = False

        def close(self) -> None:
            self.closed = True

    reader = SpkReader.__new__(SpkReader)
    reader._kernel = _ClosableKernel([])
    reader._path = None
    reader._closed = False
    reader._segments_by_pair = {}

    reader.close()
    assert reader._closed is True
    assert reader._kernel is None

    try:
        reader.has_segment(0, 10)
    except RuntimeError as exc:
        assert "closed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError after close")


def test_get_reader_is_singleton_safe_under_concurrent_first_access(monkeypatch) -> None:
    init_count = 0
    created = []

    class _FakeReader:
        def __init__(self, path) -> None:
            nonlocal init_count
            time.sleep(0.05)
            init_count += 1
            self.path = Path(path)
            created.append(self)

        def close(self) -> None:
            return None

    monkeypatch.setattr(spk_reader, "SpkReader", _FakeReader)
    monkeypatch.setattr(spk_reader, "_reader", None)
    monkeypatch.setattr(spk_reader, "_reader_path", None)

    results = [None, None]

    def _worker(index: int) -> None:
        results[index] = spk_reader.get_reader("kernels/de441.bsp")

    t1 = threading.Thread(target=_worker, args=(0,))
    t2 = threading.Thread(target=_worker, args=(1,))
    t1.start()
    t2.start()
    t1.join(timeout=2.0)
    t2.join(timeout=2.0)

    assert not t1.is_alive()
    assert not t2.is_alive()
    assert init_count == 1
    assert len(created) == 1
    assert results[0] is results[1] is created[0]


def test_get_reader_rejects_runtime_kernel_replacement(monkeypatch) -> None:
    created = []

    class _FakeReader:
        def __init__(self, path) -> None:
            self.path = Path(path)
            created.append(self)

        def close(self) -> None:
            return None

    monkeypatch.setattr(spk_reader, "SpkReader", _FakeReader)
    monkeypatch.setattr(spk_reader, "_reader", None)
    monkeypatch.setattr(spk_reader, "_reader_path", None)

    first = spk_reader.get_reader("kernels/de441.bsp")
    assert first is created[0]

    try:
        spk_reader.get_reader("kernels/other.bsp")
    except RuntimeError as exc:
        assert "Cannot replace the active SpkReader singleton" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError on active reader replacement")


def test_set_kernel_path_rejects_change_after_singleton_open(monkeypatch) -> None:
    class _FakeReader:
        def close(self) -> None:
            return None

    monkeypatch.setattr(spk_reader, "_reader", _FakeReader())
    monkeypatch.setattr(spk_reader, "_reader_path", Path("kernels/de441.bsp"))

    try:
        spk_reader.set_kernel_path("kernels/other.bsp")
    except RuntimeError as exc:
        assert "Cannot change kernel path" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when changing active kernel path")


def test_reader_override_routes_get_reader_without_touching_singleton(monkeypatch) -> None:
    override = _reader_with_segments(_FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0))
    override._path = Path("kernels/override.bsp")

    monkeypatch.setattr(spk_reader, "_reader", None)
    monkeypatch.setattr(spk_reader, "_reader_path", None)

    with spk_reader.use_reader_override(override):
        assert spk_reader.get_reader() is override
        assert spk_reader.get_reader("kernels/override.bsp") is override


# ---------------------------------------------------------------------------
# SpkReader.coverage / covered_bodies / epoch_range
# ---------------------------------------------------------------------------

def test_coverage_returns_envelope_per_pair() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
        _FakeSegment(center=0, target=11, start_jd=1500.0, end_jd=2500.0),
    )
    cov = reader.coverage()
    assert cov[(0, 10)] == (1000.0, 2000.0)
    assert cov[(0, 11)] == (1500.0, 2500.0)


def test_coverage_spans_split_segments_correctly() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
        _FakeSegment(center=0, target=10, start_jd=3000.0, end_jd=4000.0),
    )
    cov = reader.coverage()
    assert cov[(0, 10)] == (1000.0, 4000.0)


def test_covered_bodies_returns_frozenset_of_target_ids() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
        _FakeSegment(center=0, target=11, start_jd=1000.0, end_jd=2000.0),
    )
    assert reader.covered_bodies() == frozenset({10, 11})


def test_epoch_range_returns_none_for_absent_pair() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    assert reader.epoch_range(0, 99) is None


def test_epoch_range_returns_span_for_present_pair() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
        _FakeSegment(center=0, target=10, start_jd=3000.0, end_jd=4000.0),
    )
    assert reader.epoch_range(0, 10) == (1000.0, 4000.0)


# ---------------------------------------------------------------------------
# KernelReader Protocol conformance
# ---------------------------------------------------------------------------

def test_spk_reader_satisfies_kernel_reader_protocol() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    assert isinstance(reader, KernelReader)


def test_kernel_pool_satisfies_kernel_reader_protocol() -> None:
    pool = KernelPool()
    assert isinstance(pool, KernelReader)


# ---------------------------------------------------------------------------
# swap_reader
# ---------------------------------------------------------------------------

def test_swap_reader_installs_new_reader_and_closes_old(monkeypatch) -> None:
    closed = []

    class _ClosingReader:
        path = Path("kernels/old.bsp")

        def close(self) -> None:
            closed.append(True)

    old = _ClosingReader()
    new = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0)
    )
    new._path = Path("kernels/new.bsp")

    monkeypatch.setattr(spk_reader, "_reader", old)
    monkeypatch.setattr(spk_reader, "_reader_path", old.path)

    result = spk_reader.swap_reader(new)

    assert result is new
    assert spk_reader._reader is new
    assert len(closed) == 1


def test_swap_reader_with_path_opens_new_spk_reader(monkeypatch) -> None:
    created = []

    class _FakeReader:
        def __init__(self, path) -> None:
            self._path = Path(path)
            created.append(self)

        @property
        def path(self):
            return self._path

        def close(self) -> None:
            pass

    monkeypatch.setattr(spk_reader, "SpkReader", _FakeReader)
    monkeypatch.setattr(spk_reader, "_reader", None)
    monkeypatch.setattr(spk_reader, "_reader_path", None)

    result = spk_reader.swap_reader("kernels/de441.bsp")

    assert len(created) == 1
    assert result is created[0]
    assert spk_reader._reader is created[0]


# ---------------------------------------------------------------------------
# reset_singleton
# ---------------------------------------------------------------------------

def test_reset_singleton_closes_reader_and_clears_module_state(monkeypatch) -> None:
    closed = []

    class _ClosingReader:
        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(spk_reader, "_reader", _ClosingReader())
    monkeypatch.setattr(spk_reader, "_reader_path", Path("kernels/de441.bsp"))

    spk_reader.reset_singleton()

    assert len(closed) == 1
    assert spk_reader._reader is None
    assert spk_reader._reader_path is None


def test_reset_singleton_allows_reconfiguration_and_re_init(monkeypatch) -> None:
    created = []

    class _FakeReader:
        def __init__(self, path) -> None:
            self._path = Path(path)
            created.append(self)

        @property
        def path(self):
            return self._path

        def close(self) -> None:
            pass

    monkeypatch.setattr(spk_reader, "SpkReader", _FakeReader)
    monkeypatch.setattr(spk_reader, "_reader", None)
    monkeypatch.setattr(spk_reader, "_reader_path", None)

    spk_reader.set_kernel_path("kernels/de441.bsp")
    first = spk_reader.get_reader()

    spk_reader.reset_singleton()

    spk_reader.set_kernel_path("kernels/de440.bsp")
    second = spk_reader.get_reader()

    assert len(created) == 2
    assert first is not second
    assert second._path == Path("kernels/de440.bsp")


# ---------------------------------------------------------------------------
# KernelPool — dispatch, fallback, introspection, lifecycle
# ---------------------------------------------------------------------------

def _pool_with_readers(*readers) -> KernelPool:
    pool = KernelPool(readers)
    # Prevent SmallBodyKernel isinstance path from firing — all test readers
    # here are SpkReader instances, which should not match SmallBodyKernel.
    return pool


def test_kernel_pool_dispatches_to_covering_reader() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    pool = _pool_with_readers(reader)

    pos = pool.position(0, 10, 1500.0)
    assert pos == (1.0, 2.0, 3.0)


def test_kernel_pool_falls_back_to_second_reader() -> None:
    first = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    second = _reader_with_segments(
        _FakeSegment(center=0, target=11, start_jd=1000.0, end_jd=2000.0),
    )
    pool = _pool_with_readers(first, second)

    pos = pool.position(0, 11, 1500.0)
    assert pos == (1.0, 2.0, 3.0)


def test_kernel_pool_raises_out_of_range_when_no_reader_covers_query() -> None:
    from moira.spk_reader import OutOfRangeError
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    pool = _pool_with_readers(reader)

    with pytest.raises(OutOfRangeError):
        pool.position(0, 99, 1500.0)


def test_kernel_pool_has_segment_checks_all_readers() -> None:
    first = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    second = _reader_with_segments(
        _FakeSegment(center=0, target=11, start_jd=1000.0, end_jd=2000.0),
    )
    pool = _pool_with_readers(first, second)

    assert pool.has_segment(0, 10) is True
    assert pool.has_segment(0, 11) is True
    assert pool.has_segment(0, 99) is False


def test_kernel_pool_has_segment_at_is_epoch_aware() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    pool = _pool_with_readers(reader)

    assert pool.has_segment_at(0, 10, 1500.0) is True
    assert pool.has_segment_at(0, 10, 2500.0) is False


def test_kernel_pool_coverage_merges_ranges_across_readers() -> None:
    first = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    second = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=3000.0, end_jd=4000.0),
        _FakeSegment(center=0, target=11, start_jd=1000.0, end_jd=2000.0),
    )
    pool = _pool_with_readers(first, second)

    cov = pool.coverage()
    assert cov[(0, 10)] == (1000.0, 4000.0)
    assert cov[(0, 11)] == (1000.0, 2000.0)


def test_kernel_pool_covered_bodies_unions_all_readers() -> None:
    first = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    second = _reader_with_segments(
        _FakeSegment(center=0, target=11, start_jd=1000.0, end_jd=2000.0),
    )
    pool = _pool_with_readers(first, second)

    assert pool.covered_bodies() == frozenset({10, 11})


def test_kernel_pool_close_closes_all_readers() -> None:
    closed = []

    class _TrackingReader(SpkReader):
        def close(self) -> None:
            closed.append(id(self))

    r1 = _TrackingReader.__new__(_TrackingReader)
    r1._kernel = _FakeKernel([])
    r1._path = None
    r1._closed = False
    r1._segments_by_pair = {}

    r2 = _TrackingReader.__new__(_TrackingReader)
    r2._kernel = _FakeKernel([])
    r2._path = None
    r2._closed = False
    r2._segments_by_pair = {}

    pool = KernelPool([r1, r2])
    pool.close()

    assert len(closed) == 2
    assert id(r1) in closed
    assert id(r2) in closed


def test_kernel_pool_position_and_velocity_dispatches_to_spk_reader() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    pool = _pool_with_readers(reader)

    pos, vel = pool.position_and_velocity(0, 10, 1500.0)
    assert pos == (1.0, 2.0, 3.0)
    assert vel == (4.0, 5.0, 6.0)


# ---------------------------------------------------------------------------
# SmallBodyKernel.has_segment_at / coverage
# ---------------------------------------------------------------------------

def _small_body_kernel_with_segments(*segments):
    from moira._spk_body_kernel import SmallBodyKernel
    sbk = SmallBodyKernel.__new__(SmallBodyKernel)
    sbk._path = None
    sbk._kernel = _FakeKernel(list(segments))
    sbk._available = {seg.target for seg in segments}
    sbk._center = {}
    for seg in segments:
        sbk._center.setdefault(seg.target, seg.center)
    return sbk


def test_small_body_kernel_has_segment_at_is_epoch_aware() -> None:
    sbk = _small_body_kernel_with_segments(
        _FakeSegment(center=10, target=2000433, start_jd=2451545.0, end_jd=2460000.0),
    )
    assert sbk.has_segment_at(10, 2000433, 2455000.0) is True
    assert sbk.has_segment_at(10, 2000433, 2400000.0) is False
    assert sbk.has_segment_at(10, 9999999, 2455000.0) is False


def test_small_body_kernel_coverage_returns_range_per_pair() -> None:
    sbk = _small_body_kernel_with_segments(
        _FakeSegment(center=10, target=2000433, start_jd=2451545.0, end_jd=2460000.0),
        _FakeSegment(center=10, target=2000001, start_jd=2400000.0, end_jd=2500000.0),
    )
    cov = sbk.coverage()
    assert cov[(10, 2000433)] == (2451545.0, 2460000.0)
    assert cov[(10, 2000001)] == (2400000.0, 2500000.0)


def test_small_body_kernel_coverage_merges_split_segments() -> None:
    sbk = _small_body_kernel_with_segments(
        _FakeSegment(center=10, target=2000433, start_jd=2451545.0, end_jd=2455000.0),
        _FakeSegment(center=10, target=2000433, start_jd=2456000.0, end_jd=2460000.0),
    )
    cov = sbk.coverage()
    assert cov[(10, 2000433)] == (2451545.0, 2460000.0)


@pytest.mark.requires_ephemeris
def test_native_spk_record_parity_against_jplephem_type2_segment() -> None:
    if not spk_reader._HAS_NATIVE_SPK:
        pytest.skip("native SPK Chebyshev evaluator is unavailable")

    from moira._kernel_paths import find_planetary_kernel

    with SpkReader(find_planetary_kernel()) as reader:
        jd = 2451545.0
        segment = reader._segment_for(0, 10, jd)
        if getattr(segment, "data_type", None) != 2:
            pytest.skip("active planetary kernel did not expose a type-2 segment")

        coeff_record, s, derivative_scale = spk_reader._native_spk_record_inputs(segment, jd)
        native_pos = spk_reader._moira_native.spk_chebyshev_record(coeff_record, s)
        native_pos, native_vel = spk_reader._moira_native.spk_chebyshev_record_with_derivative(
            coeff_record, s, derivative_scale
        )
        ref_pos, ref_vel = segment.compute_and_differentiate(jd)

        def to_list(obj):
            return obj.tolist() if hasattr(obj, 'tolist') else list(obj)

        for got, want in zip(to_list(native_pos), to_list(ref_pos)):
            assert abs(got - float(want)) < 1e-9
        for got, want in zip(to_list(native_vel), to_list(ref_vel)):
            assert abs(got - float(want)) < 1e-9


@pytest.mark.requires_ephemeris
def test_spk_reader_native_daf_kernel_catalog_matches_live_kernel() -> None:
    if not spk_reader._HAS_NATIVE_DAF:
        pytest.skip("native DAF catalog reader is unavailable")

    from moira._kernel_paths import find_planetary_kernel

    with SpkReader(find_planetary_kernel()) as reader:
        assert type(reader._kernel).__name__ == "_NativeSpkKernel"
        assert reader.has_segment(0, 10) is True
        assert reader.has_segment(0, 3) is True


@pytest.mark.requires_ephemeris
def test_native_segment_compute_matches_jplephem_for_live_kernel() -> None:
    if not spk_reader._HAS_NATIVE_SEGMENTS:
        pytest.skip("native Chebyshev segment path is unavailable")
    if not spk_reader._HAS_JPLEPHEM:
        pytest.skip("jplephem is unavailable for compute parity comparison")

    from moira._kernel_paths import find_planetary_kernel

    path = find_planetary_kernel()
    native_reader = SpkReader(path)
    jpl_kernel = spk_reader._SPK.open(str(path))
    try:
        jd = 2451545.0
        native_segment = native_reader._segment_for(0, 10, jd)
        jpl_segment = jpl_kernel[0, 10]
        native_pos, native_vel = native_segment.compute_and_differentiate(jd)
        jpl_pos, jpl_vel = jpl_segment.compute_and_differentiate(jd)
        np.testing.assert_allclose(native_pos, jpl_pos, rtol=0.0, atol=1e-9)
        np.testing.assert_allclose(native_vel, jpl_vel, rtol=0.0, atol=1e-9)
    finally:
        native_reader.close()
        jpl_kernel.close()


@pytest.mark.requires_ephemeris
def test_native_segment_split_jd_matches_jplephem_for_live_kernel() -> None:
    if not spk_reader._HAS_NATIVE_SEGMENTS:
        pytest.skip("native Chebyshev segment path is unavailable")
    if not spk_reader._HAS_JPLEPHEM:
        pytest.skip("jplephem is unavailable for split-JD parity comparison")

    from moira._kernel_paths import find_planetary_kernel

    path = find_planetary_kernel()
    native_reader = SpkReader(path)
    jpl_kernel = spk_reader._SPK.open(str(path))
    try:
        jd = 2451545.0
        jd2 = 1e-9
        native_segment = native_reader._segment_for(0, 10, jd)
        jpl_segment = jpl_kernel[0, 10]
        native_pos, native_vel = native_segment.compute_and_differentiate(jd, jd2)
        jpl_pos, jpl_vel = jpl_segment.compute_and_differentiate(jd, jd2)
        np.testing.assert_allclose(native_pos, jpl_pos, rtol=0.0, atol=1e-9)
        np.testing.assert_allclose(native_vel, jpl_vel, rtol=0.0, atol=1e-9)
    finally:
        native_reader.close()
        jpl_kernel.close()


@pytest.mark.requires_ephemeris
def test_native_segment_split_jd_uses_native_path_without_payload_fallback(monkeypatch) -> None:
    if not spk_reader._HAS_NATIVE_SEGMENTS:
        pytest.skip("native Chebyshev segment path is unavailable")
    if not spk_reader._HAS_NATIVE_DAF:
        pytest.skip("native DAF handle path is unavailable")

    from moira._kernel_paths import find_planetary_kernel

    with SpkReader(find_planetary_kernel()) as reader:
        segment = reader._segment_for(0, 10, 2451545.0)
        if type(reader._kernel).__name__ != "_NativeSpkKernel":
            pytest.skip("active planetary kernel did not route through the native SPK kernel handle")

        monkeypatch.setattr(
            segment,
            "_load_data",
            lambda: (_ for _ in ()).throw(AssertionError("split-JD path should not fall back to Python payload materialization")),
        )

        pos, vel = segment.compute_and_differentiate(2451545.0, 1e-9)
        assert len(pos) == 3
        assert len(vel) == 3


@pytest.mark.requires_ephemeris
def test_native_handle_batch_segment_position_and_velocity_accepts_split_jd() -> None:
    if not spk_reader._HAS_NATIVE_DAF:
        pytest.skip("native DAF handle path is unavailable")
    if not spk_reader._HAS_JPLEPHEM:
        pytest.skip("jplephem is unavailable for split-JD batch parity comparison")

    from moira._kernel_paths import find_planetary_kernel

    path = find_planetary_kernel()
    native_reader = SpkReader(path)
    jpl_kernel = spk_reader._SPK.open(str(path))
    try:
        if type(native_reader._kernel).__name__ != "_NativeSpkKernel":
            pytest.skip("active planetary kernel did not route through the native SPK kernel handle")

        handle = native_reader._kernel._handle
        jd = 2451545.0
        jd2 = 1e-9
        segment = native_reader._segment_for(0, 10, jd)
        specs = [(int(segment.start_i), int(segment.end_i), int(segment.data_type))]
        batch = handle.batch_segment_position_and_velocity(specs, jd, jd2)
        jpl_pos, jpl_vel = jpl_kernel[0, 10].compute_and_differentiate(jd, jd2)
        pos, vel = batch[0]
        np.testing.assert_allclose(pos, jpl_pos, rtol=0.0, atol=1e-9)
        np.testing.assert_allclose(vel, jpl_vel, rtol=0.0, atol=1e-9)
    finally:
        native_reader.close()
        jpl_kernel.close()


@pytest.mark.requires_ephemeris
def test_native_handle_batch_segment_position_requests_accepts_split_jd() -> None:
    if not spk_reader._HAS_NATIVE_DAF:
        pytest.skip("native DAF handle path is unavailable")
    if not spk_reader._HAS_JPLEPHEM:
        pytest.skip("jplephem is unavailable for split-JD batch parity comparison")

    from moira._kernel_paths import find_planetary_kernel

    path = find_planetary_kernel()
    native_reader = SpkReader(path)
    jpl_kernel = spk_reader._SPK.open(str(path))
    try:
        if type(native_reader._kernel).__name__ != "_NativeSpkKernel":
            pytest.skip("active planetary kernel did not route through the native SPK kernel handle")

        handle = native_reader._kernel._handle
        jd = 2451545.0
        jd2 = 1e-9
        segment = native_reader._segment_for(0, 10, jd)
        requests = [(int(segment.start_i), int(segment.end_i), int(segment.data_type), jd, jd2)]
        batch = handle.batch_segment_position_requests(requests)
        jpl_pos = jpl_kernel[0, 10].compute(jd, jd2)
        np.testing.assert_allclose(batch[0], jpl_pos, rtol=0.0, atol=1e-9)
    finally:
        native_reader.close()
        jpl_kernel.close()
