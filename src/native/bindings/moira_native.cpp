#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include <pybind11/numpy.h>
#include "geometry.hpp"
#include "julian.hpp"
#include "math_utils.hpp"
#include "interpolation.hpp"
#include "solvers.hpp"
#include "coordinates.hpp"
#include "sidereal.hpp"
#include "daf.hpp"
#include "light_time.hpp"
#include "evaluators.hpp"
#include "separation.hpp"
#include "events.hpp"
#include "cartography.hpp"
#include "search_pool.hpp"

namespace py = pybind11;
using namespace moira::native;

namespace {

py::list vector_to_py_list(const std::vector<double>& values) {
    py::list out;
    for (double v : values) out.append(v);
    return out;
}

/**
 * @brief 2D version: evaluates one record provided as a (coefficient, component) array.
 */
py::list spk_chebyshev_record_py(
    py::array_t<double, py::array::c_style | py::array::forcecast> coeff_record,
    double s
) {
    auto buf = coeff_record.request();
    if (buf.ndim != 2) throw std::runtime_error("Evaluator expects 2D coefficients");

    const size_t component_count = static_cast<size_t>(buf.shape[0]);
    const size_t coefficient_count = static_cast<size_t>(buf.shape[1]);
    const auto* coeffs = static_cast<const double*>(buf.ptr);

    std::vector<double> result(component_count);
    spk_chebyshev_record_inplace(
        coeffs, coefficient_count, component_count, s, result.data(), 
        1,                // coeff_stride = 1
        coefficient_count // component_stride = n
    );

    return vector_to_py_list(result);
}

py::tuple spk_chebyshev_record_with_derivative_py(
    py::array_t<double, py::array::c_style | py::array::forcecast> coeff_record,
    double s,
    double derivative_scale
) {
    auto buf = coeff_record.request();
    if (buf.ndim != 2) throw std::runtime_error("Evaluator expects 2D coefficients");

    const size_t component_count = static_cast<size_t>(buf.shape[0]);
    const size_t coefficient_count = static_cast<size_t>(buf.shape[1]);
    const auto* coeffs = static_cast<const double*>(buf.ptr);

    std::vector<double> values(component_count);
    std::vector<double> rates(component_count);

    spk_chebyshev_record_with_derivative_inplace(
        coeffs, coefficient_count, component_count, s, values.data(), rates.data(),
        1,                // coeff_stride = 1
        coefficient_count // component_stride = n
    );

    py::list v_out = vector_to_py_list(values);
    py::list r_out;
    for (double r : rates) r_out.append(r * derivative_scale);

    return py::make_tuple(v_out, r_out);
}

/**
 * @brief 3D version: evaluates one record from a (record, component, coefficient) series.
 */
py::list spk_chebyshev_series_record_py(
    py::array_t<double, py::array::c_style | py::array::forcecast> coefficients,
    int32_t record_index,
    double s
) {
    auto buf = coefficients.request();
    if (buf.ndim != 3) throw std::runtime_error("Series evaluator expects 3D coefficients");

    const size_t component_count = static_cast<size_t>(buf.shape[1]);
    const size_t coefficient_count = static_cast<size_t>(buf.shape[2]);
    const size_t record_stride = component_count * coefficient_count;

    const auto* coeffs = static_cast<const double*>(buf.ptr);
    std::vector<double> result(component_count);

    spk_chebyshev_record_inplace(
        coeffs + static_cast<size_t>(record_index) * record_stride,
        coefficient_count,
        component_count,
        s,
        result.data(),
        1,                // coeff_stride = 1 (contiguous)
        coefficient_count // component_stride = n
    );

    return vector_to_py_list(result);
}

py::tuple spk_chebyshev_series_record_with_derivative_py(
    py::array_t<double, py::array::c_style | py::array::forcecast> coefficients,
    int32_t record_index,
    double s,
    double derivative_scale
) {
    auto buf = coefficients.request();
    if (buf.ndim != 3) throw std::runtime_error("Series evaluator expects 3D coefficients");

    const size_t component_count = static_cast<size_t>(buf.shape[1]);
    const size_t coefficient_count = static_cast<size_t>(buf.shape[2]);
    const size_t record_stride = component_count * coefficient_count;

    const auto* coeffs = static_cast<const double*>(buf.ptr);
    std::vector<double> values(component_count);
    std::vector<double> rates(component_count);

    spk_chebyshev_record_with_derivative_inplace(
        coeffs + static_cast<size_t>(record_index) * record_stride,
        coefficient_count,
        component_count,
        s,
        values.data(),
        rates.data(),
        1,
        coefficient_count
    );

    py::list v_out = vector_to_py_list(values);
    py::list r_out;
    for (double r : rates) r_out.append(r * derivative_scale);

    return py::make_tuple(v_out, r_out);
}

py::tuple spk_chebyshev_series_bulk_evaluate_py(
    py::array_t<double, py::array::c_style | py::array::forcecast> coeff_series,
    py::array_t<int32_t, py::array::c_style | py::array::forcecast> record_indices,
    py::array_t<double, py::array::c_style | py::array::forcecast> s_values,
    py::array_t<double, py::array::c_style | py::array::forcecast> derivative_scales,
    bool need_rates
) {
    auto buf = coeff_series.request();
    auto idx_buf = record_indices.request();
    auto s_buf = s_values.request();
    auto ds_buf = derivative_scales.request();

    if (buf.ndim != 3) throw std::runtime_error("Bulk evaluator expects 3D coefficients");
    
    const size_t workload_size = static_cast<size_t>(idx_buf.shape[0]);
    const size_t record_count = static_cast<size_t>(buf.shape[0]);
    const size_t component_count = static_cast<size_t>(buf.shape[1]);
    const size_t coefficient_count = static_cast<size_t>(buf.shape[2]);
    const size_t record_stride = component_count * coefficient_count;

    const auto* coeffs = static_cast<const double*>(buf.ptr);
    const auto* indices = static_cast<const int32_t*>(idx_buf.ptr);
    const auto* s_ptr = static_cast<const double*>(s_buf.ptr);
    const auto* ds_ptr = static_cast<const double*>(ds_buf.ptr);

    py::array_t<double> values_out({workload_size, component_count});
    auto v_out_ptr = values_out.mutable_data();

    if (need_rates) {
        py::array_t<double> rates_out({workload_size, component_count});
        auto r_out_ptr = rates_out.mutable_data();

        for (size_t i = 0; i < workload_size; ++i) {
            const int32_t record_index = indices[i];
            spk_chebyshev_record_with_derivative_inplace(
                coeffs + static_cast<size_t>(record_index) * record_stride,
                coefficient_count, component_count, s_ptr[i],
                v_out_ptr + i * component_count,
                r_out_ptr + i * component_count,
                1, coefficient_count
            );
            
            const double ds = ds_ptr[i];
            for (size_t j = 0; j < component_count; ++j) {
                r_out_ptr[i * component_count + j] *= ds;
            }
        }
        return py::make_tuple(values_out, rates_out);
    } else {
        for (size_t i = 0; i < workload_size; ++i) {
            const int32_t record_index = indices[i];
            spk_chebyshev_record_inplace(
                coeffs + static_cast<size_t>(record_index) * record_stride,
                coefficient_count, component_count, s_ptr[i],
                v_out_ptr + i * component_count,
                1, coefficient_count
            );
        }
        return py::make_tuple(values_out, py::none());
    }
}

py::dict read_daf_catalog_py(const std::string& path) {
    DafCatalog catalog = read_daf_catalog(path);
    py::list summaries;
    for (const DafSummaryEntry& entry : catalog.summaries) {
        py::dict item;
        item["name"] = py::bytes(entry.name);
        item["descriptor"] = py::make_tuple(
            entry.start_second, entry.end_second, entry.target,
            entry.center, entry.frame, entry.data_type,
            entry.start_i, entry.end_i
        );
        summaries.append(std::move(item));
    }

    py::dict out;
    out["locidw"] = catalog.locidw;
    out["locfmt"] = catalog.locfmt;
    out["nd"] = catalog.nd;
    out["ni"] = catalog.ni;
    out["fward"] = catalog.fward;
    out["bward"] = catalog.bward;
    out["free"] = catalog.free;
    out["little_endian"] = catalog.little_endian;
    out["summaries"] = std::move(summaries);
    return out;
}

py::dict read_spk_chebyshev_segment_payload_py(
    const std::string& path, int32_t start_i, int32_t end_i, bool little_endian, int32_t data_type
) {
    SpkChebyshevSegmentPayload payload = read_spk_chebyshev_segment_payload(path, start_i, end_i, little_endian, data_type);

    py::array_t<double> coeffs({payload.record_count, payload.component_count, payload.coefficient_count});
    auto out = coeffs.mutable_unchecked<3>();
    for (size_t i = 0; i < payload.record_count; ++i) {
        for (size_t j = 0; j < payload.component_count; ++j) {
            for (size_t k = 0; k < payload.coefficient_count; ++k) {
                out(i, j, k) = payload.coefficients[(i * payload.component_count + j) * payload.coefficient_count + k];
            }
        }
    }

    py::dict out_dict;
    out_dict["init"] = payload.init;
    out_dict["intlen"] = payload.intlen;
    out_dict["coefficients"] = coeffs;
    return out_dict;
}

py::dict read_spk_type13_segment_payload_py(const std::string& path, int32_t start_i, int32_t end_i, bool little_endian) {
    SpkType13SegmentPayload payload = read_spk_type13_segment_payload(path, start_i, end_i, little_endian);

    py::array_t<double> epochs(payload.state_count);
    std::copy(payload.epochs_jd.begin(), payload.epochs_jd.end(), epochs.mutable_data());

    py::array_t<double> coeffs({static_cast<size_t>(payload.state_count), static_cast<size_t>(6)});
    auto out = coeffs.mutable_unchecked<2>();
    for (size_t i = 0; i < static_cast<size_t>(payload.state_count); ++i) {
        for (size_t j = 0; j < 6; ++j) {
            out(i, j) = payload.states[j * payload.state_count + i];
        }
    }

    py::dict out_dict;
    out_dict["epochs"] = epochs;
    out_dict["coefficients"] = coeffs;
    out_dict["window_size"] = payload.window_size;
    return out_dict;
}

// --- Cartography Helpers ---

void solar_cartography_grid_sweep_py(
    const IEvaluator& sun,
    const IEvaluator& moon,
    py::array_t<double> jds,
    py::array_t<double> gasts_deg,
    py::array_t<double> lats_deg,
    py::array_t<double> lons_deg,
    double sun_radius_km,
    double moon_radius_km,
    py::array_t<double> overlap_max,
    py::array_t<double> central_max,
    py::array_t<double> magnitude_max
) {
    auto jd_ptr = jds.data();
    auto gast_ptr = gasts_deg.data();
    auto lat_ptr = lats_deg.data();
    auto lon_ptr = lons_deg.data();
    auto overlap_ptr = overlap_max.mutable_data();
    auto central_ptr = central_max.mutable_data();
    auto magnitude_ptr = magnitude_max.mutable_data();

    solar_cartography_grid_sweep(
        sun, moon, jd_ptr, gast_ptr, jds.size(),
        lat_ptr, lon_ptr, lats_deg.size(),
        sun_radius_km, moon_radius_km,
        overlap_ptr, central_ptr, magnitude_ptr
    );
}

void lunar_cartography_grid_sweep_py(
    const IEvaluator& sun,
    const IEvaluator& moon,
    py::array_t<double> jds,
    py::array_t<double> gasts_deg,
    py::array_t<double> magnitudes_base,
    py::array_t<double> lats_deg,
    py::array_t<double> lons_deg,
    py::array_t<double> penumbral_max,
    py::array_t<double> partial_max,
    py::array_t<double> total_max,
    py::array_t<double> magnitude_max,
    py::object u1_u4_obj,
    py::object u2_u3_obj
) {
    auto jd_ptr = jds.data();
    auto gast_ptr = gasts_deg.data();
    auto mag_base_ptr = magnitudes_base.data();
    auto lat_ptr = lats_deg.data();
    auto lon_ptr = lons_deg.data();
    auto pen_ptr = penumbral_max.mutable_data();
    auto par_ptr = partial_max.mutable_data();
    auto tot_ptr = total_max.mutable_data();
    auto mag_ptr = magnitude_max.mutable_data();

    double u1_u4[2], u2_u3[2];
    double* p_u1_u4 = nullptr;
    double* p_u2_u3 = nullptr;

    if (!u1_u4_obj.is_none()) {
        auto arr = u1_u4_obj.cast<py::array_t<double>>();
        u1_u4[0] = arr.at(0);
        u1_u4[1] = arr.at(1);
        p_u1_u4 = u1_u4;
    }
    if (!u2_u3_obj.is_none()) {
        auto arr = u2_u3_obj.cast<py::array_t<double>>();
        u2_u3[0] = arr.at(0);
        u2_u3[1] = arr.at(1);
        p_u2_u3 = u2_u3;
    }

    lunar_cartography_grid_sweep(
        sun, moon, jd_ptr, gast_ptr, mag_base_ptr, jds.size(),
        lat_ptr, lon_ptr, lats_deg.size(),
        pen_ptr, par_ptr, tot_ptr, mag_ptr,
        p_u1_u4, p_u2_u3
    );
}

py::tuple solar_find_greatest_eclipse_location_py(
    const IEvaluator& sun,
    const IEvaluator& moon,
    double jd,
    double gast_deg
) {
    auto result = solar_find_greatest_eclipse_location(sun, moon, jd, gast_deg);
    return py::make_tuple(result.lat_deg, result.lon_deg, result.separation_deg);
}

// Batch version: solves for each JD in a list, returns list of (lat, lon, sep) tuples.
py::list solar_centerline_batch_py(
    const IEvaluator& sun,
    const IEvaluator& moon,
    py::array_t<double> jds,
    py::array_t<double> gasts_deg
) {
    auto jd_ptr   = jds.data();
    auto gast_ptr = gasts_deg.data();
    size_t n = static_cast<size_t>(jds.size());
    py::list results;
    for (size_t i = 0; i < n; ++i) {
        auto r = solar_find_greatest_eclipse_location(sun, moon, jd_ptr[i], gast_ptr[i]);
        results.append(py::make_tuple(r.lat_deg, r.lon_deg, r.separation_deg));
    }
    return results;
}

py::tuple solar_observer_quantities_batch_py(
    const IEvaluator& sun,
    const IEvaluator& moon,
    double jd,
    double gast_deg,
    py::array_t<double> lats_deg,
    py::array_t<double> lons_deg,
    double sun_radius_km,
    double moon_radius_km
) {
    auto buf_lat = lats_deg.request();
    auto buf_lon = lons_deg.request();
    size_t n_obs = buf_lat.size;
    
    auto lat_ptr = static_cast<const double*>(buf_lat.ptr);
    auto lon_ptr = static_cast<const double*>(buf_lon.ptr);
    
    py::ssize_t shape = static_cast<py::ssize_t>(n_obs);
    py::array_t<double> raw_ov(shape);
    py::array_t<double> alt(shape);
    py::array_t<double> ha(shape);
    
    auto raw_ov_ptr = static_cast<double*>(raw_ov.request().ptr);
    auto alt_ptr    = static_cast<double*>(alt.request().ptr);
    auto ha_ptr     = static_cast<double*>(ha.request().ptr);
    
    solar_observer_quantities_batch(
        sun, moon, jd, gast_deg, lat_ptr, lon_ptr, n_obs,
        sun_radius_km, moon_radius_km, raw_ov_ptr, alt_ptr, ha_ptr
    );
    
    return py::make_tuple(raw_ov, alt, ha);
}

void solar_cartography_grid_sweep_vectors_py(
    py::array_t<double> sun_xyz_series,
    py::array_t<double> moon_xyz_series,
    py::array_t<double> gasts_deg,
    py::array_t<double> lats_deg,
    py::array_t<double> lons_deg,
    double sun_radius_km,
    double moon_radius_km,
    py::array_t<double> overlap_max,
    py::array_t<double> central_max,
    py::array_t<double> magnitude_max
) {
    auto sun_buf = sun_xyz_series.request();
    auto moon_buf = moon_xyz_series.request();
    auto gast_buf = gasts_deg.request();
    auto lat_buf = lats_deg.request();
    auto lon_buf = lons_deg.request();

    if (sun_buf.ndim != 2 || moon_buf.ndim != 2 || sun_buf.shape[1] != 3 || moon_buf.shape[1] != 3) {
        throw std::runtime_error("solar_cartography_grid_sweep_vectors expects (n, 3) state arrays.");
    }
    if (sun_buf.shape[0] != gast_buf.shape[0] || moon_buf.shape[0] != gast_buf.shape[0] || lat_buf.shape[0] != lon_buf.shape[0]) {
        throw std::runtime_error("solar_cartography_grid_sweep_vectors received inconsistent array lengths.");
    }

    solar_cartography_grid_sweep_vectors(
        static_cast<const double*>(sun_buf.ptr),
        static_cast<const double*>(moon_buf.ptr),
        static_cast<const double*>(gast_buf.ptr),
        static_cast<size_t>(gast_buf.shape[0]),
        static_cast<const double*>(lat_buf.ptr),
        static_cast<const double*>(lon_buf.ptr),
        static_cast<size_t>(lat_buf.shape[0]),
        sun_radius_km,
        moon_radius_km,
        overlap_max.mutable_data(),
        central_max.mutable_data(),
        magnitude_max.mutable_data()
    );
}

py::tuple solar_observer_quantities_batch_vectors_py(
    py::array_t<double> sun_xyz,
    py::array_t<double> moon_xyz,
    double gast_deg,
    py::array_t<double> lats_deg,
    py::array_t<double> lons_deg,
    double sun_radius_km,
    double moon_radius_km
) {
    auto sun_buf = sun_xyz.request();
    auto moon_buf = moon_xyz.request();
    auto lat_buf = lats_deg.request();
    auto lon_buf = lons_deg.request();

    if (sun_buf.ndim != 1 || moon_buf.ndim != 1 || sun_buf.shape[0] != 3 || moon_buf.shape[0] != 3) {
        throw std::runtime_error("solar_observer_quantities_batch_vectors expects length-3 state arrays.");
    }
    if (lat_buf.shape[0] != lon_buf.shape[0]) {
        throw std::runtime_error("solar_observer_quantities_batch_vectors received inconsistent observer arrays.");
    }

    py::array_t<double> raw_ov(lat_buf.size);
    py::array_t<double> alt(lat_buf.size);
    py::array_t<double> ha(lat_buf.size);

    solar_observer_quantities_batch_vectors(
        static_cast<const double*>(sun_buf.ptr),
        static_cast<const double*>(moon_buf.ptr),
        gast_deg,
        static_cast<const double*>(lat_buf.ptr),
        static_cast<const double*>(lon_buf.ptr),
        static_cast<size_t>(lat_buf.size),
        sun_radius_km,
        moon_radius_km,
        raw_ov.mutable_data(),
        alt.mutable_data(),
        ha.mutable_data()
    );
    return py::make_tuple(raw_ov, alt, ha);
}

py::tuple solar_cross_track_limit_band_py(
    const IEvaluator& sun,
    const IEvaluator& moon,
    py::array_t<double> jds,
    py::array_t<double> gasts_deg,
    py::array_t<double> center_lats_deg,
    py::array_t<double> center_lons_deg,
    int margin_kind,
    double max_distance_km,
    double sun_radius_km,
    double moon_radius_km
) {
    auto roots = solar_cross_track_limit_band(
        sun, moon,
        jds.data(), gasts_deg.data(), center_lats_deg.data(), center_lons_deg.data(),
        static_cast<size_t>(jds.size()),
        margin_kind, max_distance_km, sun_radius_km, moon_radius_km
    );

    py::array_t<double> south_lats(roots.size());
    py::array_t<double> south_lons(roots.size());
    py::array_t<double> north_lats(roots.size());
    py::array_t<double> north_lons(roots.size());
    auto* slat = south_lats.mutable_data();
    auto* slon = south_lons.mutable_data();
    auto* nlat = north_lats.mutable_data();
    auto* nlon = north_lons.mutable_data();
    for (size_t i = 0; i < roots.size(); ++i) {
        slat[i] = roots[i].south_lat_deg;
        slon[i] = roots[i].south_lon_deg;
        nlat[i] = roots[i].north_lat_deg;
        nlon[i] = roots[i].north_lon_deg;
    }
    return py::make_tuple(south_lats, south_lons, north_lats, north_lons);
}

py::tuple solar_cross_track_limit_band_vectors_py(
    py::array_t<double> sun_xyz_series,
    py::array_t<double> moon_xyz_series,
    py::array_t<double> gasts_deg,
    py::array_t<double> center_lats_deg,
    py::array_t<double> center_lons_deg,
    int margin_kind,
    double max_distance_km,
    double sun_radius_km,
    double moon_radius_km
) {
    auto sun_buf = sun_xyz_series.request();
    auto moon_buf = moon_xyz_series.request();
    auto gast_buf = gasts_deg.request();
    auto lat_buf = center_lats_deg.request();
    auto lon_buf = center_lons_deg.request();
    if (sun_buf.ndim != 2 || moon_buf.ndim != 2 || sun_buf.shape[1] != 3 || moon_buf.shape[1] != 3) {
        throw std::runtime_error("solar_cross_track_limit_band_vectors expects (n, 3) state arrays.");
    }
    if (sun_buf.shape[0] != moon_buf.shape[0] || sun_buf.shape[0] != gast_buf.shape[0]
        || sun_buf.shape[0] != lat_buf.shape[0] || sun_buf.shape[0] != lon_buf.shape[0]) {
        throw std::runtime_error("solar_cross_track_limit_band_vectors received inconsistent array lengths.");
    }

    auto roots = solar_cross_track_limit_band_vectors(
        static_cast<const double*>(sun_buf.ptr),
        static_cast<const double*>(moon_buf.ptr),
        static_cast<const double*>(gast_buf.ptr),
        static_cast<const double*>(lat_buf.ptr),
        static_cast<const double*>(lon_buf.ptr),
        static_cast<size_t>(gast_buf.shape[0]),
        margin_kind,
        max_distance_km,
        sun_radius_km,
        moon_radius_km
    );

    py::array_t<double> south_lats(roots.size());
    py::array_t<double> south_lons(roots.size());
    py::array_t<double> north_lats(roots.size());
    py::array_t<double> north_lons(roots.size());
    auto* slat = south_lats.mutable_data();
    auto* slon = south_lons.mutable_data();
    auto* nlat = north_lats.mutable_data();
    auto* nlon = north_lons.mutable_data();
    for (size_t i = 0; i < roots.size(); ++i) {
        slat[i] = roots[i].south_lat_deg;
        slon[i] = roots[i].south_lon_deg;
        nlat[i] = roots[i].north_lat_deg;
        nlon[i] = roots[i].north_lon_deg;
    }
    return py::make_tuple(south_lats, south_lons, north_lats, north_lons);
}

py::tuple solar_cross_track_magnitude_contour_py(
    const IEvaluator& sun,
    const IEvaluator& moon,
    py::array_t<double> jds,
    py::array_t<double> gasts_deg,
    py::array_t<double> center_lats_deg,
    py::array_t<double> center_lons_deg,
    double threshold,
    double max_distance_km,
    double sun_radius_km,
    double moon_radius_km
) {
    auto roots = solar_cross_track_magnitude_contour(
        sun, moon,
        jds.data(), gasts_deg.data(), center_lats_deg.data(), center_lons_deg.data(),
        static_cast<size_t>(jds.size()),
        threshold, max_distance_km, sun_radius_km, moon_radius_km
    );

    py::array_t<double> south_lats(roots.size());
    py::array_t<double> south_lons(roots.size());
    py::array_t<double> north_lats(roots.size());
    py::array_t<double> north_lons(roots.size());
    auto* slat = south_lats.mutable_data();
    auto* slon = south_lons.mutable_data();
    auto* nlat = north_lats.mutable_data();
    auto* nlon = north_lons.mutable_data();
    for (size_t i = 0; i < roots.size(); ++i) {
        slat[i] = roots[i].south_lat_deg;
        slon[i] = roots[i].south_lon_deg;
        nlat[i] = roots[i].north_lat_deg;
        nlon[i] = roots[i].north_lon_deg;
    }
    return py::make_tuple(south_lats, south_lons, north_lats, north_lons);
}

py::tuple solar_cross_track_magnitude_contour_vectors_py(
    py::array_t<double> sun_xyz_series,
    py::array_t<double> moon_xyz_series,
    py::array_t<double> gasts_deg,
    py::array_t<double> center_lats_deg,
    py::array_t<double> center_lons_deg,
    double threshold,
    double max_distance_km,
    double sun_radius_km,
    double moon_radius_km
) {
    auto sun_buf = sun_xyz_series.request();
    auto moon_buf = moon_xyz_series.request();
    auto gast_buf = gasts_deg.request();
    auto lat_buf = center_lats_deg.request();
    auto lon_buf = center_lons_deg.request();
    if (sun_buf.ndim != 2 || moon_buf.ndim != 2 || sun_buf.shape[1] != 3 || moon_buf.shape[1] != 3) {
        throw std::runtime_error("solar_cross_track_magnitude_contour_vectors expects (n, 3) state arrays.");
    }
    if (sun_buf.shape[0] != moon_buf.shape[0] || sun_buf.shape[0] != gast_buf.shape[0]
        || sun_buf.shape[0] != lat_buf.shape[0] || sun_buf.shape[0] != lon_buf.shape[0]) {
        throw std::runtime_error("solar_cross_track_magnitude_contour_vectors received inconsistent array lengths.");
    }

    auto roots = solar_cross_track_magnitude_contour_vectors(
        static_cast<const double*>(sun_buf.ptr),
        static_cast<const double*>(moon_buf.ptr),
        static_cast<const double*>(gast_buf.ptr),
        static_cast<const double*>(lat_buf.ptr),
        static_cast<const double*>(lon_buf.ptr),
        static_cast<size_t>(gast_buf.shape[0]),
        threshold,
        max_distance_km,
        sun_radius_km,
        moon_radius_km
    );

    py::array_t<double> south_lats(roots.size());
    py::array_t<double> south_lons(roots.size());
    py::array_t<double> north_lats(roots.size());
    py::array_t<double> north_lons(roots.size());
    auto* slat = south_lats.mutable_data();
    auto* slon = south_lons.mutable_data();
    auto* nlat = north_lats.mutable_data();
    auto* nlon = north_lons.mutable_data();
    for (size_t i = 0; i < roots.size(); ++i) {
        slat[i] = roots[i].south_lat_deg;
        slon[i] = roots[i].south_lon_deg;
        nlat[i] = roots[i].north_lat_deg;
        nlon[i] = roots[i].north_lon_deg;
    }
    return py::make_tuple(south_lats, south_lons, north_lats, north_lons);
}

} // namespace

PYBIND11_MODULE(_moira_native, m) {
    m.doc() = "Moira Native Backend Forge";

    // --- Evaluators ---
    py::class_<IEvaluator, std::shared_ptr<IEvaluator>>(m, "IEvaluator")
        .def("evaluate", [](IEvaluator& self, double jd) {
            double res[6];
            self.evaluate(jd, res);
            std::vector<double> out(res, res + 6);
            return vector_to_py_list(out);
        })
        .def("evaluate_batch", [](IEvaluator& self, py::array_t<double> jds) {
            auto buf = jds.request();
            size_t count = buf.size;
            const double* ptr = static_cast<const double*>(buf.ptr);
            
            py::array_t<double> out({count, static_cast<size_t>(6)});
            auto out_ptr = static_cast<double*>(out.request().ptr);
            
            self.evaluate_batch(ptr, count, out_ptr);
            return out;
        });

    py::class_<ChebyshevEvaluator, IEvaluator, std::shared_ptr<ChebyshevEvaluator>>(m, "ChebyshevEvaluator")
        .def(py::init<double, double, size_t, size_t, size_t, std::vector<double>>());

    py::class_<LagrangeEvaluator, IEvaluator, std::shared_ptr<LagrangeEvaluator>>(m, "LagrangeEvaluator")
        .def(py::init<std::vector<double>, std::vector<double>, size_t>());

    py::class_<RelativeEvaluator, IEvaluator, std::shared_ptr<RelativeEvaluator>>(m, "RelativeEvaluator")
        .def(py::init<std::shared_ptr<IEvaluator>, std::shared_ptr<IEvaluator>>());

    m.def("longitude_difference", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, double jd) {
        return longitude_difference(*t1, *t2, *obs, jd);
    });

    m.def("angular_separation", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, double jd) {
        return angular_separation(*t1, *t2, *obs, jd);
    });

    m.def("find_conjunctions", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, double a, double b, double dt) {
        auto f = [&](double jd) { return longitude_difference(*t1, *t2, *obs, jd); };
        return find_roots(f, a, b, dt);
    });

    m.def("find_aspects", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, double aspect_deg, double a, double b, double dt) {
        auto f = [&](double jd) { 
            double diff = longitude_difference(*t1, *t2, *obs, jd);
            double val = diff - aspect_deg;
            while (val > 180.0) val -= 360.0;
            while (val <= -180.0) val += 360.0;
            return val;
        };
        return find_roots(f, a, b, dt);
    });

    m.def("find_stations", [](std::shared_ptr<IEvaluator> target, std::shared_ptr<IEvaluator> obs, double a, double b, double dt) {
        return find_stations(*target, *obs, a, b, dt);
    });

    m.def("find_ingresses", [](std::shared_ptr<IEvaluator> target, std::shared_ptr<IEvaluator> obs, double a, double b, double dt) {
        return find_ingresses(*target, *obs, a, b, dt);
    });

    py::class_<OccultationEvent>(m, "OccultationEvent")
        .def_readonly("t_mid", &OccultationEvent::t_mid)
        .def_readonly("separation_min", &OccultationEvent::separation_min)
        .def_readonly("t_start", &OccultationEvent::t_start)
        .def_readonly("t_end", &OccultationEvent::t_end)
        .def_readonly("is_total", &OccultationEvent::is_total);

    m.def("find_occultations", &find_occultations, 
          py::arg("target1"), py::arg("r1_km"),
          py::arg("target2"), py::arg("r2_km"),
          py::arg("observer"), py::arg("a"), py::arg("b"), py::arg("dt"));

    py::enum_<EventType>(m, "EventType")
        .value("STATION", EventType::STATION)
        .value("INGRESS", EventType::INGRESS)
        .value("OCCULTATION", EventType::OCCULTATION)
        .export_values();

    py::class_<SearchResult>(m, "SearchResult")
        .def_readonly("type", &SearchResult::type)
        .def_readonly("jd", &SearchResult::jd)
        .def_readonly("description", &SearchResult::description)
        .def_readonly("value", &SearchResult::value);

    py::class_<SearchPool>(m, "SearchPool")
        .def(py::init<>())
        .def("add_station_task", &SearchPool::add_station_task)
        .def("add_ingress_task", &SearchPool::add_ingress_task)
        .def("add_occultation_task", &SearchPool::add_occultation_task)
        .def("run", &SearchPool::run, py::arg("a"), py::arg("b"), py::arg("dt") = 0.5);


    // --- Geometry ---
    py::class_<Vec3>(m, "Vec3")
        .def(py::init<double, double, double>())
        .def_property("x", [](Vec3& v) { return v[0]; }, [](Vec3& v, double val) { v[0] = val; })
        .def_property("y", [](Vec3& v) { return v[1]; }, [](Vec3& v, double val) { v[1] = val; })
        .def_property("z", [](Vec3& v) { return v[2]; }, [](Vec3& v, double val) { v[2] = val; })
        .def("norm", &Vec3::norm)
        .def("unit", &Vec3::unit);

    py::class_<Mat3>(m, "Mat3")
        .def(py::init<>())
        .def(py::init<std::array<std::array<double, 3>, 3>>())
        .def_readwrite("data", &Mat3::data)
        .def_static("identity", &Mat3::identity)
        .def_static("mul_vec", py::overload_cast<const Mat3&, const Vec3&>(&Mat3::mul))
        .def_static("mul_mat", py::overload_cast<const Mat3&, const Mat3&>(&Mat3::mul))
        .def_static("compose", &Mat3::compose)
        .def("transpose", &Mat3::transpose)
        .def("determinant", &Mat3::determinant)
        .def("inverse", &Mat3::inverse)
        .def("is_orthonormal", &Mat3::is_orthonormal, py::arg("epsilon") = 1e-12)
        .def("orthonormalize", &Mat3::orthonormalize)
        .def_static("rot_x", &Mat3::rot_x)
        .def_static("rot_y", &Mat3::rot_y)
        .def_static("rot_z", &Mat3::rot_z);

    // --- Julian ---
    m.def("julian_day", &julian_day, py::arg("year"), py::arg("month"), py::arg("day"), py::arg("hour") = 0.0);
    m.def("calendar_from_jd", &calendar_from_jd, py::arg("jd"));
    m.def("earth_rotation_angle", &earth_rotation_angle, py::arg("jd_ut"));
    m.def("greenwich_mean_sidereal_time", &greenwich_mean_sidereal_time, py::arg("jd_ut"));
    m.def("apparent_sidereal_time", &apparent_sidereal_time, py::arg("jd_ut"), py::arg("nutation_longitude"), py::arg("obliquity"));

    // --- Interpolation ---
    m.def("horner", [](py::array_t<double> coeffs, double x) {
        auto buf = coeffs.request();
        double res = 0.0;
        const double* ptr = static_cast<const double*>(buf.ptr);
        for (int i = static_cast<int>(buf.size) - 1; i >= 0; --i) {
            res = res * x + ptr[i];
        }
        return res;
    }, py::arg("coeffs"), py::arg("x"));
    m.def("lagrange_interpolate", [](py::array_t<double> x_pts, py::array_t<double> y_pts, double x) {
        auto buf_x = x_pts.request();
        auto buf_y = y_pts.request();
        if (buf_x.size != buf_y.size) throw std::runtime_error("Lagrange points must have same size");
        return lagrange_interpolate(static_cast<const double*>(buf_x.ptr), static_cast<const double*>(buf_y.ptr), buf_x.size, x);
    }, py::arg("x_pts"), py::arg("y_pts"), py::arg("x"));
    
    m.def("spk_chebyshev_record", &spk_chebyshev_record_py, py::arg("coeff_record"), py::arg("s"));
    m.def("spk_chebyshev_record_with_derivative", &spk_chebyshev_record_with_derivative_py, py::arg("coeff_record"), py::arg("s"), py::arg("derivative_scale"));
    
    m.def("spk_chebyshev_series_record", &spk_chebyshev_series_record_py, py::arg("coefficients"), py::arg("record_index"), py::arg("s"));
    m.def("spk_chebyshev_series_record_with_derivative", &spk_chebyshev_series_record_with_derivative_py, py::arg("coefficients"), py::arg("record_index"), py::arg("s"), py::arg("derivative_scale"));
    
    m.def("spk_chebyshev_series_bulk_evaluate", &spk_chebyshev_series_bulk_evaluate_py, 
          py::arg("coeff_series"), py::arg("record_indices"), py::arg("s_values"), py::arg("derivative_scales"), py::arg("need_rates"));

    m.def("spk_type13_record", [](py::array_t<double> epochs, py::array_t<double> states, size_t window_size, double jd) {
        auto buf_e = epochs.request();
        auto buf_s = states.request();
        
        std::vector<double> result(6);
        spk_type13_record_inplace(
            static_cast<const double*>(buf_e.ptr),
            static_cast<const double*>(buf_s.ptr),
            static_cast<size_t>(buf_e.size),
            window_size,
            jd,
            result.data()
        );
        return vector_to_py_list(result);
    }, py::arg("epochs"), py::arg("states"), py::arg("window_size"), py::arg("jd"));

    m.def("read_daf_catalog", &read_daf_catalog_py, py::arg("path"));
    m.def("read_spk_chebyshev_segment_payload", &read_spk_chebyshev_segment_payload_py, py::arg("path"), py::arg("start_i"), py::arg("end_i"), py::arg("little_endian"), py::arg("data_type"));
    m.def("read_spk_type13_segment_payload", &read_spk_type13_segment_payload_py, py::arg("path"), py::arg("start_i"), py::arg("end_i"), py::arg("little_endian"));

    // --- Solvers ---
    m.def("brent_root", &brent_root, py::arg("f"), py::arg("a"), py::arg("b"), py::arg("tol") = 1e-12, py::arg("max_iter") = 100);
    m.def("brent_minimize", &brent_minimize, py::arg("f"), py::arg("a"), py::arg("b"), py::arg("tol") = 1e-12, py::arg("max_iter") = 100);
    m.def("newton_safe", &newton_safe, py::arg("f"), py::arg("df"), py::arg("a"), py::arg("b"), py::arg("tol") = 1e-12, py::arg("max_iter") = 100);
    m.def("find_roots", &find_roots, py::arg("f"), py::arg("a"), py::arg("b"), py::arg("dt"), py::arg("tol") = 1e-12);
    m.def("find_extrema", &find_extrema, py::arg("f"), py::arg("a"), py::arg("b"), py::arg("dt"), py::arg("tol") = 1e-12);
    m.def("solve_light_time", &solve_light_time, py::arg("target_ephemeris"), py::arg("observer_pos"), py::arg("t_obs"), py::arg("initial_tau") = 0.0, py::arg("tol") = 1e-12, py::arg("max_iter") = 10);

    // --- Events & Separation ---
    m.def("angular_separation", py::overload_cast<const IEvaluator&, const IEvaluator&, const IEvaluator&, double>(&angular_separation));
    m.def("angular_separation", py::overload_cast<const Vec3&, const Vec3&>(&angular_separation));
    
    m.def("find_solar_eclipses", &find_solar_eclipses, py::arg("sun"), py::arg("moon"), py::arg("jd_start"), py::arg("jd_end"), py::arg("r_sun_km"), py::arg("r_moon_km"), py::arg("dt_days"));
    m.def("find_lunar_eclipses", &find_lunar_eclipses, py::arg("sun"), py::arg("moon"), py::arg("jd_start"), py::arg("jd_end"), py::arg("r_sun_km"), py::arg("r_moon_km"), py::arg("r_earth_km"), py::arg("dt_days"));
    
    py::class_<Event>(m, "Event")
        .def_readwrite("type", &Event::type)
        .def_readwrite("t_mid", &Event::t_mid)
        .def_readwrite("t_start", &Event::t_start)
        .def_readwrite("t_end", &Event::t_end)
        .def_readwrite("value", &Event::value)
        .def_readwrite("description", &Event::description);

    // --- Coordinates ---
    m.def("radec_to_vec3", &radec_to_vec3, py::arg("ra_deg"), py::arg("dec_deg"), py::arg("dist") = 1.0);
    m.def("vec3_to_radec", &vec3_to_radec, py::arg("v"));
    m.def("lonlat_to_vec3", &lonlat_to_vec3, py::arg("lon_deg"), py::arg("lat_deg"), py::arg("dist") = 1.0);
    m.def("vec3_to_lonlat", &vec3_to_lonlat, py::arg("v"));
    m.def("ecliptic_to_equatorial", &ecliptic_to_equatorial, py::arg("lon_deg"), py::arg("lat_deg"), py::arg("obliquity_deg"));
    m.def("equatorial_to_ecliptic", &equatorial_to_ecliptic, py::arg("ra_deg"), py::arg("dec_deg"), py::arg("obliquity_deg"));

    // --- Topocentric ---
    py::class_<TopocentricEvaluator, IEvaluator, std::shared_ptr<TopocentricEvaluator>>(m, "TopocentricEvaluator")
        .def(py::init<std::shared_ptr<IEvaluator>, double, double, double>());

    // --- Cartography ---
    m.def("solar_cartography_grid_sweep", &solar_cartography_grid_sweep_py,
        py::arg("sun"), py::arg("moon"), py::arg("jds"), py::arg("gasts_deg"),
        py::arg("lats_deg"), py::arg("lons_deg"),
        py::arg("sun_radius_km"), py::arg("moon_radius_km"),
        py::arg("overlap_max"), py::arg("central_max"), py::arg("magnitude_max"));

    m.def("lunar_cartography_grid_sweep", &lunar_cartography_grid_sweep_py,
        py::arg("sun"), py::arg("moon"), py::arg("jds"), py::arg("gasts_deg"),
        py::arg("magnitudes_base"), py::arg("lats_deg"), py::arg("lons_deg"),
        py::arg("penumbral_max"), py::arg("partial_max"), py::arg("total_max"), py::arg("magnitude_max"),
        py::arg("u1_u4") = py::none(), py::arg("u2_u3") = py::none());

    m.def("solar_find_greatest_eclipse_location", &solar_find_greatest_eclipse_location_py,
        py::arg("sun"), py::arg("moon"), py::arg("jd"), py::arg("gast_deg"),
        "Find (lat, lon, separation_deg) of the point of greatest eclipse at a fixed JD."
        " Exact port of Python _solve_solar_greatest_location().");

    m.def("solar_centerline_batch", &solar_centerline_batch_py,
        py::arg("sun"), py::arg("moon"), py::arg("jds"), py::arg("gasts_deg"),
        "Batch centerline solve: returns list of (lat, lon, sep) for each JD in jds.");

    m.def("solar_observer_quantities_batch", &solar_observer_quantities_batch_py,
        py::arg("sun"), py::arg("moon"), py::arg("jd"), py::arg("gast_deg"),
        py::arg("lats_deg"), py::arg("lons_deg"),
        py::arg("sun_radius_km"), py::arg("moon_radius_km"),
        "Compute (raw_overlap, altitude, hour_angle) for multiple observers at a fixed JD.");

    m.def("solar_cartography_grid_sweep_vectors", &solar_cartography_grid_sweep_vectors_py,
        py::arg("sun_xyz_series"), py::arg("moon_xyz_series"), py::arg("gasts_deg"),
        py::arg("lats_deg"), py::arg("lons_deg"),
        py::arg("sun_radius_km"), py::arg("moon_radius_km"),
        py::arg("overlap_max"), py::arg("central_max"), py::arg("magnitude_max"),
        "Aggregate solar cartography maxima from apparent state-vector series.");

    m.def("solar_observer_quantities_batch_vectors", &solar_observer_quantities_batch_vectors_py,
        py::arg("sun_xyz"), py::arg("moon_xyz"), py::arg("gast_deg"),
        py::arg("lats_deg"), py::arg("lons_deg"),
        py::arg("sun_radius_km"), py::arg("moon_radius_km"),
        "Compute solar observer quantities from apparent state vectors.");

    m.def("solar_cross_track_limit_band", &solar_cross_track_limit_band_py,
        py::arg("sun"), py::arg("moon"), py::arg("jds"), py::arg("gasts_deg"),
        py::arg("center_lats_deg"), py::arg("center_lons_deg"),
        py::arg("margin_kind"), py::arg("max_distance_km"),
        py::arg("sun_radius_km"), py::arg("moon_radius_km"),
        "Solve solar cross-track partial/central boundary roots from a centerline.");

    m.def("solar_cross_track_limit_band_vectors", &solar_cross_track_limit_band_vectors_py,
        py::arg("sun_xyz_series"), py::arg("moon_xyz_series"), py::arg("gasts_deg"),
        py::arg("center_lats_deg"), py::arg("center_lons_deg"),
        py::arg("margin_kind"), py::arg("max_distance_km"),
        py::arg("sun_radius_km"), py::arg("moon_radius_km"),
        "Solve solar cross-track partial/central boundary roots from apparent state-vector series.");

    m.def("solar_cross_track_magnitude_contour", &solar_cross_track_magnitude_contour_py,
        py::arg("sun"), py::arg("moon"), py::arg("jds"), py::arg("gasts_deg"),
        py::arg("center_lats_deg"), py::arg("center_lons_deg"),
        py::arg("threshold"), py::arg("max_distance_km"),
        py::arg("sun_radius_km"), py::arg("moon_radius_km"),
        "Solve solar cross-track magnitude contour roots from a centerline.");

    m.def("solar_cross_track_magnitude_contour_vectors", &solar_cross_track_magnitude_contour_vectors_py,
        py::arg("sun_xyz_series"), py::arg("moon_xyz_series"), py::arg("gasts_deg"),
        py::arg("center_lats_deg"), py::arg("center_lons_deg"),
        py::arg("threshold"), py::arg("max_distance_km"),
        py::arg("sun_radius_km"), py::arg("moon_radius_km"),
        "Solve solar cross-track magnitude contour roots from apparent state-vector series.");
}
