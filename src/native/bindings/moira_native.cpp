#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include <array>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string>
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
#include "visibility.hpp"
#include "precession.hpp"
#include "harmograms.hpp"

namespace py = pybind11;
using namespace moira::native;

namespace {

struct NativeNutationTerm {
    double c1 = 0.0;
    double c2 = 0.0;
    std::array<int, 14> args{};
    size_t arg_count = 0;
};

struct NativeLeapSecondEntry {
    double jd_utc = 0.0;
    double tai_minus_utc = 0.0;
};

struct NativeNaifLsk {
    double delta_t_a = 32.184;
    double k = 1.657e-3;
    double eb = 1.671e-2;
    double m0 = 6.239996;
    double m1 = 1.99096871e-7;
    std::vector<NativeLeapSecondEntry> delta_at;
    bool loaded = false;
    std::string source_path;
};

std::vector<NativeNutationTerm> g_native_nutation_ls_terms;
std::vector<NativeNutationTerm> g_native_nutation_pl_terms;
size_t g_native_nutation_ls_j0_count = 0;
size_t g_native_nutation_pl_j0_count = 0;
bool g_native_nutation_tables_ready = false;
std::mutex g_native_nutation_mutex;
NativeNaifLsk g_native_naif_lsk;
std::mutex g_native_naif_lsk_mutex;

constexpr double NUTATION_ARCSEC = 3.141592653589793238462643383279502884 / 648000.0;
constexpr double NUTATION_UAS2DEG = 1e-6 / 3600.0;
constexpr double NATIVE_J2000 = 2451545.0;

std::string trim_copy(const std::string& value) {
    const size_t first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return "";
    }
    const size_t last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::string replace_fortran_d(std::string value) {
    for (char& ch : value) {
        if (ch == 'D' || ch == 'd') {
            ch = 'E';
        }
    }
    return value;
}

int month_from_naif_abbrev(const std::string& month) {
    if (month == "JAN") return 1;
    if (month == "FEB") return 2;
    if (month == "MAR") return 3;
    if (month == "APR") return 4;
    if (month == "MAY") return 5;
    if (month == "JUN") return 6;
    if (month == "JUL") return 7;
    if (month == "AUG") return 8;
    if (month == "SEP") return 9;
    if (month == "OCT") return 10;
    if (month == "NOV") return 11;
    if (month == "DEC") return 12;
    throw std::runtime_error("Unsupported NAIF month token in LSK: " + month);
}

double jd_from_naif_date_token(const std::string& token) {
    if (token.size() < 2 || token[0] != '@') {
        throw std::runtime_error("Invalid NAIF date token in LSK: " + token);
    }

    std::string raw = token.substr(1);
    std::vector<std::string> parts;
    std::stringstream ss(raw);
    std::string item;
    while (std::getline(ss, item, '-')) {
        parts.push_back(trim_copy(item));
    }
    if (parts.size() != 3) {
        throw std::runtime_error("Unsupported NAIF date token format in LSK: " + token);
    }

    const int year = std::stoi(parts[0]);
    const int month = month_from_naif_abbrev(parts[1]);
    const int day = std::stoi(parts[2]);
    return julian_day(year, month, day, 0.0);
}

NativeNaifLsk parse_naif_lsk(const std::string& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("Could not open NAIF LSK: " + path);
    }

    NativeNaifLsk parsed;
    parsed.source_path = path;

    auto parse_delta_at_row = [&parsed](const std::string& row_text) {
        const std::string row = trim_copy(row_text);
        if (row.empty()) {
            return;
        }
        const size_t comma_pos = row.find(',');
        if (comma_pos == std::string::npos) {
            throw std::runtime_error("Malformed DELTET/DELTA_AT row in LSK: " + row);
        }
        const double offset = std::stod(trim_copy(row.substr(0, comma_pos)));
        const std::string date_token = trim_copy(row.substr(comma_pos + 1));
        parsed.delta_at.push_back({jd_from_naif_date_token(date_token), offset});
    };

    std::string line;
    bool in_delta_at = false;
    while (std::getline(input, line)) {
        const std::string trimmed = trim_copy(line);
        if (trimmed.empty()) {
            continue;
        }

        if (in_delta_at) {
            const size_t close_pos = trimmed.find(')');
            const std::string row = close_pos == std::string::npos ? trimmed : trimmed.substr(0, close_pos);
            parse_delta_at_row(row);
            if (close_pos != std::string::npos) {
                in_delta_at = false;
            }
            continue;
        }

        if (trimmed.rfind("DELTET/DELTA_T_A", 0) == 0) {
            const size_t eq = trimmed.find('=');
            parsed.delta_t_a = std::stod(replace_fortran_d(trim_copy(trimmed.substr(eq + 1))));
            continue;
        }
        if (trimmed.rfind("DELTET/K", 0) == 0) {
            const size_t eq = trimmed.find('=');
            parsed.k = std::stod(replace_fortran_d(trim_copy(trimmed.substr(eq + 1))));
            continue;
        }
        if (trimmed.rfind("DELTET/EB", 0) == 0) {
            const size_t eq = trimmed.find('=');
            parsed.eb = std::stod(replace_fortran_d(trim_copy(trimmed.substr(eq + 1))));
            continue;
        }
        if (trimmed.rfind("DELTET/M", 0) == 0) {
            const size_t open = trimmed.find('(');
            const size_t close = trimmed.find(')');
            const std::string values = trimmed.substr(open + 1, close - open - 1);
            std::stringstream value_stream(values);
            std::string first;
            std::string second;
            value_stream >> first >> second;
            parsed.m0 = std::stod(replace_fortran_d(first));
            parsed.m1 = std::stod(replace_fortran_d(second));
            continue;
        }
        if (trimmed.rfind("DELTET/DELTA_AT", 0) == 0) {
            const size_t open = trimmed.find('(');
            if (open != std::string::npos) {
                const std::string inline_row = trim_copy(trimmed.substr(open + 1));
                if (!inline_row.empty()) {
                    parse_delta_at_row(inline_row);
                }
            }
            in_delta_at = true;
            continue;
        }
    }

    if (parsed.delta_at.empty()) {
        throw std::runtime_error("NAIF LSK did not provide any DELTET/DELTA_AT entries: " + path);
    }
    parsed.loaded = true;
    return parsed;
}

void load_naif_lsk_py(const std::string& path) {
    NativeNaifLsk parsed = parse_naif_lsk(path);
    std::lock_guard<std::mutex> lock(g_native_naif_lsk_mutex);
    g_native_naif_lsk = std::move(parsed);
}

double native_tai_minus_utc(double jd_utc) {
    if (!g_native_naif_lsk.loaded) {
        throw std::runtime_error("Native NAIF LSK is not loaded");
    }
    if (jd_utc < g_native_naif_lsk.delta_at.front().jd_utc) {
        throw std::runtime_error("Native NAIF LSK time admission does not support pre-1972 UTC epochs");
    }
    double result = g_native_naif_lsk.delta_at.front().tai_minus_utc;
    for (const NativeLeapSecondEntry& entry : g_native_naif_lsk.delta_at) {
        if (jd_utc >= entry.jd_utc) {
            result = entry.tai_minus_utc;
        } else {
            break;
        }
    }
    return result;
}

double jd_utc_to_et_seconds_past_j2000_py(double jd_utc) {
    std::lock_guard<std::mutex> lock(g_native_naif_lsk_mutex);
    const double utc_seconds_past_j2000 = (jd_utc - NATIVE_J2000) * 86400.0;
    const double delta_at = native_tai_minus_utc(jd_utc);

    double et = utc_seconds_past_j2000 + g_native_naif_lsk.delta_t_a + delta_at;
    for (int i = 0; i < 6; ++i) {
        const double mean_anomaly = g_native_naif_lsk.m0 + g_native_naif_lsk.m1 * et;
        const double eccentric_anomaly = mean_anomaly + g_native_naif_lsk.eb * std::sin(mean_anomaly);
        const double et_minus_utc = g_native_naif_lsk.delta_t_a + delta_at + g_native_naif_lsk.k * std::sin(eccentric_anomaly);
        et = utc_seconds_past_j2000 + et_minus_utc;
    }
    return et;
}

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
// Note: cartography Python bindings are omitted pending numpy-free redesign.
// The C++ kernels remain available in cartography.hpp for future re-binding.


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
        .def("evaluate_batch", [](IEvaluator& self, const std::vector<double>& jds) {
            size_t count = jds.size();
            std::vector<std::vector<double>> out(count, std::vector<double>(6));
            std::vector<double> flat(count * 6);
            self.evaluate_batch(jds.data(), count, flat.data());
            for (size_t i = 0; i < count; ++i) {
                out[i].assign(flat.data() + i * 6, flat.data() + i * 6 + 6);
            }
            return out;
        });

    py::class_<ChebyshevEvaluator, IEvaluator, std::shared_ptr<ChebyshevEvaluator>>(m, "ChebyshevEvaluator")
        .def(py::init<double, double, size_t, size_t, size_t, std::vector<double>>());

    py::class_<SpkSegmentEvaluator, std::shared_ptr<SpkSegmentEvaluator>, IEvaluator>(m, "SpkSegmentEvaluator")
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
    
    py::class_<SumEvaluator, IEvaluator, std::shared_ptr<SumEvaluator>>(m, "SumEvaluator")
        .def(py::init<std::shared_ptr<IEvaluator>, std::shared_ptr<IEvaluator>>());

    m.def("longitude_difference", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, double jd) {
        return longitude_difference(*t1, *t2, *obs, jd);
    });

    m.def("longitude_difference_batch", [](std::shared_ptr<IEvaluator> t1, std::shared_ptr<IEvaluator> t2, std::shared_ptr<IEvaluator> obs, const std::vector<double>& jds) {
        std::vector<double> out(jds.size());
        for (size_t i = 0; i < jds.size(); ++i) {
            out[i] = longitude_difference(*t1, *t2, *obs, jds[i]);
        }
        return out;
    });

    m.def("declination_batch", [](std::shared_ptr<IEvaluator> t, std::shared_ptr<IEvaluator> obs, const std::vector<double>& jds) {
        std::vector<double> out(jds.size());
        for (size_t i = 0; i < jds.size(); ++i) {
            double r_t[6], r_o[6];
            t->evaluate(jds[i], r_t);
            obs->evaluate(jds[i], r_o);
            double x = r_t[0] - r_o[0];
            double y = r_t[1] - r_o[1];
            double z = r_t[2] - r_o[2];
            double dist = std::sqrt(x*x + y*y + z*z);
            out[i] = std::asin(z / dist) * 180.0 / 3.14159265358979323846;
        }
        return out;
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
    m.def("load_naif_lsk", &load_naif_lsk_py, py::arg("path"));
    m.def("jd_utc_to_et_seconds_past_j2000", &jd_utc_to_et_seconds_past_j2000_py, py::arg("jd_utc"));
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
    m.def("vec3_to_lonlat_signed", &vec3_to_lonlat_signed, py::arg("v"));
    m.def("geodetic_to_cartesian_wgs84", &geodetic_to_cartesian_wgs84,
        py::arg("lon_deg"), py::arg("lat_deg"), py::arg("elevation_m") = 0.0);
    m.def("ecliptic_to_equatorial", &ecliptic_to_equatorial, py::arg("lon_deg"), py::arg("lat_deg"), py::arg("obliquity_deg"));
    m.def("equatorial_to_ecliptic", &equatorial_to_ecliptic, py::arg("ra_deg"), py::arg("dec_deg"), py::arg("obliquity_deg"));

    // --- Topocentric ---
    py::class_<TopocentricEvaluator, IEvaluator, std::shared_ptr<TopocentricEvaluator>>(m, "TopocentricEvaluator")
        .def(py::init<std::shared_ptr<IEvaluator>, double, double, double>());

    py::class_<FixedStarEvaluator, IEvaluator, std::shared_ptr<FixedStarEvaluator>>(m, "FixedStarEvaluator")
        .def(py::init<double, double, double, double, double, double>(),
             py::arg("ra_deg"), py::arg("dec_deg"), py::arg("pmra_mas"), py::arg("pmdec_mas"), py::arg("parallax"), py::arg("rv"));

    // --- Cartography ---
    // Bindings omitted pending integration; C++ kernels remain in cartography.hpp.

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

    // --- Visibility ---
    py::class_<HeliacalEvent>(m, "HeliacalEvent")
        .def_readonly("event_kind", &HeliacalEvent::event_kind)
        .def_readonly("jd_ut", &HeliacalEvent::jd_ut)
        .def_readonly("is_found", &HeliacalEvent::is_found)
        .def_readonly("arcus_visionis", &HeliacalEvent::arcus_visionis)
        .def_readonly("elongation", &HeliacalEvent::elongation)
        .def_readonly("star_altitude", &HeliacalEvent::star_altitude)
        .def_readonly("day_offset", &HeliacalEvent::day_offset);

    m.def("arcus_visionis", &arcus_visionis, 
        py::arg("mag"), py::arg("limiting_mag"), py::arg("extinction_k"),
        "Compute required Arcus Visionis for visibility via Schoch/Ptolemy logic.");

    m.def("target_topocentric_altitude",
        [](const IEvaluator& target_eval, double jd_ut, double lat_deg, double lon_deg,
           double pressure_mbar, double temperature_c, bool use_refraction, double delta_t,
           const IEvaluator* earth_eval) {
            return target_topocentric_altitude(target_eval, jd_ut, lat_deg, lon_deg,
                pressure_mbar, temperature_c, use_refraction, delta_t, earth_eval);
        },
        py::arg("target_eval"), py::arg("jd_ut"), py::arg("lat_deg"), py::arg("lon_deg"),
        py::arg("pressure_mbar") = 1013.25, py::arg("temperature_c") = 10.0, py::arg("use_refraction") = true,
        py::arg("delta_t") = 64.184, py::arg("earth_eval") = nullptr,
        "Compute topocentric altitude with optional annual aberration via Earth evaluator.");

    m.def("find_sun_at_alt",
        [](const IEvaluator& sun_eval, double jd_midnight, double lat_deg, double lon_deg,
           double target_alt, bool morning, double delta_t, const IEvaluator* earth_eval) {
            return find_sun_at_alt(sun_eval, jd_midnight, lat_deg, lon_deg,
                target_alt, morning, delta_t, earth_eval);
        },
        py::arg("sun_eval"), py::arg("jd_midnight"), py::arg("lat_deg"), py::arg("lon_deg"),
        py::arg("target_alt"), py::arg("morning"), py::arg("delta_t") = 64.184,
        py::arg("earth_eval") = nullptr,
        "Solve for JD within a half-day window where the Sun reaches a target altitude.");

    m.def("search_heliacal_rising",
        [](const IEvaluator& star_eval, const IEvaluator& sun_eval, double jd_start,
           double lat, double lon, double arcus_visionis_val, int search_days,
           double delta_t, const IEvaluator* earth_eval) {
            return search_heliacal_rising(star_eval, sun_eval, jd_start, lat, lon,
                arcus_visionis_val, search_days, delta_t, earth_eval);
        },
        py::arg("star_eval"), py::arg("sun_eval"), py::arg("jd_start"),
        py::arg("lat"), py::arg("lon"), py::arg("arcus_visionis_val"),
        py::arg("search_days"), py::arg("delta_t") = 64.184, py::arg("earth_eval") = nullptr,
        "Native fast-path search for star heliacal rising (morning appearance).");

    m.def("search_heliacal_setting",
        [](const IEvaluator& star_eval, const IEvaluator& sun_eval, double jd_start,
           double lat, double lon, double arcus_visionis_val, int search_days,
           double delta_t, const IEvaluator* earth_eval) {
            return search_heliacal_setting(star_eval, sun_eval, jd_start, lat, lon,
                arcus_visionis_val, search_days, delta_t, earth_eval);
        },
        py::arg("star_eval"), py::arg("sun_eval"), py::arg("jd_start"),
        py::arg("lat"), py::arg("lon"), py::arg("arcus_visionis_val"),
        py::arg("search_days"), py::arg("delta_t") = 64.184, py::arg("earth_eval") = nullptr,
        "Native fast-path search for star heliacal setting (morning disappearance).");


    m.def("heliacal_signed_elongation", &heliacal_signed_elongation,
        py::arg("star_eval"), py::arg("sun_eval"), py::arg("jd_ut"), py::arg("delta_t") = 64.184,
        "Compute signed ecliptic elongation between star and Sun.");

    m.def("mean_obliquity_p03", &mean_obliquity_p03, py::arg("jd_tt"),
        "IAU 2006 Mean Obliquity (P03 model).");

    // ── Harmogram acceleration kernels ────────────────────────────────────────

    m.def("harmogram_compute_components",
        [](const std::vector<double>& longitudes_deg,
           const std::vector<int>&    harmonics,
           bool                       raw_sum)
        {
            return harmogram_compute_components(longitudes_deg, harmonics, raw_sum);
        },
        py::arg("longitudes_deg"), py::arg("harmonics"), py::arg("raw_sum"),
        "Compute harmonic vector components (amplitude, phase) for a set of "
        "ecliptic longitudes. Returns list of (harmonic, amplitude, phase_deg).");

    m.def("harmogram_trace_batch",
        [](const std::vector<std::vector<double>>& samples_source_lons,
           const std::vector<std::vector<double>>& samples_target_lons,
           bool                                    same_source_target,
           bool                                    ordered,
           bool                                    include_self,
           bool                                    raw_sum,
           double                                  h0_contribution,
           const std::vector<int>&                 harmonics,
           const std::vector<std::tuple<int, double, double>>& intensity_components)
        {
            auto res = harmogram_trace_batch(
                samples_source_lons, samples_target_lons,
                same_source_target, ordered, include_self, raw_sum,
                h0_contribution, harmonics, intensity_components
            );
            return py::make_tuple(res.total_strengths, res.sample_components);
        },
        py::arg("samples_source_lons"),
        py::arg("samples_target_lons"),
        py::arg("same_source_target"),
        py::arg("ordered"),
        py::arg("include_self"),
        py::arg("raw_sum"),
        py::arg("h0_contribution"),
        py::arg("harmonics"),
        py::arg("intensity_components"),
        "Batch ZA-parts Fourier + intensity projection for N time samples, "
        "parallelised via OpenMP. Returns (total_strengths[N], "
        "sample_components[N][H]) where each component is (harmonic, amplitude, phase_deg).");

    m.def("harmogram_intensity_components",
        [](int                       harmonic_number,
           int                       harmonic_start,
           int                       harmonic_stop,
           int                       sample_count,
           const std::string&        orb_mode,
           double                    orb_width_deg,
           bool                      include_conjunction,
           const std::string&        orb_scaling_mode,
           double                    gaussian_width_deg,
           bool                      gaussian_fwhm_mode)
        {
            auto [h0_amp, comps] = harmogram_intensity_components(
                harmonic_number, harmonic_start, harmonic_stop,
                sample_count, orb_mode, orb_width_deg, include_conjunction,
                orb_scaling_mode, gaussian_width_deg, gaussian_fwhm_mode
            );
            return py::make_tuple(h0_amp, comps);
        },
        py::arg("harmonic_number"),
        py::arg("harmonic_start"),
        py::arg("harmonic_stop"),
        py::arg("sample_count"),
        py::arg("orb_mode"),
        py::arg("orb_width_deg"),
        py::arg("include_conjunction"),
        py::arg("orb_scaling_mode"),
        py::arg("gaussian_width_deg") = 0.0,
        py::arg("gaussian_fwhm_mode") = false,
        "Sample the intensity orb function and compute its DFT spectrum. "
        "Returns (h0_amplitude, [(harmonic, amplitude, phase_deg), ...]).");
}
