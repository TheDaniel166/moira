from __future__ import annotations

from pathlib import Path


def test_first_wave_native_hot_paths_release_the_gil() -> None:
    source = Path("src/native/bindings/moira_native.cpp").read_text(encoding="utf-8")

    assert 'py::gil_scoped_release release;' in source
    assert '.def("evaluate", [](IEvaluator& self, double jd) {' in source
    assert '.def("evaluate_batch", [](IEvaluator& self, const std::vector<double>& jds) {' in source
    assert '.def("position", [](const SpkSegmentEvaluator& self, double jd, double jd2) {' in source
    assert 'py::tuple spk_chebyshev_series_bulk_evaluate_py(' in source
    assert 'm.def("harmogram_compute_components",' in source
    assert 'm.def("harmogram_trace_batch",' in source
    assert 'm.def("harmogram_intensity_components",' in source
    assert 'm.def("normalize_vectors_bulk", [](const std::vector<double>& x, const std::vector<double>& y, const std::vector<double>& z) {' in source
