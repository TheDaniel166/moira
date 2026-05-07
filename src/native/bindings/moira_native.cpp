#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include "geometry.hpp"
#include "julian.hpp"
#include "math_utils.hpp"
#include "interpolation.hpp"
#include "solvers.hpp"
#include "coordinates.hpp"

namespace py = pybind11;
using namespace moira::native;

PYBIND11_MODULE(moira_native, m) {
    m.doc() = "Moira Native Accelerated Backend";

    // --- Math Utils & Hygiene ---
    m.def("is_finite", &is_finite);
    m.def("has_nan", &has_nan);
    m.def("clamp", &clamp);
    m.def("safe_acos", &safe_acos);
    m.def("safe_asin", &safe_asin);
    m.def("mod_floor", &mod_floor);
    m.def("almost_equal", &almost_equal, py::arg("a"), py::arg("b"), py::arg("abs_eps") = 1e-12, py::arg("rel_eps") = 1e-12);
    
    m.def("deg_to_rad", &deg_to_rad);
    m.def("rad_to_deg", &rad_to_deg);
    m.def("arcsec_to_rad", &arcsec_to_rad);
    m.def("rad_to_arcsec", &rad_to_arcsec);
    m.def("hours_to_rad", &hours_to_rad);
    m.def("rad_to_hours", &rad_to_hours);
    m.def("normalize_deg_360", &normalize_deg_360);
    m.def("normalize_deg_180", &normalize_deg_180);
    m.def("normalize_rad_tau", &normalize_rad_tau);

    // --- Geometry ---
    py::class_<Vec3>(m, "Vec3")
        .def(py::init<std::array<double, 3>>())
        .def_readwrite("data", &Vec3::data)
        .def("__getitem__", [](const Vec3& v, size_t i) {
            if (i >= 3) throw py::index_error();
            return v[i];
        })
        .def_static("add", &Vec3::add)
        .def_static("sub", &Vec3::sub)
        .def_static("scale", &Vec3::scale)
        .def_static("dot", &Vec3::dot)
        .def_static("cross", &Vec3::cross)
        .def("norm", &Vec3::norm)
        .def("unit", &Vec3::unit)
        .def_static("angle_between", &Vec3::angle_between)
        .def_static("project", &Vec3::project)
        .def_static("reject", &Vec3::reject)
        .def_static("lerp", &Vec3::lerp);

    py::class_<Mat3>(m, "Mat3")
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

    // --- Interpolation ---
    m.def("horner", &horner, py::arg("coeffs"), py::arg("x"));
    m.def("lagrange_interpolate", &lagrange_interpolate, py::arg("x_pts"), py::arg("y_pts"), py::arg("x"));
    // Note: chebyshev_eval and derivative would need array mapping or vector wrapper

    // --- Solvers ---
    m.def("bisect", &bisect, py::arg("f"), py::arg("a"), py::arg("b"), py::arg("tol") = 1e-12, py::arg("max_iter") = 100);
    m.def("newton_safe", &newton_safe, py::arg("f"), py::arg("df"), py::arg("a"), py::arg("b"), py::arg("tol") = 1e-12, py::arg("max_iter") = 100);
    m.def("minimize_bracketed", &minimize_bracketed, py::arg("f"), py::arg("a"), py::arg("b"), py::arg("tol") = 1e-12);

    // --- Coordinates ---
    m.def("radec_to_vec3", &radec_to_vec3, py::arg("ra_deg"), py::arg("dec_deg"), py::arg("dist") = 1.0);
    m.def("vec3_to_radec", &vec3_to_radec, py::arg("v"));
    m.def("lonlat_to_vec3", &lonlat_to_vec3, py::arg("lon_deg"), py::arg("lat_deg"), py::arg("dist") = 1.0);
    m.def("vec3_to_lonlat", &vec3_to_lonlat, py::arg("v"));
    m.def("ecliptic_to_equatorial", &ecliptic_to_equatorial, py::arg("lon_deg"), py::arg("lat_deg"), py::arg("obliquity_deg"));
    m.def("equatorial_to_ecliptic", &equatorial_to_ecliptic, py::arg("ra_deg"), py::arg("dec_deg"), py::arg("obliquity_deg"));
}
