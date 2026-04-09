import threading
import time
from pathlib import Path

import moira.spk_reader as spk_reader
from moira.spk_reader import SpkReader


class _FakeSegment:
    def __init__(self, center: int, target: int, start_jd: float, end_jd: float) -> None:
        self.center = center
        self.target = target
        self.start_jd = start_jd
        self.end_jd = end_jd


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
