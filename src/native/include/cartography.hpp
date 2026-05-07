#ifndef MOIRA_NATIVE_CARTOGRAPHY_HPP
#define MOIRA_NATIVE_CARTOGRAPHY_HPP

#include <vector>
#include <cmath>
#include <algorithm>
#include "geometry.hpp"
#include "coordinates.hpp"
#include "evaluators.hpp"
#include "constants.hpp"

namespace moira {
namespace native {

/**
 * @brief THEOREM: Solar Cartography Grid Sweep.
 * Aggregates maximum eclipse margins and magnitudes across a time series.
 * 
 * Performance: O(JD_count * Observer_count). 
 * This is the 'Fast Path' for solar eclipse map generation.
 */
inline void solar_cartography_grid_sweep(
    const IEvaluator& sun_eval,
    const IEvaluator& moon_eval,
    const double* jds,
    const double* gasts_deg,
    size_t jd_count,
    const double* lats_deg,
    const double* lons_deg,
    size_t observer_count,
    double sun_radius_km,
    double moon_radius_km,
    double* overlap_max,
    double* central_max,
    double* magnitude_max
) {
    const double f = 1.0 / 298.257223563;
    const double a = 6378.137; // EARTH_RADIUS_KM
    const double b = a * (1.0 - f);
    const double e2 = 1.0 - (b * b) / (a * a);

    // Initialise results with sentinel values
    for (size_t i = 0; i < observer_count; ++i) {
        overlap_max[i] = -1e18;
        central_max[i] = -1e18;
        magnitude_max[i] = 0.0;
    }

    for (size_t j = 0; j < jd_count; ++j) {
        double jd = jds[j];
        double gast_r = deg_to_rad(gasts_deg[j]);

        double s_geo[6], m_geo[6];
        sun_eval.evaluate(jd, s_geo);
        moon_eval.evaluate(jd, m_geo);
        
        Vec3 sun_xyz = {s_geo[0], s_geo[1], s_geo[2]};
        Vec3 moon_xyz = {m_geo[0], m_geo[1], m_geo[2]};

        for (size_t i = 0; i < observer_count; ++i) {
            double lat_r = deg_to_rad(lats_deg[i]);
            double lon_r = deg_to_rad(lons_deg[i]);
            double lst_r = gast_r + lon_r;

            double sin_lat = std::sin(lat_r);
            double cos_lat = std::cos(lat_r);
            double N = a / std::sqrt(1.0 - e2 * sin_lat * sin_lat);

            double obs_x = N * cos_lat * std::cos(lst_r);
            double obs_y = N * cos_lat * std::sin(lst_r);
            double obs_z = (1.0 - e2) * N * sin_lat;

            Vec3 s_topo = {sun_xyz[0] - obs_x, sun_xyz[1] - obs_y, sun_xyz[2] - obs_z};
            Vec3 m_topo = {moon_xyz[0] - obs_x, moon_xyz[1] - obs_y, moon_xyz[2] - obs_z};

            double rs = s_topo.norm();
            double rm = m_topo.norm();

            // Apparent radii
            double app_rs = rad_to_deg(std::asin(std::clamp(sun_radius_km / rs, -1.0, 1.0)));
            double app_rm = rad_to_deg(std::asin(std::clamp(moon_radius_km / rm, -1.0, 1.0)));

            // Topocentric positions
            double s_dec = std::asin(std::clamp(s_topo[2] / rs, -1.0, 1.0));
            double s_ra = std::atan2(s_topo[1], s_topo[0]);
            
            // Horizon mask
            double ha_s = lst_r - s_ra;
            double sin_alt_s = sin_lat * std::sin(s_dec) + cos_lat * std::cos(s_dec) * std::cos(ha_s);
            
            if (sin_alt_s > -0.01003) {
                double m_dec = std::asin(std::clamp(m_topo[2] / rm, -1.0, 1.0));
                double m_ra = std::atan2(m_topo[1], m_topo[0]);
                
                double cos_sep = std::sin(s_dec) * std::sin(m_dec) + std::cos(s_dec) * std::cos(m_dec) * std::cos(s_ra - m_ra);
                double sep_deg = rad_to_deg(std::acos(std::clamp(cos_sep, -1.0, 1.0)));
                
                double overlap = (app_rs + app_rm) - sep_deg;
                double central = std::abs(app_rm - app_rs) - sep_deg;
                double magnitude = (app_rs + app_rm - sep_deg) / std::max(2.0 * app_rs, 1e-9);
                if (magnitude < 0) magnitude = 0;

                if (overlap > overlap_max[i]) overlap_max[i] = overlap;
                if (central > central_max[i]) central_max[i] = central;
                if (magnitude > magnitude_max[i]) magnitude_max[i] = magnitude;
            }
        }
    }
}

/**
 * @brief THEOREM: Lunar Cartography Grid Sweep.
 * Aggregates maximum eclipse altitudes and magnitudes.
 */
inline void lunar_cartography_grid_sweep(
    const IEvaluator& sun_eval,
    const IEvaluator& moon_eval,
    const double* jds,
    const double* gasts_deg,
    const double* magnitudes_base, // Magnitude at each JD (geocentric-ish)
    size_t jd_count,
    const double* lats_deg,
    const double* lons_deg,
    size_t observer_count,
    double* penumbral_max,
    double* partial_max,
    double* total_max,
    double* magnitude_max,
    const double* u1_u4, // [u1, u4] range or nullptr
    const double* u2_u3  // [u2, u3] range or nullptr
) {
    const double f = 1.0 / 298.257223563;
    const double a = 6378.137;
    const double b = a * (1.0 - f);
    const double e2 = 1.0 - (b * b) / (a * a);

    for (size_t i = 0; i < observer_count; ++i) {
        penumbral_max[i] = -1e18;
        partial_max[i] = -1e18;
        total_max[i] = -1e18;
        magnitude_max[i] = 0.0;
    }

    for (size_t j = 0; j < jd_count; ++j) {
        double jd = jds[j];
        double gast_r = deg_to_rad(gasts_deg[j]);
        double mag_base = magnitudes_base[j];

        double m_geo[6];
        moon_eval.evaluate(jd, m_geo);
        Vec3 moon_xyz = {m_geo[0], m_geo[1], m_geo[2]};

        bool in_partial = (u1_u4 && jd >= u1_u4[0] && jd <= u1_u4[1]);
        bool in_total = (u2_u3 && jd >= u2_u3[0] && jd <= u2_u3[1]);

        for (size_t i = 0; i < observer_count; ++i) {
            double lat_r = deg_to_rad(lats_deg[i]);
            double lon_r = deg_to_rad(lons_deg[i]);
            double lst_r = gast_r + lon_r;

            double sin_lat = std::sin(lat_r);
            double cos_lat = std::cos(lat_r);
            double N = a / std::sqrt(1.0 - e2 * sin_lat * sin_lat);

            double obs_x = N * cos_lat * std::cos(lst_r);
            double obs_y = N * cos_lat * std::sin(lst_r);
            double obs_z = (1.0 - e2) * N * sin_lat;

            Vec3 m_topo = {moon_xyz[0] - obs_x, moon_xyz[1] - obs_y, moon_xyz[2] - obs_z};
            double rm = m_topo.norm();

            double m_dec = std::asin(std::clamp(m_topo[2] / rm, -1.0, 1.0));
            double m_ra = std::atan2(m_topo[1], m_topo[0]);
            double ha_m = lst_r - m_ra;
            double sin_alt_m = sin_lat * std::sin(m_dec) + cos_lat * std::cos(m_dec) * std::cos(ha_m);
            double alt_deg = rad_to_deg(std::asin(std::clamp(sin_alt_m, -1.0, 1.0)));

            if (alt_deg > penumbral_max[i]) penumbral_max[i] = alt_deg;
            if (in_partial && alt_deg > partial_max[i]) partial_max[i] = alt_deg;
            if (in_total && alt_deg > total_max[i]) total_max[i] = alt_deg;

            if (sin_alt_m > -0.01003) {
                if (mag_base > magnitude_max[i]) magnitude_max[i] = mag_base;
            }
        }
    }
}

/**
 * @brief THEOREM: Native Solar Observer Quantities Batch.
 *
 * Computes per-observer sun altitude, hour-angle, and raw overlap margin
 * directly from cached geocentric state vectors at a single JD.
 * Replaces Python _topocentric_solar_observer_quantities_batch_backend lean pass —
 * eliminates the nutation/precession matrix chain per observer.
 */
inline void solar_observer_quantities_batch(
    const IEvaluator& sun_eval,
    const IEvaluator& moon_eval,
    double jd,
    double gast_deg,
    const double* lats_deg,
    const double* lons_deg,
    size_t n_obs,
    double sun_radius_km,
    double moon_radius_km,
    double* raw_overlap_out,
    double* altitude_out,
    double* hour_angle_out
) {
    constexpr double f  = 1.0 / 298.257223563;
    constexpr double a  = 6378.137;
    constexpr double e2 = 1.0 - (1.0 - f) * (1.0 - f);

    double s_geo[6], m_geo[6];
    sun_eval.evaluate(jd, s_geo);
    moon_eval.evaluate(jd, m_geo);
    const Vec3 sun_xyz  = {s_geo[0], s_geo[1], s_geo[2]};
    const Vec3 moon_xyz = {m_geo[0], m_geo[1], m_geo[2]};
    const double gast_r = deg_to_rad(gast_deg);

    for (size_t i = 0; i < n_obs; ++i) {
        const double lat_r = deg_to_rad(lats_deg[i]);
        const double lon_r = deg_to_rad(lons_deg[i]);
        const double lst_r = gast_r + lon_r;
        const double sin_lat = std::sin(lat_r);
        const double cos_lat = std::cos(lat_r);
        const double N = a / std::sqrt(1.0 - e2 * sin_lat * sin_lat);
        const double obs_x = N * cos_lat * std::cos(lst_r);
        const double obs_y = N * cos_lat * std::sin(lst_r);
        const double obs_z = (1.0 - e2) * N * sin_lat;

        const Vec3 s_topo  = {sun_xyz[0]  - obs_x, sun_xyz[1]  - obs_y, sun_xyz[2]  - obs_z};
        const Vec3 m_topo  = {moon_xyz[0] - obs_x, moon_xyz[1] - obs_y, moon_xyz[2] - obs_z};
        const double rs = s_topo.norm();
        const double rm = m_topo.norm();

        const double s_dec = std::asin(std::clamp(s_topo[2] / rs, -1.0, 1.0));
        const double s_ra  = std::atan2(s_topo[1], s_topo[0]);
        const double ha_r  = lst_r - s_ra;
        const double sin_alt = sin_lat * std::sin(s_dec)
                             + cos_lat * std::cos(s_dec) * std::cos(ha_r);

        altitude_out[i]   = rad_to_deg(std::asin(std::clamp(sin_alt, -1.0, 1.0)));
        hour_angle_out[i] = rad_to_deg(ha_r);

        if (sin_alt > -0.01003) {
            const double m_dec    = std::asin(std::clamp(m_topo[2] / rm, -1.0, 1.0));
            const double m_ra     = std::atan2(m_topo[1], m_topo[0]);
            const double cos_sep  = std::sin(s_dec) * std::sin(m_dec)
                                  + std::cos(s_dec) * std::cos(m_dec) * std::cos(s_ra - m_ra);
            const double sep_deg  = rad_to_deg(std::acos(std::clamp(cos_sep, -1.0, 1.0)));
            const double app_rs   = rad_to_deg(std::asin(std::clamp(sun_radius_km  / rs, -1.0, 1.0)));
            const double app_rm   = rad_to_deg(std::asin(std::clamp(moon_radius_km / rm, -1.0, 1.0)));
            raw_overlap_out[i] = (app_rs + app_rm) - sep_deg;
        } else {
            raw_overlap_out[i] = -1e18;
        }
    }
}

/**
 * @brief THEOREM: Native Solar Eclipse Greatest-Location Solver.
 *
 * Exact algorithmic port of Python _solve_solar_greatest_location().
 * At a fixed JD:
 *   1. Evaluate sun & moon geocentric vectors once.
 *   2. Coarse 20-degree grid scan (lat -80..80, lon -180..180).
 *   3. Multi-scale hill-climb: steps (10, 5, 2, 1, 0.5, 0.25, 0.1, 0.05) deg.
 * Zero Python boundary crossings during the search.
 *
 * @returns {best_lat_deg, best_lon_deg, best_separation_deg}
 */
struct GreatestLocationResult {
    double lat_deg;
    double lon_deg;
    double separation_deg;
};

inline GreatestLocationResult solar_find_greatest_eclipse_location(
    const IEvaluator& sun_eval,
    const IEvaluator& moon_eval,
    double jd,
    double gast_deg
) {
    // Evaluation constants — match Python manuscript
    constexpr double EARLY_EXIT_SEP  = 1.0e-4;
    constexpr int    MAX_EVALS       = 4096;
    constexpr double COARSE_LAT_STEP = 20.0;
    constexpr double COARSE_LON_STEP = 20.0;
    constexpr int    MAX_PASSES      = 512;
    constexpr double GEO_STEPS[]     = {10.0, 5.0, 2.0, 1.0, 0.5, 0.25, 0.1, 0.05};
    constexpr int    N_GEO_STEPS     = 8;

    // WGS-84 ellipsoid
    constexpr double f  = 1.0 / 298.257223563;
    constexpr double a  = 6378.137;
    constexpr double e2 = 1.0 - (1.0 - f) * (1.0 - f);

    // Evaluate geocentric state vectors once at this JD
    double s_geo[6], m_geo[6];
    sun_eval.evaluate(jd, s_geo);
    moon_eval.evaluate(jd, m_geo);
    const Vec3 sun_xyz = {s_geo[0], s_geo[1], s_geo[2]};
    const Vec3 moon_xyz = {m_geo[0], m_geo[1], m_geo[2]};
    const double gast_r = deg_to_rad(gast_deg);

    // Inline topocentric separation at (lat_deg, lon_deg)
    // Returns +inf if sun is below the geometric horizon.
    auto topo_sep = [&](double lat_deg, double lon_deg) -> double {
        // Wrap longitude
        lon_deg = std::fmod(lon_deg + 180.0, 360.0) - 180.0;

        const double lat_r = deg_to_rad(lat_deg);
        const double lon_r = deg_to_rad(lon_deg);
        const double lst_r = gast_r + lon_r;

        const double sin_lat = std::sin(lat_r);
        const double cos_lat = std::cos(lat_r);
        const double N = a / std::sqrt(1.0 - e2 * sin_lat * sin_lat);
        const double obs_x = N * cos_lat * std::cos(lst_r);
        const double obs_y = N * cos_lat * std::sin(lst_r);
        const double obs_z = (1.0 - e2) * N * sin_lat;

        const Vec3 s_topo = {sun_xyz[0] - obs_x, sun_xyz[1] - obs_y, sun_xyz[2] - obs_z};
        const Vec3 m_topo = {moon_xyz[0] - obs_x, moon_xyz[1] - obs_y, moon_xyz[2] - obs_z};

        const double rs = s_topo.norm();
        const double rm = m_topo.norm();

        const double s_dec = std::asin(std::clamp(s_topo[2] / rs, -1.0, 1.0));
        const double s_ra  = std::atan2(s_topo[1], s_topo[0]);
        const double ha_s  = lst_r - s_ra;
        const double sin_alt = sin_lat * std::sin(s_dec)
                             + cos_lat * std::cos(s_dec) * std::cos(ha_s);
        if (sin_alt <= -0.01003) return 1e18; // below horizon

        const double m_dec = std::asin(std::clamp(m_topo[2] / rm, -1.0, 1.0));
        const double m_ra  = std::atan2(m_topo[1], m_topo[0]);
        const double cos_sep = std::sin(s_dec) * std::sin(m_dec)
                             + std::cos(s_dec) * std::cos(m_dec) * std::cos(s_ra - m_ra);
        return rad_to_deg(std::acos(std::clamp(cos_sep, -1.0, 1.0)));
    };

    double best_lat = 0.0, best_lon = 0.0, best_sep = 1e18;
    int evals = 0;
    bool done = false;

    // --- Coarse grid scan ---
    for (double lat = -80.0; lat <= 80.0 + 1e-9 && !done; lat += COARSE_LAT_STEP) {
        for (double lon = -180.0; lon < 180.0 - 1e-9 && !done; lon += COARSE_LON_STEP) {
            if (evals >= MAX_EVALS) { done = true; break; }
            double sep = topo_sep(lat, lon);
            ++evals;
            if (sep < best_sep) {
                best_lat = lat; best_lon = lon; best_sep = sep;
                if (best_sep <= EARLY_EXIT_SEP) { done = true; break; }
            }
        }
    }

    // --- Multi-scale hill-climb ---
    for (int si = 0; si < N_GEO_STEPS && !done; ++si) {
        const double step = GEO_STEPS[si];
        bool improved = true;
        int passes = 0;
        while (improved && passes < MAX_PASSES && !done) {
            if (evals >= MAX_EVALS) { done = true; break; }
            ++passes;
            improved = false;
            for (int di = -1; di <= 1 && !done; ++di) {
                for (int dj = -1; dj <= 1 && !done; ++dj) {
                    if (di == 0 && dj == 0) continue;
                    if (evals >= MAX_EVALS) { done = true; break; }
                    double cand_lat = std::clamp(best_lat + di * step, -89.5, 89.5);
                    double cand_lon = best_lon + dj * step;
                    double sep = topo_sep(cand_lat, cand_lon);
                    ++evals;
                    if (sep < best_sep) {
                        best_lat = cand_lat; best_lon = cand_lon; best_sep = sep;
                        improved = true;
                        if (best_sep <= EARLY_EXIT_SEP) { done = true; break; }
                    }
                }
            }
        }
    }

    return {best_lat, best_lon, best_sep};
}

} // namespace native
} // namespace moira

#endif
