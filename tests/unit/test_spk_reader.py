import threading
import time
from pathlib import Path

import moira.spk_reader as spk_reader
from moira.spk_reader import KernelPool, KernelReader, SpkReader


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


def test_kernel_pool_raises_key_error_when_no_reader_covers_query() -> None:
    reader = _reader_with_segments(
        _FakeSegment(center=0, target=10, start_jd=1000.0, end_jd=2000.0),
    )
    pool = _pool_with_readers(reader)

    try:
        pool.position(0, 99, 1500.0)
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError when no reader covers the query")


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
