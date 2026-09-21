#ifndef MOIRA_NATIVE_HOUSES_HPP
#define MOIRA_NATIVE_HOUSES_HPP

#include <cmath>
#include <array>
#include <tuple>
#include <string>
#include <stdexcept>

#include "constants.hpp"
#include "math_utils.hpp"
#include "geometry.hpp"
#include "precession.hpp"
#include "sidereal.hpp"
#include "nutation.hpp"

namespace moira {
namespace native {

// --- Cardines & Angles ---

inline double mc_from_armc(double armc, double obliquity) {
    double armc_r = armc * DEG2RAD;
    double eps_r  = obliquity * DEG2RAD;
    return normalize_deg_360(std::atan2(std::sin(armc_r), std::cos(armc_r) * std::cos(eps_r)) * RAD2DEG);
}

inline double asc_from_armc(double armc, double obliquity, double lat) {
    double armc_r = armc * DEG2RAD;
    double eps_r  = obliquity * DEG2RAD;
    double lat_r  = lat * DEG2RAD;

    double y   = -std::cos(armc_r);
    double x   =  std::sin(armc_r) * std::cos(eps_r) + std::tan(lat_r) * std::sin(eps_r);
    double raw = normalize_deg_360(std::atan2(y, x) * RAD2DEG);

    double expected = normalize_deg_360(armc + 90.0);
    double alt      = normalize_deg_360(raw + 180.0);

    auto adist = [](double a, double b) {
        double d = normalize_deg_360(std::abs(a - b));
        return (d <= 180.0) ? d : 360.0 - d;
    };

    double chosen = (adist(alt, expected) < adist(raw, expected)) ? alt : raw;
    return normalize_deg_360(chosen);
}

inline double vertex_from_armc(double armc, double obliquity, double lat) {
    double sin_lat = std::sin(lat * DEG2RAD);
    if (std::abs(sin_lat) < 1e-9) {
        return 0.0;
    }

    double armc_r = armc * DEG2RAD;
    double eps_r  = obliquity * DEG2RAD;
    double lat_r  = lat * DEG2RAD;

    double y = -std::cos(armc_r);
    double x = std::sin(armc_r) * std::cos(eps_r) - (std::cos(lat_r) / sin_lat) * std::sin(eps_r);

    double raw  = normalize_deg_360(std::atan2(y, x) * RAD2DEG);
    double alt  = normalize_deg_360(raw + 180.0);
    double west = normalize_deg_360(armc - 90.0);

    auto adist = [](double a, double b) {
        double d = normalize_deg_360(std::abs(a - b));
        return (d <= 180.0) ? d : 360.0 - d;
    };

    double chosen = (adist(alt, west) < adist(raw, west)) ? alt : raw;
    return normalize_deg_360(chosen);
}

inline double east_point_from_armc(double armc, double obliquity) {
    double ra = normalize_deg_360(armc + 90.0);
    double ra_r = ra * DEG2RAD;
    double eps_r = obliquity * DEG2RAD;
    double y = std::sin(ra_r) * std::cos(eps_r);
    double x = std::cos(ra_r);
    return normalize_deg_360(std::atan2(y, x) * RAD2DEG);
}

/**
 * Reduce UT1 and geographic observer location to local celestial angles.
 * Returns (armc, obliquity, dpsi, mc, asc, vertex, east_point).
 */
inline std::tuple<double, double, double, double, double, double, double> reduce_local_angles(
    double jd_ut,
    double jd_tt,
    double lat,
    double lon
) {
    NutationResult nut = nutation_2000r06(jd_tt);
    double dpsi = nut.longitude * RAD2DEG;
    double deps = nut.obliquity * RAD2DEG;
    double eps0 = mean_obliquity_p03(jd_tt);
    double obliquity = eps0 + deps;
    double gast = apparent_sidereal_time(jd_ut, dpsi, obliquity);
    double armc = normalize_deg_360(gast + lon);
    double mc = mc_from_armc(armc, obliquity);
    double asc = asc_from_armc(armc, obliquity, lat);
    double vertex = vertex_from_armc(armc, obliquity, lat);
    double east_point = east_point_from_armc(armc, obliquity);

    return std::make_tuple(armc, obliquity, dpsi, mc, asc, vertex, east_point);
}

// --- House Geometry Solvers ---

inline std::array<double, 12> porphyry_cusps(double asc, double mc) {
    double ic  = mod_floor(mc  + 180.0, 360.0);
    double dsc = mod_floor(asc + 180.0, 360.0);

    std::array<double, 12> cusps{};
    cusps[0] = asc;
    cusps[3] = ic;
    cusps[6] = dsc;
    cusps[9] = mc;

    auto trisect = [](double start, double end) -> std::pair<double, double> {
        double span = mod_floor(end - start, 360.0);
        return {
            mod_floor(start + span / 3.0, 360.0),
            mod_floor(start + 2.0 * span / 3.0, 360.0)
        };
    };

    auto [c2, c3]   = trisect(asc, ic);
    auto [c5, c6]   = trisect(ic,  dsc);
    auto [c8, c9]   = trisect(dsc, mc);
    auto [c11, c12] = trisect(mc,  asc);

    cusps[1]  = c2;
    cusps[2]  = c3;
    cusps[4]  = c5;
    cusps[5]  = c6;
    cusps[7]  = c8;
    cusps[8]  = c9;
    cusps[10] = c11;
    cusps[11] = c12;

    return cusps;
}

inline std::array<double, 12> equal_cusps(double asc) {
    std::array<double, 12> cusps{};
    for (int i = 0; i < 12; ++i) {
        cusps[i] = mod_floor(asc + i * 30.0, 360.0);
    }
    return cusps;
}

inline std::array<double, 12> whole_sign_cusps(double asc) {
    std::array<double, 12> cusps{};
    double base = std::floor(asc / 30.0) * 30.0;
    for (int i = 0; i < 12; ++i) {
        cusps[i] = mod_floor(base + i * 30.0, 360.0);
    }
    return cusps;
}

inline std::array<double, 12> placidus_cusps(double armc, double obliquity, double lat) {
    double eps    = obliquity * DEG2RAD;
    double armc_r = armc      * DEG2RAD;
    double ic_r   = armc_r + PI;

    double cos_eps = std::cos(eps);
    double phi     = lat * DEG2RAD;

    double mc  = mc_from_armc(armc, obliquity);
    double asc = asc_from_armc(armc, obliquity, lat);

    double asc_r = asc * DEG2RAD;
    double sin_asc = std::sin(asc_r);
    double ra_asc_r = std::atan2(sin_asc * cos_eps, std::cos(asc_r));
    double dsa_asc = mod_floor(ra_asc_r - armc_r, TAU);
    if (dsa_asc > PI) {
        dsa_asc = TAU - dsa_asc;
    }
    double nsa_asc = PI - dsa_asc;

    auto lam_to_ra = [cos_eps](double lam) noexcept -> double {
        return std::atan2(std::sin(lam) * cos_eps, std::cos(lam));
    };

    auto ra_to_lam = [cos_eps](double ra) noexcept -> double {
        return std::atan2(std::sin(ra), cos_eps * std::cos(ra));
    };

    auto dra_d_lam = [cos_eps](double lam) noexcept -> double {
        double sin_lam = std::sin(lam);
        double cos_lam = std::cos(lam);
        double den = cos_lam * cos_lam + sin_lam * sin_lam * cos_eps * cos_eps;
        if (std::abs(den) < 1e-15) {
            return 1.0;
        }
        return cos_eps / den;
    };

    auto semi_arc_event = [eps, phi](double lam) -> std::pair<double, double> {
        double sin_dec = std::sin(eps) * std::sin(lam);
        double dec = safe_asin(sin_dec);
        double arg = -std::tan(phi) * std::tan(dec);
        if (arg < -1.0 || arg > 1.0) {
            throw std::domain_error("placidus semi-arc event out of domain");
        }
        double dsa = std::acos(arg);
        double sin_dsa = std::sin(dsa);
        if (std::abs(sin_dsa) < 1e-12) {
            return {dsa, 0.0};
        }
        double d_dec_d_lam = std::sin(eps) * std::cos(lam) / std::cos(dec);
        double d_dsa_d_lam = (std::tan(phi) / (std::cos(dec) * std::cos(dec)) * d_dec_d_lam) / sin_dsa;
        return {dsa, d_dsa_d_lam};
    };

    constexpr double MAX_STEP = PI / 3.0; // 60 degrees

    auto solve_upper = [&](double frac) -> double {
        double lam = ra_to_lam(armc_r + frac * dsa_asc);
        for (int iter = 0; iter < 30; ++iter) {
            auto [dsa, d_dsa] = semi_arc_event(lam);
            double ra_lam = lam_to_ra(lam);
            ra_lam = armc_r + mod_floor(ra_lam - armc_r + PI, TAU) - PI;
            double f  = ra_lam - armc_r - frac * dsa;
            double df = dra_d_lam(lam) - frac * d_dsa;
            if (std::abs(df) < 1e-15) {
                break;
            }
            double step = clamp(f / df, -MAX_STEP, MAX_STEP);
            lam -= step;
            if (std::abs(step) < 1e-12) {
                break;
            }
        }
        return mod_floor(lam * RAD2DEG, 360.0);
    };

    auto solve_lower = [&](double frac) -> double {
        double lam = ra_to_lam(ic_r - frac * nsa_asc);
        for (int iter = 0; iter < 30; ++iter) {
            auto [dsa, d_dsa] = semi_arc_event(lam);
            double nsa = PI - dsa;
            double ra_lam = lam_to_ra(lam);
            ra_lam = ic_r + mod_floor(ra_lam - ic_r + PI, TAU) - PI;
            double f  = ra_lam - ic_r + frac * nsa;
            double df = dra_d_lam(lam) - frac * d_dsa;
            if (std::abs(df) < 1e-15) {
                break;
            }
            double step = clamp(f / df, -MAX_STEP, MAX_STEP);
            lam -= step;
            if (std::abs(step) < 1e-12) {
                break;
            }
        }
        return mod_floor(lam * RAD2DEG, 360.0);
    };

    std::array<double, 12> cusps{};
    cusps[0] = asc;
    cusps[3] = mod_floor(mc + 180.0, 360.0);
    cusps[6] = mod_floor(asc + 180.0, 360.0);
    cusps[9] = mc;

    cusps[10] = solve_upper(1.0 / 3.0);
    cusps[11] = solve_upper(2.0 / 3.0);
    cusps[2]  = solve_lower(1.0 / 3.0);
    cusps[1]  = solve_lower(2.0 / 3.0);

    cusps[4] = mod_floor(cusps[10] + 180.0, 360.0);
    cusps[5] = mod_floor(cusps[11] + 180.0, 360.0);
    cusps[7] = mod_floor(cusps[1]  + 180.0, 360.0);
    cusps[8] = mod_floor(cusps[2]  + 180.0, 360.0);

    return cusps;
}

// --- Horizon Basis & Vector Geometry for Quadrant Systems ---

inline std::tuple<Vec3, Vec3, Vec3> local_horizon_basis(double armc_deg, double latitude_deg) {
    double phi   = latitude_deg * DEG2RAD;
    double theta = armc_deg * DEG2RAD;
    double sin_theta = std::sin(theta);
    double cos_theta = std::cos(theta);

    Vec3 east(-sin_theta, cos_theta, 0.0);
    Vec3 north(
        -std::sin(phi) * cos_theta,
        -std::sin(phi) * sin_theta,
        std::cos(phi)
    );
    Vec3 zenith(
        std::cos(phi) * cos_theta,
        std::cos(phi) * sin_theta,
        std::sin(phi)
    );
    return {east, north, zenith};
}

inline std::pair<Vec3, Vec3> ecliptic_intersection_candidates(const Vec3& plane_normal, double obliquity_deg) {
    double eps_r = obliquity_deg * DEG2RAD;
    Vec3 ecl_north(0.0, -std::sin(eps_r), std::cos(eps_r));
    Vec3 primary = Vec3::cross(plane_normal, ecl_north).unit();
    Vec3 secondary(-primary[0], -primary[1], -primary[2]);
    return {primary, secondary};
}

inline double ecliptic_longitude_from_equatorial_vector(const Vec3& v, double obliquity_deg) {
    Vec3 u = v.unit();
    double eps_r = obliquity_deg * DEG2RAD;
    double y_ecl = u[1] * std::cos(eps_r) + u[2] * std::sin(eps_r);
    return normalize_deg_360(std::atan2(y_ecl, u[0]) * RAD2DEG);
}

inline bool in_forward_arc(double lon, double start, double end) {
    return mod_floor(lon - start, 360.0) < mod_floor(end - start, 360.0);
}

inline double select_antipodal_branch(double lon, double arc_start, double arc_end) {
    double lon_alt = normalize_deg_360(lon + 180.0);
    if (in_forward_arc(lon, arc_start, arc_end)) {
        return lon;
    }
    if (in_forward_arc(lon_alt, arc_start, arc_end)) {
        return lon_alt;
    }

    double span = mod_floor(arc_end - arc_start, 360.0);
    double target = normalize_deg_360(arc_start + span / 2.0);

    auto adist = [](double a, double b) {
        double d = mod_floor(std::abs(a - b), 360.0);
        return (d <= 180.0) ? d : 360.0 - d;
    };

    if (adist(lon, target) <= adist(lon_alt, target)) {
        return lon;
    }
    return lon_alt;
}

inline double select_horizon_branch(
    const Vec3& primary,
    const Vec3& secondary,
    const Vec3& zenith,
    bool prefer_above_horizon,
    double obliquity_deg,
    double tie_arc_start,
    double tie_arc_end
) {
    double height_primary   = Vec3::dot(primary.unit(), zenith);
    double height_secondary = Vec3::dot(secondary.unit(), zenith);
    double lon_primary   = ecliptic_longitude_from_equatorial_vector(primary, obliquity_deg);
    double lon_secondary = ecliptic_longitude_from_equatorial_vector(secondary, obliquity_deg);
    constexpr double eps = 1e-12;

    if (prefer_above_horizon) {
        if (height_primary > eps && height_secondary < -eps) return lon_primary;
        if (height_secondary > eps && height_primary < -eps) return lon_secondary;
    } else {
        if (height_primary < -eps && height_secondary > eps) return lon_primary;
        if (height_secondary < -eps && height_primary > eps) return lon_secondary;
    }

    return select_antipodal_branch(lon_primary, tie_arc_start, tie_arc_end);
}

inline double project_pole_height_cusp(
    double ra_deg,
    double pole_height_deg,
    double obliquity_deg,
    const Vec3& zenith,
    bool prefer_above_horizon,
    double tie_arc_start,
    double tie_arc_end
) {
    double ra_r   = ra_deg * DEG2RAD;
    double pole_r = pole_height_deg * DEG2RAD;
    double cp     = std::cos(pole_r);
    double sp     = std::sin(pole_r);
    Vec3 plane_normal(-std::sin(ra_r) * cp, std::cos(ra_r) * cp, -sp);
    auto [primary, secondary] = ecliptic_intersection_candidates(plane_normal, obliquity_deg);
    return select_horizon_branch(
        primary,
        secondary,
        zenith,
        prefer_above_horizon,
        obliquity_deg,
        tie_arc_start,
        tie_arc_end
    );
}

inline double mc_above_horizon(double mc, double obliquity, double lat) {
    double eps_r = obliquity * DEG2RAD;
    double sin_dec = clamp(std::sin(eps_r) * std::sin(mc * DEG2RAD), -1.0, 1.0);
    double dec_r = std::asin(sin_dec);
    double sin_alt = std::sin(lat * DEG2RAD) * std::sin(dec_r)
                   + std::cos(lat * DEG2RAD) * std::cos(dec_r);
    return (sin_alt < 0.0) ? normalize_deg_360(mc + 180.0) : mc;
}

inline std::array<double, 12> assemble_antipodal_quadrant_cusps(
    double asc,
    double mc,
    double h2,
    double h3,
    double h11,
    double h12
) {
    std::array<double, 12> cusps{};
    cusps[0] = normalize_deg_360(asc);
    cusps[1] = normalize_deg_360(h2);
    cusps[2] = normalize_deg_360(h3);
    cusps[3] = normalize_deg_360(mc + 180.0);
    cusps[4] = normalize_deg_360(h11 + 180.0);
    cusps[5] = normalize_deg_360(h12 + 180.0);
    cusps[6] = normalize_deg_360(asc + 180.0);
    cusps[7] = normalize_deg_360(h2 + 180.0);
    cusps[8] = normalize_deg_360(h3 + 180.0);
    cusps[9] = normalize_deg_360(mc);
    cusps[10] = normalize_deg_360(h11);
    cusps[11] = normalize_deg_360(h12);
    return cusps;
}

inline std::array<double, 12> koch_cusps(double armc, double obliquity, double lat) {
    double mc  = mc_from_armc(armc, obliquity);
    double asc = asc_from_armc(armc, obliquity, lat);
    double ic  = normalize_deg_360(mc + 180.0);

    auto [east, north, zenith] = local_horizon_basis(armc, lat);

    double mc_r  = mc * DEG2RAD;
    double eps_r = obliquity * DEG2RAD;
    Vec3 v_mc(std::cos(mc_r), std::sin(mc_r) * std::cos(eps_r), std::sin(mc_r) * std::sin(eps_r));

    double cos_dec_mc = std::hypot(v_mc[0], v_mc[1]);
    double cos_lat    = std::hypot(zenith[0], zenith[1]);

    double horizon_product = 0.0;
    if (cos_dec_mc > 0.0 && cos_lat > 0.0) {
        horizon_product = clamp((v_mc[2] * zenith[2]) / (cos_dec_mc * cos_lat), -1.0, 1.0);
    }

    double dsa_deg = std::acos(-horizon_product) * RAD2DEG;
    double ad_mc   = std::asin(horizon_product) * RAD2DEG;

    double oa_mc = armc - ad_mc;
    double oa_ic = (armc + 180.0) + ad_mc;

    double h2  = project_pole_height_cusp(oa_ic - 2.0 * dsa_deg / 3.0, lat, obliquity, zenith, false, asc, ic);
    double h3  = project_pole_height_cusp(oa_ic - dsa_deg / 3.0, lat, obliquity, zenith, false, asc, ic);
    double h11 = project_pole_height_cusp(oa_mc + dsa_deg / 3.0, lat, obliquity, zenith, true, mc, asc);
    double h12 = project_pole_height_cusp(oa_mc + 2.0 * dsa_deg / 3.0, lat, obliquity, zenith, true, mc, asc);

    return assemble_antipodal_quadrant_cusps(asc, mc, h2, h3, h11, h12);
}

inline std::array<double, 12> regiomontanus_cusps(double armc, double obliquity, double lat) {
    double mc_raw = mc_from_armc(armc, obliquity);
    double mc  = mc_above_horizon(mc_raw, obliquity, lat);
    double asc = asc_from_armc(armc, obliquity, lat);
    double ic  = normalize_deg_360(mc + 180.0);

    double phi = lat * DEG2RAD;
    double phi_h1 = std::atan(std::tan(phi) * std::sin(30.0 * DEG2RAD)) * RAD2DEG;
    double phi_h2 = std::atan(std::tan(phi) * std::sin(60.0 * DEG2RAD)) * RAD2DEG;

    auto [east, north, zenith] = local_horizon_basis(armc, lat);

    double h2  = project_pole_height_cusp(armc + 120.0, phi_h2, obliquity, zenith, false, asc, ic);
    double h3  = project_pole_height_cusp(armc + 150.0, phi_h1, obliquity, zenith, false, asc, ic);
    double h11 = project_pole_height_cusp(armc + 30.0, phi_h1, obliquity, zenith, true, mc, asc);
    double h12 = project_pole_height_cusp(armc + 60.0, phi_h2, obliquity, zenith, true, mc, asc);

    return assemble_antipodal_quadrant_cusps(asc, mc, h2, h3, h11, h12);
}

inline std::array<double, 12> campanus_cusps(double armc, double obliquity, double lat) {
    double mc_raw = mc_from_armc(armc, obliquity);
    double mc  = mc_above_horizon(mc_raw, obliquity, lat);
    double asc = asc_from_armc(armc, obliquity, lat);
    double ic  = normalize_deg_360(mc + 180.0);

    auto [east, north, zenith] = local_horizon_basis(armc, lat);

    auto campanus_cusp = [&](double alpha_deg, bool prefer_above_horizon, double tie_start, double tie_end) -> double {
        double alpha = alpha_deg * DEG2RAD;
        Vec3 plane_normal(
            std::cos(alpha) * east[0] + std::sin(alpha) * zenith[0],
            std::cos(alpha) * east[1] + std::sin(alpha) * zenith[1],
            std::cos(alpha) * east[2] + std::sin(alpha) * zenith[2]
        );
        auto [primary, secondary] = ecliptic_intersection_candidates(plane_normal, obliquity);
        return select_horizon_branch(primary, secondary, zenith, prefer_above_horizon, obliquity, tie_start, tie_end);
    };

    double h2  = campanus_cusp(60.0, false, asc, ic);
    double h3  = campanus_cusp(30.0, false, asc, ic);
    double h11 = campanus_cusp(150.0, true, mc, asc);
    double h12 = campanus_cusp(120.0, true, mc, asc);

    return assemble_antipodal_quadrant_cusps(asc, mc, h2, h3, h11, h12);
}

inline std::array<double, 12> calculate_houses_cusps(
    double armc,
    double obliquity,
    double lat,
    double asc,
    double mc,
    char system
) {
    switch (system) {
        case 'P':
            return placidus_cusps(armc, obliquity, lat);
        case 'K':
            return koch_cusps(armc, obliquity, lat);
        case 'R':
            return regiomontanus_cusps(armc, obliquity, lat);
        case 'C':
            return campanus_cusps(armc, obliquity, lat);
        case 'O':
            return porphyry_cusps(asc, mc);
        case 'E':
            return equal_cusps(asc);
        case 'W':
            return whole_sign_cusps(asc);
        default:
            throw std::invalid_argument(std::string("Unsupported native house system: ") + system);
    }
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_HOUSES_HPP
