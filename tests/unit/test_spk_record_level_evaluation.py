"""Record-level SPK evaluation is bit-identical to whole-segment evaluation.

Governing object: an SPK type 2/3 Chebyshev segment. Record i covers
[INIT + i*INTLEN, INIT + (i+1)*INTLEN); the evaluator selects the record and the
normalized time from INIT/INTLEN and applies the Chebyshev series to that
record's coefficient words. Record-level mode reads only that record from the
kernel instead of preloading the segment, so for every epoch it must return
exactly (==, not within tolerance) what the whole-segment mode returns.

Evidence class: dual-path equivalence on the configured planetary kernel, every
type 2/3 segment, deterministic epochs that include segment endpoints, record
boundaries (and 1e-9 day either side of them) and split (jd, jd2) inputs.
"""

from __future__ import annotations

import random

import pytest

import moira.spk_reader as spk_reader

native = spk_reader._moira_native

pytestmark = pytest.mark.skipif(
    native is None or not hasattr(native, "open_spk_kernel"),
    reason="native SPK kernel handle is unavailable",
)

J2000 = 2451545.0


@pytest.fixture(scope="module")
def kernel_path():
    from moira._kernel_paths import find_planetary_kernel

    try:
        path = find_planetary_kernel()
    except Exception as exc:  # pragma: no cover - resource dependent
        pytest.skip(f"planetary kernel unavailable: {exc}")
    if path is None:  # pragma: no cover - resource dependent
        pytest.skip("planetary kernel unavailable")
    return str(path)


def _open(monkeypatch, path: str, mode: str, segment_cache: str | None = None):
    monkeypatch.setenv("MOIRA_NATIVE_SPK_EVALUATION", mode)
    if segment_cache is not None:
        monkeypatch.setenv("MOIRA_NATIVE_SEGMENT_CACHE_MAX", segment_cache)
    handle = native.open_spk_kernel(path)
    monkeypatch.delenv("MOIRA_NATIVE_SPK_EVALUATION")
    if segment_cache is not None:
        monkeypatch.delenv("MOIRA_NATIVE_SEGMENT_CACHE_MAX")
    return handle


def _chebyshev_segments(handle):
    out = []
    for summary in handle.catalog()["summaries"]:
        start_s, end_s, _target, _center, _frame, data_type, start_i, end_i = summary["descriptor"]
        if int(data_type) in (2, 3):
            out.append((
                int(start_i), int(end_i), int(data_type),
                J2000 + start_s / 86400.0, J2000 + end_s / 86400.0,
            ))
    return out


def _epochs(segment, init_jd: float, intlen_days: float, record_count: int, rng: random.Random):
    _, _, _, start_jd, end_jd = segment
    epochs = [start_jd, end_jd]
    epochs += [rng.uniform(start_jd, end_jd) for _ in range(40)]
    for index in [0, 1, record_count - 1] + [rng.randrange(record_count) for _ in range(12)]:
        boundary = init_jd + index * intlen_days
        for delta in (-1e-9, 0.0, 1e-9):
            epoch = boundary + delta
            if start_jd <= epoch <= end_jd:
                epochs.append(epoch)
    return epochs


@pytest.mark.requires_ephemeris
def test_record_level_matches_whole_segment_bit_for_bit(monkeypatch, kernel_path) -> None:
    record = _open(monkeypatch, kernel_path, "record")
    # One cached segment at a time keeps the comparison handle's memory bounded.
    segment = _open(monkeypatch, kernel_path, "segment", segment_cache="1")
    assert record.record_level() is True
    assert segment.record_level() is False

    rng = random.Random(20261027)
    compared = 0
    for seg in _chebyshev_segments(record):
        start_i, end_i, data_type, _, _ = seg
        evaluator = record.load_segment_evaluator(start_i, end_i, data_type)
        assert evaluator.record_level() is True
        init_s, intlen_s, record_count, _, _ = evaluator.chebyshev_metadata()
        whole = segment.load_segment_evaluator(start_i, end_i, data_type)
        assert whole.record_level() is False
        assert whole.chebyshev_metadata() == evaluator.chebyshev_metadata()

        for epoch in _epochs(seg, J2000 + init_s / 86400.0, intlen_s / 86400.0, int(record_count), rng):
            got = record.segment_position_and_velocity(start_i, end_i, data_type, epoch, 0.0)
            want = segment.segment_position_and_velocity(start_i, end_i, data_type, epoch, 0.0)
            assert got == want, (start_i, epoch)
            day = float(int(epoch))
            got = record.segment_position(start_i, end_i, data_type, day, epoch - day)
            want = segment.segment_position(start_i, end_i, data_type, day, epoch - day)
            assert got == want, (start_i, epoch, "split")
            compared += 1

        for index in {0, int(record_count) - 1, rng.randrange(int(record_count))}:
            assert evaluator.chebyshev_records(index, 1) == whole.chebyshev_records(index, 1)
    assert compared > 0


@pytest.mark.requires_ephemeris
def test_record_cache_stays_bounded(monkeypatch, kernel_path) -> None:
    monkeypatch.setenv("MOIRA_NATIVE_SPK_RECORD_CACHE_MAX", "8")
    handle = _open(monkeypatch, kernel_path, "record")
    monkeypatch.delenv("MOIRA_NATIVE_SPK_RECORD_CACHE_MAX")
    assert handle.record_cache_limit() == 8

    start_i, end_i, data_type, start_jd, end_jd = _chebyshev_segments(handle)[0]
    evaluator = handle.load_segment_evaluator(start_i, end_i, data_type)
    rng = random.Random(7)
    for _ in range(200):
        handle.segment_position(start_i, end_i, data_type, rng.uniform(start_jd, end_jd), 0.0)
    assert 1 <= evaluator.cached_record_count() <= 8


@pytest.mark.requires_ephemeris
def test_evaluation_mode_is_explicit(monkeypatch, kernel_path) -> None:
    monkeypatch.delenv("MOIRA_NATIVE_SPK_EVALUATION", raising=False)
    assert native.open_spk_kernel(kernel_path).record_level() is True

    monkeypatch.setenv("MOIRA_NATIVE_SPK_EVALUATION", "segment")
    assert native.open_spk_kernel(kernel_path).record_level() is False

    monkeypatch.setenv("MOIRA_NATIVE_SPK_EVALUATION", "lazy")
    with pytest.raises(ValueError, match="'record' or 'segment'"):
        native.open_spk_kernel(kernel_path)


@pytest.mark.requires_ephemeris
def test_evaluator_outlives_its_closed_handle(monkeypatch, kernel_path) -> None:
    # A whole-segment evaluator owns its coefficients and keeps working after
    # the handle closes; a record-level evaluator must honour the same contract
    # for records it has not read yet.
    record = _open(monkeypatch, kernel_path, "record")
    segment = _open(monkeypatch, kernel_path, "segment", segment_cache="1")
    # A many-record segment, so start and end lie in different records.
    start_i, end_i, data_type, start_jd, end_jd = max(
        _chebyshev_segments(record), key=lambda seg: seg[1] - seg[0]
    )
    evaluator = record.load_segment_evaluator(start_i, end_i, data_type)
    whole = segment.load_segment_evaluator(start_i, end_i, data_type)
    assert evaluator.chebyshev_metadata()[2] > 1
    evaluator.position(start_jd, 0.0)
    record.close()
    segment.close()

    assert evaluator.position(end_jd, 0.0) == whole.position(end_jd, 0.0)
    with pytest.raises(RuntimeError, match="closed"):
        record.load_segment_evaluator(start_i, end_i, data_type)
