from __future__ import annotations

from pathlib import Path


def _binding_block(source: str, anchor: str) -> str:
    start = source.index(anchor)
    next_m = source.find('\n    m.def("', start + 1)
    next_def = source.find('\n        .def("', start + 1)
    next_class = source.find("\n    py::class_", start + 1)
    candidates = [index for index in (next_m, next_def, next_class) if index != -1]
    end = min(candidates) if candidates else len(source)
    return source[start:end]


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


def test_first_wave_native_binding_inventory_marks_long_running_pure_native_paths_for_gil_release() -> None:
    source = Path("src/native/bindings/moira_native.cpp").read_text(encoding="utf-8")

    expected_release = [
        '.def("run", [](SearchPool& self, double a, double b, double dt) {',
        'm.def("longitude_difference_batch", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, const std::vector<double>& jds) {',
        'm.def("declination_batch", [](std::shared_ptr<IEvaluator> t, std::shared_ptr<IEvaluator> obs, const std::vector<double>& jds) {',
        'm.def("find_conjunctions", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, double a, double b, double dt) {',
        'm.def("find_aspects", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, double aspect_deg, double a, double b, double dt) {',
        'm.def("find_stations", [](std::shared_ptr<IEvaluator> target, std::shared_ptr<IEvaluator> obs, double a, double b, double dt) {',
        'm.def("find_ingresses", [](std::shared_ptr<IEvaluator> target, std::shared_ptr<IEvaluator> obs, double a, double b, double dt) {',
        'm.def("find_occultations",',
        'm.def("find_solar_eclipses", [](std::shared_ptr<IEvaluator> sun, std::shared_ptr<IEvaluator> moon, double jd_start, double jd_end, double r_sun_km, double r_moon_km, double dt_days) {',
        'm.def("find_lunar_eclipses", [](std::shared_ptr<IEvaluator> sun, std::shared_ptr<IEvaluator> moon, double jd_start, double jd_end, double r_sun_km, double r_moon_km, double r_earth_km, double dt_days) {',
        'm.def("target_topocentric_altitude",',
        'm.def("find_sun_at_alt",',
        'm.def("search_heliacal_rising",',
        'm.def("search_heliacal_setting",',
    ]
    for anchor in expected_release:
        assert "py::gil_scoped_release release;" in _binding_block(source, anchor)


def test_first_wave_retained_gil_bindings_are_intentionally_small_or_python_shaped() -> None:
    source = Path("src/native/bindings/moira_native.cpp").read_text(encoding="utf-8")

    intentionally_retained = [
        'm.def("longitude_difference", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, double jd) {',
        'm.def("angular_separation", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, double jd) {',
        'm.def("arcus_visionis", &arcus_visionis,',
        'm.def("heliacal_signed_elongation", &heliacal_signed_elongation,',
    ]
    for anchor in intentionally_retained:
        assert anchor in source
