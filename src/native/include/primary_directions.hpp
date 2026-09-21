#ifndef MOIRA_NATIVE_PRIMARY_DIRECTIONS_HPP
#define MOIRA_NATIVE_PRIMARY_DIRECTIONS_HPP

#include <cmath>
#include <string>
#include <vector>
#include <utility>
#include <stdexcept>
#include <algorithm>

#include "constants.hpp"
#include "math_utils.hpp"

namespace moira {
namespace native {

constexpr double PRIMARY_DIRECTIONS_DOMAIN_TOLERANCE = 1e-12;

/**
 * Vessel: Minimum coordinate surface required for native primary directions.
 */
struct NativeSpeculumPoint {
    std::string name;
    double lon = 0.0;
    double lat = 0.0;
    double ra = 0.0;
    double dec = 0.0;
    double ha = 0.0;
    double dsa = 0.0;
    double nsa = 0.0;
    bool upper = true;
    double f = 0.0;
    bool is_eastern = false;

    NativeSpeculumPoint() = default;
    NativeSpeculumPoint(
        std::string n, double l_deg, double b_deg, double ra_deg, double dec_deg,
        double ha_deg, double dsa_deg, double nsa_deg, bool is_upper, double f_val, bool eastern
    ) : name(std::move(n)), lon(l_deg), lat(b_deg), ra(ra_deg), dec(dec_deg),
        ha(ha_deg), dsa(dsa_deg), nsa(nsa_deg), upper(is_upper), f(f_val), is_eastern(eastern) {}
};

inline double primary_directions_checked_unit_argument(double value, const char* object_name) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string(object_name) + " requires a finite spherical argument");
    }
    if (value < -1.0 - PRIMARY_DIRECTIONS_DOMAIN_TOLERANCE || value > 1.0 + PRIMARY_DIRECTIONS_DOMAIN_TOLERANCE) {
        throw std::domain_error(std::string(object_name) + " has no real spherical solution");
    }
    return clamp(value, -1.0, 1.0);
}

/**
 * Sine of the angle between the meridian and the body's house circle.
 *
 * In the admitted Campanus-Regiomontanus conjunction geometry, the house
 * circle is the great-circle plane through the body and the north-south
 * horizon axis. In meridian-centred equatorial coordinates, the angle
 * between that plane and the meridian has components
 *
 *     transverse = cos(dec) sin(HA)
 *     meridional = cos(phi) cos(dec) cos(HA) + sin(phi) sin(dec).
 *
 * Their hypot ratio is the branch-independent sin(ZD) required by
 * sin(pole) = sin(phi) sin(ZD). This vector/plane invariant remains
 * continuous through MD=90, unlike a chain of principal atan(tan(...))
 * reductions.
 */
inline double campanus_regio_sin_zenith_distance(double dec, double ha, double geo_lat) {
    if (!std::isfinite(geo_lat) || geo_lat <= -90.0 || geo_lat >= 90.0) {
        throw std::invalid_argument("Campanus-Regiomontanus geometry requires geographic latitude in (-90, 90)");
    }
    if (!std::isfinite(dec) || !std::isfinite(ha)) {
        throw std::invalid_argument("Campanus-Regiomontanus geometry requires finite equatorial coordinates");
    }

    double phi = deg_to_rad(geo_lat);
    double dec_r = deg_to_rad(dec);
    double ha_r = deg_to_rad(ha);
    double transverse = std::cos(dec_r) * std::sin(ha_r);
    double meridional = std::cos(phi) * std::cos(dec_r) * std::cos(ha_r)
                      + std::sin(phi) * std::sin(dec_r);
    double plane_norm = std::hypot(transverse, meridional);
    if (plane_norm <= 1e-15) {
        throw std::domain_error("Campanus-Regiomontanus house circle is singular at the horizon axis");
    }
    return std::abs(transverse) / plane_norm;
}

/**
 * Pole height of a point under the Regiomontanus / Campanus circle of position.
 * Returns pole height in degrees.
 */
inline double regiomontanus_pole_height(double dec, double ha, double geo_lat) {
    double phi = deg_to_rad(geo_lat);
    double sin_zd = campanus_regio_sin_zenith_distance(dec, ha, geo_lat);
    double pole_argument = primary_directions_checked_unit_argument(
        std::sin(phi) * sin_zd,
        "Campanus-Regiomontanus pole"
    );
    double pole = std::asin(pole_argument);
    return rad_to_deg(pole);
}

/**
 * Pole height of a point under the Topocentric proportional semi-arc law.
 * Returns pole height in degrees.
 */
inline double topocentric_pole_height(double ha, double dsa, double nsa, bool upper, double geo_lat) {
    if (!std::isfinite(geo_lat) || geo_lat <= -90.0 || geo_lat >= 90.0) {
        throw std::invalid_argument("Topocentric pole requires geographic latitude in (-90, 90)");
    }
    if (!std::isfinite(ha)) {
        throw std::invalid_argument("Topocentric pole requires finite equatorial coordinates");
    }

    double sa = upper ? dsa : nsa;
    if (sa <= 1e-9) {
        throw std::domain_error("Topocentric pole requires a non-zero semi-arc");
    }

    double md = upper ? std::abs(ha) : (180.0 - std::abs(ha));
    double md_ratio = md / sa;
    double phi = deg_to_rad(geo_lat);
    return rad_to_deg(std::atan(md_ratio * std::tan(phi)));
}

/**
 * Oblique ascension or descension under an arbitrary circle of position pole height.
 * Returns oblique coordinate W in degrees in [0, 360).
 */
inline double under_pole_w(double ra, double dec, double pole_deg, bool is_eastern) {
    if (!std::isfinite(ra) || !std::isfinite(dec) || !std::isfinite(pole_deg)) {
        throw std::invalid_argument("Oblique ascension under pole requires finite coordinates");
    }
    double dec_r = deg_to_rad(dec);
    double pole_r = deg_to_rad(pole_deg);
    double offset_argument = primary_directions_checked_unit_argument(
        std::tan(dec_r) * std::tan(pole_r),
        "Oblique ascension under pole"
    );
    double offset = std::asin(offset_argument);
    double offset_deg = rad_to_deg(offset);
    if (is_eastern) {
        return normalize_deg_360(ra - offset_deg);
    }
    return normalize_deg_360(ra + offset_deg);
}

/**
 * Single directed arc under a given pole height and significator circle of position.
 * Returns arc in degrees in [0, 360).
 */
inline double under_pole_arc_native(
    double sig_ra, double sig_dec, bool sig_is_eastern,
    double prom_ra, double prom_dec, double pole_deg
) {
    double w_sig = under_pole_w(sig_ra, sig_dec, pole_deg, sig_is_eastern);
    double w_prom = under_pole_w(prom_ra, prom_dec, pole_deg, sig_is_eastern);
    return normalize_deg_360(w_prom - w_sig);
}

/**
 * Directed primary direction arc for Regiomontanus / Morinus / Campanus under-pole law.
 */
inline double regiomontanus_under_pole_arc(
    double sig_ra, double sig_dec, double sig_ha, bool sig_is_eastern,
    double prom_ra, double prom_dec, double geo_lat
) {
    double pole = regiomontanus_pole_height(sig_dec, sig_ha, geo_lat);
    return under_pole_arc_native(sig_ra, sig_dec, sig_is_eastern, prom_ra, prom_dec, pole);
}

/**
 * Directed primary direction arc for Topocentric under-pole law.
 */
inline double topocentric_under_pole_arc(
    double sig_ra, double sig_dec, double sig_ha, double sig_dsa, double sig_nsa,
    bool sig_upper, bool sig_is_eastern,
    double prom_ra, double prom_dec, double geo_lat
) {
    double pole = topocentric_pole_height(sig_ha, sig_dsa, sig_nsa, sig_upper, geo_lat);
    return under_pole_arc_native(sig_ra, sig_dec, sig_is_eastern, prom_ra, prom_dec, pole);
}

/**
 * Direct and converse role-exchanged arcs for a pair of points.
 * Method: 'R' for Regiomontanus / Morinus / Campanus, 'T' for Topocentric.
 */
inline std::pair<double, double> compute_under_pole_pair_arcs(
    const NativeSpeculumPoint& sig,
    const NativeSpeculumPoint& prom,
    double geo_lat,
    char method_code
) {
    double direct = 0.0;
    double converse = 0.0;

    if (method_code == 'R' || method_code == 'M' || method_code == 'C') {
        direct = regiomontanus_under_pole_arc(
            sig.ra, sig.dec, sig.ha, sig.is_eastern,
            prom.ra, prom.dec, geo_lat
        );
        converse = regiomontanus_under_pole_arc(
            prom.ra, prom.dec, prom.ha, prom.is_eastern,
            sig.ra, sig.dec, geo_lat
        );
    } else if (method_code == 'T') {
        direct = topocentric_under_pole_arc(
            sig.ra, sig.dec, sig.ha, sig.dsa, sig.nsa, sig.upper, sig.is_eastern,
            prom.ra, prom.dec, geo_lat
        );
        converse = topocentric_under_pole_arc(
            prom.ra, prom.dec, prom.ha, prom.dsa, prom.nsa, prom.upper, prom.is_eastern,
            sig.ra, sig.dec, geo_lat
        );
    } else {
        throw std::invalid_argument("Unknown under-pole method code: " + std::string(1, method_code));
    }

    return {direct, converse};
}

/**
 * Batched NxN primary directions under-pole arc matrix calculation.
 * Returns matrix of (direct, converse) pairs for all (i, j).
 */
inline std::vector<std::vector<std::pair<double, double>>> compute_under_pole_arcs_matrix(
    const std::vector<NativeSpeculumPoint>& points,
    double geo_lat,
    char method_code
) {
    size_t n = points.size();
    std::vector<std::vector<std::pair<double, double>>> matrix(n, std::vector<std::pair<double, double>>(n, {0.0, 0.0}));

    #pragma omp parallel for if(n > 4)
    for (int i = 0; i < static_cast<int>(n); ++i) {
        for (int j = 0; j < static_cast<int>(n); ++j) {
            if (i == j) {
                matrix[static_cast<size_t>(i)][static_cast<size_t>(j)] = {0.0, 0.0};
            } else {
                matrix[static_cast<size_t>(i)][static_cast<size_t>(j)] = compute_under_pole_pair_arcs(
                    points[static_cast<size_t>(i)],
                    points[static_cast<size_t>(j)],
                    geo_lat,
                    method_code
                );
            }
        }
    }

    return matrix;
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_PRIMARY_DIRECTIONS_HPP
