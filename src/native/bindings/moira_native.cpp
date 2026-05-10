#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include <pybind11/numpy.h>
#include <array>
#include <mutex>
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
#include "lola.hpp"

namespace py = pybind11;
using namespace moira::native;

namespace {

struct NativeNutationTerm {
    double c1 = 0.0;
    double c2 = 0.0;
    std::array<int, 14> args{};
    size_t arg_count = 0;
};

std::vector<NativeNutationTerm> g_native_nutation_ls_terms;
std::vector<NativeNutationTerm> g_native_nutation_pl_terms;
size_t g_native_nutation_ls_j0_count = 0;
size_t g_native_nutation_pl_j0_count = 0;
bool g_native_nutation_tables_ready = false;
std::mutex g_native_nutation_mutex;

constexpr double NUTATION_ARCSEC = 3.141592653589793238462643383279502884 / 648000.0;
constexpr double NUTATION_UAS2DEG = 1e-6 / 3600.0;

std::vector<double> load_double_vector(const py::handle& src_obj, const char* label) {
    py::sequence src = py::reinterpret_borrow<py::sequence>(src_obj);
    std::vector<double> out;
    out.reserve(static_cast<size_t>(py::len(src)));
    for (const py::handle& item : src) {
        out.push_back(py::cast<double>(item));
    }
    if (out.empty()) {
        throw std::runtime_error(std::string(label) + " cannot be empty");
    }
    return out;
}

std::vector<int32_t> load_int32_vector(const py::handle& src_obj, const char* label) {
    py::sequence src = py::reinterpret_borrow<py::sequence>(src_obj);
    std::vector<int32_t> out;
    out.reserve(static_cast<size_t>(py::len(src)));
    for (const py::handle& item : src) {
        out.push_back(py::cast<int32_t>(item));
    }
    if (out.empty()) {
        throw std::runtime_error(std::string(label) + " cannot be empty");
    }
    return out;
}

struct DenseMatrixView {
    std::vector<double> values;
    size_t rows = 0;
    size_t cols = 0;
};

DenseMatrixView load_double_matrix(const py::handle& src_obj, const char* label) {
    py::sequence rows_src = py::reinterpret_borrow<py::sequence>(src_obj);
    DenseMatrixView out;
    out.rows = static_cast<size_t>(py::len(rows_src));
    if (out.rows == 0) {
        throw std::runtime_error(std::string(label) + " cannot be empty");
    }

    py::sequence first_row = py::reinterpret_borrow<py::sequence>(rows_src[0]);
    out.cols = static_cast<size_t>(py::len(first_row));
    if (out.cols == 0) {
        throw std::runtime_error(std::string(label) + " rows cannot be empty");
    }

    out.values.reserve(out.rows * out.cols);
    for (const py::handle& row_obj : rows_src) {
        py::sequence row = py::reinterpret_borrow<py::sequence>(row_obj);
        if (static_cast<size_t>(py::len(row)) != out.cols) {
            throw std::runtime_error(std::string(label) + " rows must have consistent length");
        }
        for (const py::handle& item : row) {
            out.values.push_back(py::cast<double>(item));
        }
    }
    return out;
}

struct DenseTensor3View {
    std::vector<double> values;
    size_t dim0 = 0;
    size_t dim1 = 0;
    size_t dim2 = 0;
};

DenseTensor3View load_double_tensor3(const py::handle& src_obj, const char* label) {
    py::sequence outer = py::reinterpret_borrow<py::sequence>(src_obj);
    DenseTensor3View out;
    out.dim0 = static_cast<size_t>(py::len(outer));
    if (out.dim0 == 0) {
        throw std::runtime_error(std::string(label) + " cannot be empty");
    }

    py::sequence first_mid = py::reinterpret_borrow<py::sequence>(outer[0]);
    out.dim1 = static_cast<size_t>(py::len(first_mid));
    if (out.dim1 == 0) {
        throw std::runtime_error(std::string(label) + " inner dimensions cannot be empty");
    }

    py::sequence first_inner = py::reinterpret_borrow<py::sequence>(first_mid[0]);
    out.dim2 = static_cast<size_t>(py::len(first_inner));
    if (out.dim2 == 0) {
        throw std::runtime_error(std::string(label) + " innermost dimension cannot be empty");
    }

    out.values.reserve(out.dim0 * out.dim1 * out.dim2);
    for (const py::handle& mid_obj : outer) {
        py::sequence mid = py::reinterpret_borrow<py::sequence>(mid_obj);
        if (static_cast<size_t>(py::len(mid)) != out.dim1) {
            throw std::runtime_error(std::string(label) + " mid dimensions must have consistent length");
        }
        for (const py::handle& inner_obj : mid) {
            py::sequence inner = py::reinterpret_borrow<py::sequence>(inner_obj);
            if (static_cast<size_t>(py::len(inner)) != out.dim2) {
                throw std::runtime_error(std::string(label) + " inner dimensions must have consistent length");
            }
            for (const py::handle& item : inner) {
                out.values.push_back(py::cast<double>(item));
            }
        }
    }
    return out;
}

py::list matrix_to_py_list(const double* values, size_t rows, size_t cols) {
    py::list out;
    for (size_t i = 0; i < rows; ++i) {
        py::list row;
        for (size_t j = 0; j < cols; ++j) {
            row.append(values[i * cols + j]);
        }
        out.append(std::move(row));
    }
    return out;
}

NativeNutationTerm load_native_nutation_term(const py::handle& row_obj) {
    py::sequence row = py::reinterpret_borrow<py::sequence>(row_obj);
    const size_t size = static_cast<size_t>(py::len(row));
    if (size < 3) {
        throw std::runtime_error("Nutation term rows must contain at least 3 entries");
    }

    NativeNutationTerm term;
    term.c1 = py::cast<double>(row[0]);
    term.c2 = py::cast<double>(row[1]);
    term.arg_count = size - 2;
    if (term.arg_count > term.args.size()) {
        throw std::runtime_error("Nutation term rows exceed the supported 14 arguments");
    }
    for (size_t i = 0; i < term.arg_count; ++i) {
        term.args[i] = py::cast<int>(row[i + 2]);
    }
    return term;
}

void set_nutation_2000a_tables_py(
    const py::sequence& ls_terms_src,
    const py::sequence& pl_terms_src,
    size_t ls_j0_count,
    size_t pl_j0_count
) {
    std::lock_guard<std::mutex> lock(g_native_nutation_mutex);

    std::vector<NativeNutationTerm> ls_terms;
    std::vector<NativeNutationTerm> pl_terms;
    ls_terms.reserve(static_cast<size_t>(py::len(ls_terms_src)));
    pl_terms.reserve(static_cast<size_t>(py::len(pl_terms_src)));

    for (const py::handle& row : ls_terms_src) {
        ls_terms.push_back(load_native_nutation_term(row));
    }
    for (const py::handle& row : pl_terms_src) {
        pl_terms.push_back(load_native_nutation_term(row));
    }

    g_native_nutation_ls_terms = std::move(ls_terms);
    g_native_nutation_pl_terms = std::move(pl_terms);
    g_native_nutation_ls_j0_count = ls_j0_count;
    g_native_nutation_pl_j0_count = pl_j0_count;
    g_native_nutation_tables_ready = true;
}

std::array<double, 14> native_fundamental_args(double T) {
    const double tau = 2.0 * 3.141592653589793238462643383279502884;

    const double l = (485868.249036
        + T * (1717915923.2178
        + T * (31.8792
        + T * (0.051635
        + T * (-0.00024470))))) * NUTATION_ARCSEC;

    const double lp = (1287104.793048
        + T * (129596581.0481
        + T * (-0.5532
        + T * (0.000136
        + T * (-0.00001149))))) * NUTATION_ARCSEC;

    const double F = (335779.526232
        + T * (1739527262.8478
        + T * (-12.7512
        + T * (-0.001037
        + T * (0.00000417))))) * NUTATION_ARCSEC;

    const double D = (1072260.703692
        + T * (1602961601.2090
        + T * (-6.3706
        + T * (0.006593
        + T * (-0.00003169))))) * NUTATION_ARCSEC;

    const double Om = (450160.398036
        + T * (-6962890.5431
        + T * (7.4722
        + T * (0.007702
        + T * (-0.00005939))))) * NUTATION_ARCSEC;

    auto wrap_tau = [tau](double value) {
        const double wrapped = std::fmod(value, tau);
        return wrapped < 0.0 ? wrapped + tau : wrapped;
    };

    return {
        l,
        lp,
        F,
        D,
        Om,
        wrap_tau(4.402608842 + 2608.7903141574 * T),
        wrap_tau(3.176146697 + 1021.3285546211 * T),
        wrap_tau(1.753470314 + 628.3075849991 * T),
        wrap_tau(6.203480913 + 334.0612426700 * T),
        wrap_tau(0.599546497 + 52.9690962641 * T),
        wrap_tau(0.874016757 + 21.3299104960 * T),
        wrap_tau(5.481293872 + 7.4781598567 * T),
        wrap_tau(5.311886287 + 3.8133035638 * T),
        wrap_tau(0.02438175 + 0.00000538691 * T),
    };
}

double native_nutation_argument(const NativeNutationTerm& term, const std::array<double, 14>& fa) {
    double arg = 0.0;
    for (size_t i = 0; i < term.arg_count; ++i) {
        arg += static_cast<double>(term.args[i]) * fa[i];
    }
    return arg;
}

py::tuple nutation_2000a_py(double jd_tt) {
    std::lock_guard<std::mutex> lock(g_native_nutation_mutex);
    if (!g_native_nutation_tables_ready) {
        throw std::runtime_error("Native nutation tables are not registered");
    }

    const double T = (jd_tt - 2451545.0) / 36525.0;
    const std::array<double, 14> fa = native_fundamental_args(T);

    double dpsi = 0.0;
    for (size_t i = 0; i < g_native_nutation_ls_terms.size(); ++i) {
        const NativeNutationTerm& term = g_native_nutation_ls_terms[i];
        const double arg = native_nutation_argument(term, fa);
        if (i < g_native_nutation_ls_j0_count) {
            dpsi += term.c1 * std::sin(arg) + term.c2 * std::cos(arg);
        } else {
            dpsi += T * (term.c1 * std::sin(arg) + term.c2 * std::cos(arg));
        }
    }

    double deps = 0.0;
    for (size_t i = 0; i < g_native_nutation_pl_terms.size(); ++i) {
        const NativeNutationTerm& term = g_native_nutation_pl_terms[i];
        const double arg = native_nutation_argument(term, fa);
        if (i < g_native_nutation_pl_j0_count) {
            deps += term.c2 * std::cos(arg) + term.c1 * std::sin(arg);
        } else {
            deps += T * (term.c2 * std::cos(arg) + term.c1 * std::sin(arg));
        }
    }

    return py::make_tuple(dpsi * NUTATION_UAS2DEG, deps * NUTATION_UAS2DEG);
}

py::list vector_to_py_list(const std::vector<double>& values) {
    py::list out;
    for (double v : values) out.append(v);
    return out;
}

void load_mat3(const py::sequence& src, double out[3][3]) {
    if (py::len(src) != 3) {
        throw std::runtime_error("mat3 must have exactly 3 rows");
    }
    for (size_t i = 0; i < 3; ++i) {
        py::sequence row = py::reinterpret_borrow<py::sequence>(src[i]);
        if (py::len(row) != 3) {
            throw std::runtime_error("mat3 rows must have exactly 3 columns");
        }
        for (size_t j = 0; j < 3; ++j) {
            out[i][j] = py::cast<double>(row[j]);
        }
    }
}

void load_vec3(const py::sequence& src, double out[3]) {
    if (py::len(src) != 3) {
        throw std::runtime_error("vec3 must have exactly 3 components");
    }
    for (size_t i = 0; i < 3; ++i) {
        out[i] = py::cast<double>(src[i]);
    }
}

py::tuple mat3_to_py_tuple(const double src[3][3]) {
    return py::make_tuple(
        py::make_tuple(src[0][0], src[0][1], src[0][2]),
        py::make_tuple(src[1][0], src[1][1], src[1][2]),
        py::make_tuple(src[2][0], src[2][1], src[2][2])
    );
}

py::tuple vec3_to_py_tuple(const double src[3]) {
    return py::make_tuple(src[0], src[1], src[2]);
}

py::tuple rotation_matrix_multiply_py(const py::sequence& a_src, const py::sequence& b_src) {
    double a[3][3];
    double b[3][3];
    double out[3][3];
    load_mat3(a_src, a);
    load_mat3(b_src, b);

    for (size_t i = 0; i < 3; ++i) {
        for (size_t j = 0; j < 3; ++j) {
            out[i][j] = (
                a[i][0] * b[0][j] +
                a[i][1] * b[1][j] +
                a[i][2] * b[2][j]
            );
        }
    }
    return mat3_to_py_tuple(out);
}

py::tuple rotation_matrix_apply_py(const py::sequence& m_src, const py::sequence& v_src) {
    double m[3][3];
    double v[3];
    double out[3];
    load_mat3(m_src, m);
    load_vec3(v_src, v);

    for (size_t i = 0; i < 3; ++i) {
        out[i] = m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2];
    }
    return vec3_to_py_tuple(out);
}

py::tuple apply_aberration_velocity_py(const py::sequence& xyz_src, const py::sequence& velocity_src) {
    double xyz_vals[3];
    double velocity_vals[3];
    load_vec3(xyz_src, xyz_vals);
    load_vec3(velocity_src, velocity_vals);
    constexpr double c_km_per_day = 299792.458 * 86400.0;

    const double x = xyz_vals[0];
    const double y = xyz_vals[1];
    const double z = xyz_vals[2];
    const double dist = std::sqrt(x * x + y * y + z * z);
    if (dist < 1e-10) {
        return py::make_tuple(x, y, z);
    }

    const double ux = x / dist;
    const double uy = y / dist;
    const double uz = z / dist;

    const double bx = velocity_vals[0] / c_km_per_day;
    const double by = velocity_vals[1] / c_km_per_day;
    const double bz = velocity_vals[2] / c_km_per_day;

    const double beta2 = bx * bx + by * by + bz * bz;
    const double gamma = 1.0 / std::sqrt(1.0 - beta2);
    const double dot = ux * bx + uy * by + uz * bz;
    const double factor1 = 1.0 + dot / (1.0 + gamma);
    const double factor2 = gamma * (1.0 + dot);

    double ax = (ux + factor1 * bx) / factor2;
    double ay = (uy + factor1 * by) / factor2;
    double az = (uz + factor1 * bz) / factor2;

    const double scale = dist / std::sqrt(ax * ax + ay * ay + az * az);
    const double out[3] = {ax * scale, ay * scale, az * scale};
    return vec3_to_py_tuple(out);
}

py::tuple apply_frame_bias_py(const py::sequence& xyz_src) {
    double xyz_vals[3];
    load_vec3(xyz_src, xyz_vals);

    constexpr double arcsec2rad = 3.141592653589793238462643383279502884 / 648000.0;
    constexpr double dA_r = (-14.6 / 1000.0) * arcsec2rad;
    constexpr double xi0_r = (-16.6170 / 1000.0) * arcsec2rad;
    constexpr double de0_r = (-6.8192 / 1000.0) * arcsec2rad;

    const double x = xyz_vals[0];
    const double y = xyz_vals[1];
    const double z = xyz_vals[2];
    const double xb = x - de0_r * y + xi0_r * z;
    const double yb = de0_r * x + y - dA_r * z;
    const double zb = -xi0_r * x + dA_r * y + z;

    const double out[3] = {xb, yb, zb};
    return vec3_to_py_tuple(out);
}

/**
 * @brief 2D version: evaluates one record provided as a (coefficient, component) array.
 */
py::list spk_chebyshev_record_py(
    const py::sequence& coeff_record,
    double s
) {
    DenseMatrixView coeff_record_view = load_double_matrix(coeff_record, "Evaluator coefficients");
    const size_t component_count = coeff_record_view.rows;
    const size_t coefficient_count = coeff_record_view.cols;
    const auto* coeffs = coeff_record_view.values.data();

    std::vector<double> result(component_count);
    spk_chebyshev_record_inplace(
        coeffs, coefficient_count, component_count, s, result.data(), 
        1,                // coeff_stride = 1
        coefficient_count // component_stride = n
    );

    return vector_to_py_list(result);
}

py::tuple spk_chebyshev_record_with_derivative_py(
    const py::sequence& coeff_record,
    double s,
    double derivative_scale
) {
    DenseMatrixView coeff_record_view = load_double_matrix(coeff_record, "Evaluator coefficients");
    const size_t component_count = coeff_record_view.rows;
    const size_t coefficient_count = coeff_record_view.cols;
    const auto* coeffs = coeff_record_view.values.data();

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
    const py::sequence& coefficients,
    int32_t record_index,
    double s
) {
    DenseTensor3View coeff_series_view = load_double_tensor3(coefficients, "Series evaluator coefficients");
    const size_t component_count = coeff_series_view.dim1;
    const size_t coefficient_count = coeff_series_view.dim2;
    const size_t record_stride = component_count * coefficient_count;
    if (record_index < 0 || static_cast<size_t>(record_index) >= coeff_series_view.dim0) {
        throw std::runtime_error("Series evaluator record index is out of range");
    }
    const auto* coeffs = coeff_series_view.values.data();
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
    const py::sequence& coefficients,
    int32_t record_index,
    double s,
    double derivative_scale
) {
    DenseTensor3View coeff_series_view = load_double_tensor3(coefficients, "Series evaluator coefficients");
    const size_t component_count = coeff_series_view.dim1;
    const size_t coefficient_count = coeff_series_view.dim2;
    const size_t record_stride = component_count * coefficient_count;
    if (record_index < 0 || static_cast<size_t>(record_index) >= coeff_series_view.dim0) {
        throw std::runtime_error("Series evaluator record index is out of range");
    }
    const auto* coeffs = coeff_series_view.values.data();
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
    const py::sequence& coeff_series,
    const py::sequence& record_indices,
    const py::sequence& s_values,
    const py::sequence& derivative_scales,
    bool need_rates
) {
    DenseTensor3View coeff_series_view = load_double_tensor3(coeff_series, "Bulk evaluator coefficients");
    std::vector<int32_t> indices = load_int32_vector(record_indices, "Bulk evaluator record indices");
    std::vector<double> s_vec = load_double_vector(s_values, "Bulk evaluator s values");
    std::vector<double> ds_vec = load_double_vector(derivative_scales, "Bulk evaluator derivative scales");

    const size_t workload_size = indices.size();
    const size_t record_count = coeff_series_view.dim0;
    const size_t component_count = coeff_series_view.dim1;
    const size_t coefficient_count = coeff_series_view.dim2;
    const size_t record_stride = component_count * coefficient_count;
    if (s_vec.size() != workload_size || ds_vec.size() != workload_size) {
        throw std::runtime_error("Bulk evaluator workload arrays must have matching length");
    }

    const auto* coeffs = coeff_series_view.values.data();
    std::vector<double> values_buffer(workload_size * component_count, 0.0);
    auto* v_out_ptr = values_buffer.data();

    if (need_rates) {
        std::vector<double> rates_buffer(workload_size * component_count, 0.0);
        auto* r_out_ptr = rates_buffer.data();

        for (size_t i = 0; i < workload_size; ++i) {
            const int32_t record_index = indices[i];
            if (record_index < 0 || static_cast<size_t>(record_index) >= record_count) {
                throw std::runtime_error("Bulk evaluator record index is out of range");
            }
            spk_chebyshev_record_with_derivative_inplace(
                coeffs + static_cast<size_t>(record_index) * record_stride,
                coefficient_count, component_count, s_vec[i],
                v_out_ptr + i * component_count,
                r_out_ptr + i * component_count,
                1, coefficient_count
            );
            
            const double ds = ds_vec[i];
            for (size_t j = 0; j < component_count; ++j) {
                r_out_ptr[i * component_count + j] *= ds;
            }
        }
        return py::make_tuple(
            matrix_to_py_list(values_buffer.data(), workload_size, component_count),
            matrix_to_py_list(rates_buffer.data(), workload_size, component_count)
        );
    } else {
        for (size_t i = 0; i < workload_size; ++i) {
            const int32_t record_index = indices[i];
            if (record_index < 0 || static_cast<size_t>(record_index) >= record_count) {
                throw std::runtime_error("Bulk evaluator record index is out of range");
            }
            spk_chebyshev_record_inplace(
                coeffs + static_cast<size_t>(record_index) * record_stride,
                coefficient_count, component_count, s_vec[i],
                v_out_ptr + i * component_count,
                1, coefficient_count
            );
        }
        return py::make_tuple(
            matrix_to_py_list(values_buffer.data(), workload_size, component_count),
            py::none()
        );
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

py::dict catalog_to_py_dict(const DafCatalog& catalog) {
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

    py::list records;
    for (size_t i = 0; i < payload.record_count; ++i) {
        py::list components;
        for (size_t j = 0; j < payload.component_count; ++j) {
            py::list coeffs;
            for (size_t k = 0; k < payload.coefficient_count; ++k) {
                coeffs.append(payload.coefficients[(i * payload.component_count + j) * payload.coefficient_count + k]);
            }
            components.append(py::tuple(coeffs));
        }
        records.append(py::tuple(components));
    }

    py::dict out_dict;
    out_dict["init"] = payload.init;
    out_dict["intlen"] = payload.intlen;
    out_dict["record_count"] = payload.record_count;
    out_dict["component_count"] = payload.component_count;
    out_dict["coefficient_count"] = payload.coefficient_count;
    out_dict["coefficients"] = py::tuple(records);
    return out_dict;
}

std::shared_ptr<SpkSegmentEvaluator> load_spk_segment_evaluator_py(
    const std::string& path, int32_t start_i, int32_t end_i, bool little_endian, int32_t data_type
) {
    SpkChebyshevSegmentPayload payload = read_spk_chebyshev_segment_payload(
        path, start_i, end_i, little_endian, data_type
    );
    return std::make_shared<SpkSegmentEvaluator>(
        data_type,
        false,
        payload.init,
        payload.intlen,
        payload.record_count,
        payload.component_count,
        payload.coefficient_count,
        std::move(payload.coefficients)
    );
}

std::shared_ptr<NativeSpkKernelHandle> open_spk_kernel_py(const std::string& path) {
    return std::make_shared<NativeSpkKernelHandle>(path);
}

py::dict read_spk_type13_segment_payload_py(const std::string& path, int32_t start_i, int32_t end_i, bool little_endian) {
    SpkType13SegmentPayload payload = read_spk_type13_segment_payload(path, start_i, end_i, little_endian);

    py::tuple epochs(payload.state_count);
    for (size_t i = 0; i < static_cast<size_t>(payload.state_count); ++i) {
        epochs[i] = payload.epochs_jd[i];
    }

    py::list states;
    for (size_t axis = 0; axis < 6; ++axis) {
        py::tuple axis_values(payload.state_count);
        for (size_t i = 0; i < static_cast<size_t>(payload.state_count); ++i) {
            axis_values[i] = payload.states[axis * payload.state_count + i];
        }
        states.append(std::move(axis_values));
    }

    py::dict out_dict;
    out_dict["epochs_jd"] = epochs;
    out_dict["states"] = states;
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

    py::class_<SpkSegmentEvaluator, std::shared_ptr<SpkSegmentEvaluator>>(m, "SpkSegmentEvaluator")
        .def("position", [](const SpkSegmentEvaluator& self, double jd) {
            double result[3];
            self.position(jd, result);
            py::list out;
            for (double value : result) out.append(value);
            return out;
        })
        .def("position_and_velocity", [](const SpkSegmentEvaluator& self, double jd) {
            double position[3];
            double velocity[3];
            self.position_and_velocity(jd, position, velocity);
            py::list pos_out;
            py::list vel_out;
            for (double value : position) pos_out.append(value);
            for (double value : velocity) vel_out.append(value);
            return py::make_tuple(pos_out, vel_out);
        });

    py::class_<NativeSpkKernelHandle, std::shared_ptr<NativeSpkKernelHandle>>(m, "NativeSpkKernelHandle")
        .def("catalog", [](const NativeSpkKernelHandle& self) {
            return catalog_to_py_dict(self.catalog);
        })
        .def("load_segment_evaluator", [](NativeSpkKernelHandle& self, int32_t start_i, int32_t end_i, int32_t data_type) {
            return self.get_segment_evaluator(start_i, end_i, data_type);
        })
        .def("batch_segment_position_and_velocity", [](NativeSpkKernelHandle& self, py::iterable specs, double jd) {
            py::list out;
            for (py::handle spec_handle : specs) {
                auto spec = py::cast<py::tuple>(spec_handle);
                if (py::len(spec) != 3) {
                    throw std::runtime_error("segment spec must be a 3-tuple of (start_i, end_i, data_type)");
                }
                int32_t start_i = py::cast<int32_t>(spec[0]);
                int32_t end_i = py::cast<int32_t>(spec[1]);
                int32_t data_type = py::cast<int32_t>(spec[2]);
                double position[3];
                double velocity[3];
                self.segment_position_and_velocity(start_i, end_i, data_type, jd, position, velocity);
                py::list pos_out;
                py::list vel_out;
                for (double value : position) pos_out.append(value);
                for (double value : velocity) vel_out.append(value);
                out.append(py::make_tuple(pos_out, vel_out));
            }
            return out;
        })
        .def("batch_segment_position_requests", [](NativeSpkKernelHandle& self, py::iterable requests) {
            py::list out;
            for (py::handle request_handle : requests) {
                auto request = py::cast<py::tuple>(request_handle);
                if (py::len(request) != 4) {
                    throw std::runtime_error(
                        "segment request must be a 4-tuple of (start_i, end_i, data_type, jd)"
                    );
                }
                int32_t start_i = py::cast<int32_t>(request[0]);
                int32_t end_i = py::cast<int32_t>(request[1]);
                int32_t data_type = py::cast<int32_t>(request[2]);
                double jd = py::cast<double>(request[3]);
                double position[3];
                self.segment_position(start_i, end_i, data_type, jd, position);
                py::list pos_out;
                for (double value : position) pos_out.append(value);
                out.append(pos_out);
            }
            return out;
        })
        .def("segment_position", [](NativeSpkKernelHandle& self, int32_t start_i, int32_t end_i, int32_t data_type, double jd) {
            double result[3];
            self.segment_position(start_i, end_i, data_type, jd, result);
            py::list out;
            for (double value : result) out.append(value);
            return out;
        })
        .def("segment_position_and_velocity", [](NativeSpkKernelHandle& self, int32_t start_i, int32_t end_i, int32_t data_type, double jd) {
            double position[3];
            double velocity[3];
            self.segment_position_and_velocity(start_i, end_i, data_type, jd, position, velocity);
            py::list pos_out;
            py::list vel_out;
            for (double value : position) pos_out.append(value);
            for (double value : velocity) vel_out.append(value);
            return py::make_tuple(pos_out, vel_out);
        })
        .def("close", &NativeSpkKernelHandle::close);

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
    m.def("set_nutation_2000a_tables", &set_nutation_2000a_tables_py,
        py::arg("ls_terms"), py::arg("pl_terms"), py::arg("ls_j0_count"), py::arg("pl_j0_count"));
    m.def("nutation_2000a", &nutation_2000a_py, py::arg("jd_tt"));
    m.def("rotation_matrix_multiply", &rotation_matrix_multiply_py, py::arg("a"), py::arg("b"));
    m.def("rotation_matrix_apply", &rotation_matrix_apply_py, py::arg("matrix"), py::arg("vector"));
    m.def("apply_aberration_velocity", &apply_aberration_velocity_py, py::arg("xyz"), py::arg("velocity"));
    m.def("apply_frame_bias", &apply_frame_bias_py, py::arg("xyz"));

    // --- Interpolation ---
    m.def("horner", [](const py::sequence& coeffs, double x) {
        std::vector<double> coeff_vec = load_double_vector(coeffs, "Horner coefficients");
        double res = 0.0;
        for (int i = static_cast<int>(coeff_vec.size()) - 1; i >= 0; --i) {
            res = res * x + coeff_vec[static_cast<size_t>(i)];
        }
        return res;
    }, py::arg("coeffs"), py::arg("x"));
    m.def("lagrange_interpolate", [](const py::sequence& x_pts, const py::sequence& y_pts, double x) {
        std::vector<double> x_vec = load_double_vector(x_pts, "Lagrange x points");
        std::vector<double> y_vec = load_double_vector(y_pts, "Lagrange y points");
        if (x_vec.size() != y_vec.size()) throw std::runtime_error("Lagrange points must have same size");
        return lagrange_interpolate(x_vec.data(), y_vec.data(), x_vec.size(), x);
    }, py::arg("x_pts"), py::arg("y_pts"), py::arg("x"));
    
    m.def("spk_chebyshev_record", &spk_chebyshev_record_py, py::arg("coeff_record"), py::arg("s"));
    m.def("spk_chebyshev_record_with_derivative", &spk_chebyshev_record_with_derivative_py, py::arg("coeff_record"), py::arg("s"), py::arg("derivative_scale"));
    
    m.def("spk_chebyshev_series_record", &spk_chebyshev_series_record_py, py::arg("coefficients"), py::arg("record_index"), py::arg("s"));
    m.def("spk_chebyshev_series_record_with_derivative", &spk_chebyshev_series_record_with_derivative_py, py::arg("coefficients"), py::arg("record_index"), py::arg("s"), py::arg("derivative_scale"));
    
    m.def("spk_chebyshev_series_bulk_evaluate", &spk_chebyshev_series_bulk_evaluate_py, 
          py::arg("coeff_series"), py::arg("record_indices"), py::arg("s_values"), py::arg("derivative_scales"), py::arg("need_rates"));

    m.def("spk_type13_record", [](const py::sequence& epochs, const py::sequence& states, size_t window_size, double jd) {
        std::vector<double> epochs_vec = load_double_vector(epochs, "Type13 epochs");
        DenseMatrixView states_view = load_double_matrix(states, "Type13 states");
        if (states_view.rows * states_view.cols == 0) {
            throw std::runtime_error("Type13 states cannot be empty");
        }
        std::vector<double> result(6);
        spk_type13_record_inplace(
            epochs_vec.data(),
            states_view.values.data(),
            epochs_vec.size(),
            window_size,
            jd,
            result.data()
        );
        return vector_to_py_list(result);
    }, py::arg("epochs"), py::arg("states"), py::arg("window_size"), py::arg("jd"));

    m.def("read_daf_catalog", &read_daf_catalog_py, py::arg("path"));
    m.def("open_spk_kernel", &open_spk_kernel_py, py::arg("path"));
    m.def("read_spk_chebyshev_segment_payload", &read_spk_chebyshev_segment_payload_py, py::arg("path"), py::arg("start_i"), py::arg("end_i"), py::arg("little_endian"), py::arg("data_type"));
    m.def("load_spk_segment_evaluator", &load_spk_segment_evaluator_py, py::arg("path"), py::arg("start_i"), py::arg("end_i"), py::arg("little_endian"), py::arg("data_type"));
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

    // --- LOLA (Lunar Orbiter Laser Altimeter) ---
    
    py::class_<lola::SphericalCoords>(m, "SphericalCoords")
        .def_readwrite("lon_deg", &lola::SphericalCoords::lon_deg)
        .def_readwrite("lat_deg", &lola::SphericalCoords::lat_deg)
        .def_readwrite("radius_km", &lola::SphericalCoords::radius_km);

    py::class_<lola::SkyPlaneProjection>(m, "SkyPlaneProjection")
        .def_readwrite("east_km", &lola::SkyPlaneProjection::east_km)
        .def_readwrite("north_km", &lola::SkyPlaneProjection::north_km)
        .def_readwrite("radius_km", &lola::SkyPlaneProjection::radius_km)
        .def_readwrite("pa_deg", &lola::SkyPlaneProjection::pa_deg);

    py::class_<lola::MaxPerBin>(m, "MaxPerBin")
        .def_readwrite("bins", &lola::MaxPerBin::bins)
        .def_readwrite("radii_km", &lola::MaxPerBin::radii_km)
        .def_readwrite("point_indices", &lola::MaxPerBin::point_indices);

    py::class_<lola::Point2D>(m, "Point2D")
        .def(py::init<double, double>())
        .def_readwrite("x", &lola::Point2D::x)
        .def_readwrite("y", &lola::Point2D::y);

    py::class_<lola::LolaPointCloud>(m, "LolaPointCloud")
        .def(py::init<const std::vector<double>&, const std::vector<double>&, const std::vector<double>&>())
        .def(py::init<>())
        .def("size", &lola::LolaPointCloud::size)
        .def("x_data", [](const lola::LolaPointCloud& self) { return reinterpret_cast<uintptr_t>(self.x_data()); })
        .def("y_data", [](const lola::LolaPointCloud& self) { return reinterpret_cast<uintptr_t>(self.y_data()); })
        .def("z_data", [](const lola::LolaPointCloud& self) { return reinterpret_cast<uintptr_t>(self.z_data()); })
        .def("get_x", &lola::LolaPointCloud::x_list)
        .def("get_y", &lola::LolaPointCloud::y_list)
        .def("get_z", &lola::LolaPointCloud::z_list)
        .def("filter_by_visibility", &lola::LolaPointCloud::filter_by_visibility)
        .def("filter_by_position_angle", &lola::LolaPointCloud::filter_by_position_angle)
        .def("filter_by_radius", &lola::LolaPointCloud::filter_by_radius)
        .def("filter_combined", &lola::LolaPointCloud::filter_combined)
        .def("to_spherical", &lola::LolaPointCloud::to_spherical)
        .def("project_to_sky_plane", &lola::LolaPointCloud::project_to_sky_plane);

    m.def("normalize_vectors_bulk", [](const std::vector<double>& x, const std::vector<double>& y, const std::vector<double>& z) {
        size_t count = x.size();
        if (y.size() != count || z.size() != count) throw std::invalid_argument("LOLA: Coordinate vectors must have the same size");
        std::vector<double> ox(count), oy(count), oz(count);
        lola::normalize_vectors_bulk(x.data(), y.data(), z.data(), ox.data(), oy.data(), oz.data(), count);
        return py::make_tuple(ox, oy, oz);
    }, py::arg("x"), py::arg("y"), py::arg("z"));

    m.def("dot_product_bulk", [](const std::vector<double>& x, const std::vector<double>& y, const std::vector<double>& z, const Vec3& reference) {
        size_t count = x.size();
        if (y.size() != count || z.size() != count) throw std::invalid_argument("LOLA: Coordinate vectors must have the same size");
        std::vector<double> results(count);
        lola::dot_product_bulk(x.data(), y.data(), z.data(), reference, results.data(), count);
        return results;
    }, py::arg("x"), py::arg("y"), py::arg("z"), py::arg("reference"));

    m.def("cross_product_bulk", [](const std::vector<double>& x, const std::vector<double>& y, const std::vector<double>& z, const Vec3& reference) {
        size_t count = x.size();
        if (y.size() != count || z.size() != count) throw std::invalid_argument("LOLA: Coordinate vectors must have the same size");
        std::vector<double> ox(count), oy(count), oz(count);
        lola::cross_product_bulk(x.data(), y.data(), z.data(), reference, ox.data(), oy.data(), oz.data(), count);
        return py::make_tuple(ox, oy, oz);
    }, py::arg("x"), py::arg("y"), py::arg("z"), py::arg("reference"));

    m.def("project_onto_plane_bulk", [](const std::vector<double>& x_in, const std::vector<double>& y_in, const std::vector<double>& z_in, const Vec3& plane_normal) {
        size_t count = x_in.size();
        if (y_in.size() != count || z_in.size() != count) throw std::invalid_argument("LOLA: Coordinate vectors must have the same size");
        std::vector<double> ox(count), oy(count), oz(count);
        lola::project_onto_plane_bulk(x_in.data(), y_in.data(), z_in.data(), plane_normal, ox.data(), oy.data(), oz.data(), count);
        return py::make_tuple(ox, oy, oz);
    }, py::arg("x_in"), py::arg("y_in"), py::arg("z_in"), py::arg("plane_normal"));

    m.def("cartesian_to_spherical_bulk", [](const std::vector<double>& x, const std::vector<double>& y, const std::vector<double>& z) {
        size_t count = x.size();
        if (y.size() != count || z.size() != count) throw std::invalid_argument("LOLA: Coordinate vectors must have the same size");
        std::vector<double> lon(count), lat(count), rad(count);
        lola::cartesian_to_spherical_bulk(x.data(), y.data(), z.data(), lon.data(), lat.data(), rad.data(), count);
        return py::make_tuple(lon, lat, rad);
    }, py::arg("x"), py::arg("y"), py::arg("z"));

    m.def("spherical_to_cartesian_bulk", [](const std::vector<double>& lon_deg, const std::vector<double>& lat_deg, const std::vector<double>& radius_km) {
        size_t count = lon_deg.size();
        if (lat_deg.size() != count || radius_km.size() != count) throw std::invalid_argument("LOLA: Coordinate vectors must have the same size");
        std::vector<double> x(count), y(count), z(count);
        lola::spherical_to_cartesian_bulk(lon_deg.data(), lat_deg.data(), radius_km.data(), x.data(), y.data(), z.data(), count);
        return py::make_tuple(x, y, z);
    }, py::arg("lon_deg"), py::arg("lat_deg"), py::arg("radius_km"));

    m.def("normalize_longitude_bulk", [](const std::vector<double>& lon_deg) {
        std::vector<double> out = lon_deg;
        lola::normalize_longitude_bulk(out.data(), out.size());
        return out;
    }, py::arg("lon_deg"));

    m.def("bin_by_position_angle", [](const std::vector<double>& pa_deg, double target_pa_deg, double bin_width_deg) {
        return lola::bin_by_position_angle(pa_deg.data(), target_pa_deg, bin_width_deg, pa_deg.size());
    }, py::arg("pa_deg"), py::arg("target_pa_deg"), py::arg("bin_width_deg"));

    m.def("select_max_radius_per_bin", [](const std::vector<int>& bin_indices, const std::vector<double>& radius_km) {
        if (bin_indices.size() != radius_km.size()) throw std::invalid_argument("LOLA: bin_indices and radius_km must have the same size");
        return lola::select_max_radius_per_bin(bin_indices.data(), radius_km.data(), bin_indices.size());
    }, py::arg("bin_indices"), py::arg("radius_km"));

    m.def("lexsort_by_bin_and_radius", [](const std::vector<int>& bin_indices, const std::vector<double>& radius_km) {
        if (bin_indices.size() != radius_km.size()) throw std::invalid_argument("LOLA: bin_indices and radius_km must have the same size");
        return lola::lexsort_by_bin_and_radius(bin_indices.data(), radius_km.data(), bin_indices.size());
    }, py::arg("bin_indices"), py::arg("radius_km"));

    m.def("convex_hull_2d", &lola::convex_hull_2d, py::arg("points"));
    
    m.def("ray_hull_intersection", &lola::ray_hull_intersection, 
        py::arg("hull"), py::arg("position_angle_deg"), py::arg("fallback_radius_km"));
}
