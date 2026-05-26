from __future__ import annotations

from pathlib import Path


def test_native_spk_handle_has_explicit_closed_state_and_serialized_close() -> None:
    source = Path("src/native/include/daf.hpp").read_text(encoding="utf-8")

    assert "bool closed_ = false;" in source
    assert 'throw std::runtime_error("native SPK kernel handle is closed");' in source
    assert "std::lock_guard<std::mutex> guard(cache_mutex);" in source
    assert "closed_ = true;" in source


def test_second_wave_bindings_release_the_gil() -> None:
    source = Path("src/native/bindings/moira_native.cpp").read_text(encoding="utf-8")

    assert '.def("load_segment_evaluator", [](NativeSpkKernelHandle& self, int32_t start_i, int32_t end_i, int32_t data_type) {' in source
    assert '.def("batch_segment_position_and_velocity", [](NativeSpkKernelHandle& self, py::iterable specs, double jd, double jd2) {' in source
    assert '.def("batch_segment_position_requests", [](NativeSpkKernelHandle& self, py::iterable requests) {' in source
    assert '.def("segment_position", [](NativeSpkKernelHandle& self, int32_t start_i, int32_t end_i, int32_t data_type, double jd, double jd2) {' in source
    assert '.def("segment_position_and_velocity", [](NativeSpkKernelHandle& self, int32_t start_i, int32_t end_i, int32_t data_type, double jd, double jd2) {' in source
    assert '.def("close", [](NativeSpkKernelHandle& self) {' in source
    assert '"evaluate_all_planets_apparent_geocentric_ecliptic"' in source
    assert "std::vector<NativePlanetaryPayload> payloads;" in source
    assert "py::gil_scoped_release release;" in source
