#ifndef MOIRA_NATIVE_MATH_UTILS_HPP
#define MOIRA_NATIVE_MATH_UTILS_HPP

#include <cmath>
#include <algorithm>
#include "constants.hpp"

namespace moira {
namespace native {

// --- Numerical Hygiene ---

inline bool is_finite(double x) { return std::isfinite(x); }
inline bool has_nan(double x) { return std::isnan(x); }

inline double clamp(double x, double min_val, double max_val) {
    return std::max(min_val, std::min(max_val, x));
}

inline double safe_acos(double x) { return std::acos(clamp(x, -1.0, 1.0)); }
inline double safe_asin(double x) { return std::asin(clamp(x, -1.0, 1.0)); }

/**
 * @brief THEOREM: Floored modulo.
 * Ensures consistent behavior for negative numbers across platforms.
 * Equivalent to Python's % operator.
 */
inline double mod_floor(double x, double y) {
    return x - y * std::floor(x / y);
}

inline bool almost_equal(double a, double b, double abs_eps = 1e-12, double rel_eps = 1e-12) {
    double diff = std::abs(a - b);
    if (diff <= abs_eps) return true;
    return diff <= rel_eps * std::max(std::abs(a), std::abs(b));
}

// --- Angle Primitives ---

inline double deg_to_rad(double deg) { return deg * DEG2RAD; }
inline double rad_to_deg(double rad) { return rad * RAD2DEG; }

inline double arcsec_to_rad(double arcsec) { return arcsec * ARCSEC2RAD; }
inline double rad_to_arcsec(double rad) { return rad / ARCSEC2RAD; }

inline double hours_to_rad(double hours) { return hours * 15.0 * DEG2RAD; }
inline double rad_to_hours(double rad) { return rad * RAD2DEG / 15.0; }

inline double normalize_deg_360(double deg) { return mod_floor(deg, 360.0); }
inline double normalize_deg_180(double deg) {
    double res = mod_floor(deg, 360.0);
    if (res > 180.0) res -= 360.0;
    return res;
}

inline double normalize_rad_tau(double rad) { return mod_floor(rad, TAU); }

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_MATH_UTILS_HPP
