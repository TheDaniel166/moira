#ifndef MOIRA_NATIVE_CARTOGRAPHY_HPP
#define MOIRA_NATIVE_CARTOGRAPHY_HPP

#include <vector>
#include <cmath>
#include <algorithm>
#include <limits>
#include <utility>
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
            
            double ha_s = lst_r - s_ra;
            double sin_alt_s = sin_lat * std::sin(s_dec) + cos_lat * std::cos(s_dec) * std::cos(ha_s);
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
        hour_angle_out[i] = std::fmod(rad_to_deg(ha_r) + 180.0, 360.0);
        if (hour_angle_out[i] < 0.0) hour_angle_out[i] += 360.0;
        hour_angle_out[i] -= 180.0;

        const double m_dec    = std::asin(std::clamp(m_topo[2] / rm, -1.0, 1.0));
        const double m_ra     = std::atan2(m_topo[1], m_topo[0]);
        const double cos_sep  = std::sin(s_dec) * std::sin(m_dec)
                              + std::cos(s_dec) * std::cos(m_dec) * std::cos(s_ra - m_ra);
        const double sep_deg  = rad_to_deg(std::acos(std::clamp(cos_sep, -1.0, 1.0)));
        const double app_rs   = rad_to_deg(std::asin(std::clamp(sun_radius_km  / rs, -1.0, 1.0)));
        const double app_rm   = rad_to_deg(std::asin(std::clamp(moon_radius_km / rm, -1.0, 1.0)));
        raw_overlap_out[i] = (app_rs + app_rm) - sep_deg;
    }
}

inline void solar_cartography_grid_sweep_vectors(
    const double* sun_xyz_series,
    const double* moon_xyz_series,
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
    const double a = 6378.137;
    const double b = a * (1.0 - f);
    const double e2 = 1.0 - (b * b) / (a * a);

    for (size_t i = 0; i < observer_count; ++i) {
        overlap_max[i] = -1e18;
        central_max[i] = -1e18;
        magnitude_max[i] = 0.0;
    }

    for (size_t j = 0; j < jd_count; ++j) {
        const double gast_r = deg_to_rad(gasts_deg[j]);
        const Vec3 sun_xyz = {
            sun_xyz_series[j * 3 + 0],
            sun_xyz_series[j * 3 + 1],
            sun_xyz_series[j * 3 + 2],
        };
        const Vec3 moon_xyz = {
            moon_xyz_series[j * 3 + 0],
            moon_xyz_series[j * 3 + 1],
            moon_xyz_series[j * 3 + 2],
        };

        for (size_t i = 0; i < observer_count; ++i) {
            const double lat_r = deg_to_rad(lats_deg[i]);
            const double lon_r = deg_to_rad(lons_deg[i]);
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

            const double app_rs = rad_to_deg(std::asin(std::clamp(sun_radius_km / rs, -1.0, 1.0)));
            const double app_rm = rad_to_deg(std::asin(std::clamp(moon_radius_km / rm, -1.0, 1.0)));

            const double s_dec = std::asin(std::clamp(s_topo[2] / rs, -1.0, 1.0));
            const double s_ra = std::atan2(s_topo[1], s_topo[0]);
            const double m_dec = std::asin(std::clamp(m_topo[2] / rm, -1.0, 1.0));
            const double m_ra = std::atan2(m_topo[1], m_topo[0]);

            const double cos_sep = std::sin(s_dec) * std::sin(m_dec) + std::cos(s_dec) * std::cos(m_dec) * std::cos(s_ra - m_ra);
            const double sep_deg = rad_to_deg(std::acos(std::clamp(cos_sep, -1.0, 1.0)));

            const double overlap = (app_rs + app_rm) - sep_deg;
            const double central = std::abs(app_rm - app_rs) - sep_deg;
            double magnitude = (app_rs + app_rm - sep_deg) / std::max(2.0 * app_rs, 1e-9);
            if (magnitude < 0.0) magnitude = 0.0;

            if (overlap > overlap_max[i]) overlap_max[i] = overlap;
            if (central > central_max[i]) central_max[i] = central;
            if (magnitude > magnitude_max[i]) magnitude_max[i] = magnitude;
        }
    }
}

inline void solar_observer_quantities_batch_vectors(
    const double* sun_xyz,
    const double* moon_xyz,
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

    const Vec3 sun = {sun_xyz[0], sun_xyz[1], sun_xyz[2]};
    const Vec3 moon = {moon_xyz[0], moon_xyz[1], moon_xyz[2]};
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

        const Vec3 s_topo = {sun[0] - obs_x, sun[1] - obs_y, sun[2] - obs_z};
        const Vec3 m_topo = {moon[0] - obs_x, moon[1] - obs_y, moon[2] - obs_z};
        const double rs = s_topo.norm();
        const double rm = m_topo.norm();

        const double s_dec = std::asin(std::clamp(s_topo[2] / rs, -1.0, 1.0));
        const double s_ra = std::atan2(s_topo[1], s_topo[0]);
        const double ha_r = lst_r - s_ra;
        const double sin_alt = sin_lat * std::sin(s_dec) + cos_lat * std::cos(s_dec) * std::cos(ha_r);

        altitude_out[i] = rad_to_deg(std::asin(std::clamp(sin_alt, -1.0, 1.0)));
        hour_angle_out[i] = std::fmod(rad_to_deg(ha_r) + 180.0, 360.0);
        if (hour_angle_out[i] < 0.0) hour_angle_out[i] += 360.0;
        hour_angle_out[i] -= 180.0;

        const double m_dec = std::asin(std::clamp(m_topo[2] / rm, -1.0, 1.0));
        const double m_ra = std::atan2(m_topo[1], m_topo[0]);
        const double cos_sep = std::sin(s_dec) * std::sin(m_dec)
            + std::cos(s_dec) * std::cos(m_dec) * std::cos(s_ra - m_ra);
        const double sep_deg = rad_to_deg(std::acos(std::clamp(cos_sep, -1.0, 1.0)));
        const double app_rs = rad_to_deg(std::asin(std::clamp(sun_radius_km / rs, -1.0, 1.0)));
        const double app_rm = rad_to_deg(std::asin(std::clamp(moon_radius_km / rm, -1.0, 1.0)));
        raw_overlap_out[i] = (app_rs + app_rm) - sep_deg;
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

struct SolarCrossTrackRoot {
    double south_lat_deg;
    double south_lon_deg;
    double north_lat_deg;
    double north_lon_deg;
};

namespace detail {

inline double wrap_longitude_deg(double value) {
    double wrapped = std::fmod(value + 180.0, 360.0);
    if (wrapped < 0.0) wrapped += 360.0;
    wrapped -= 180.0;
    return wrapped == -180.0 ? 180.0 : wrapped;
}

inline std::pair<double, double> offset_point_deg(
    double lat_deg,
    double lon_deg,
    double bearing_deg,
    double distance_km
) {
    constexpr double earth_radius_km = 6378.137;
    const double angular_distance = distance_km / earth_radius_km;
    const double lat1 = deg_to_rad(lat_deg);
    const double lon1 = deg_to_rad(lon_deg);
    const double bearing = deg_to_rad(bearing_deg);

    const double sin_lat2 = std::sin(lat1) * std::cos(angular_distance)
        + std::cos(lat1) * std::sin(angular_distance) * std::cos(bearing);
    const double lat2 = std::asin(std::clamp(sin_lat2, -1.0, 1.0));
    const double lon2 = lon1 + std::atan2(
        std::sin(bearing) * std::sin(angular_distance) * std::cos(lat1),
        std::cos(angular_distance) - std::sin(lat1) * std::sin(lat2)
    );
    return {rad_to_deg(lat2), wrap_longitude_deg(rad_to_deg(lon2))};
}

inline double bearing_deg(
    double lat_a_deg,
    double lon_a_deg,
    double lat_b_deg,
    double lon_b_deg
) {
    const double lat1 = deg_to_rad(lat_a_deg);
    const double lat2 = deg_to_rad(lat_b_deg);
    const double dlon = deg_to_rad(lon_b_deg - lon_a_deg);
    const double y = std::sin(dlon) * std::cos(lat2);
    const double x = std::cos(lat1) * std::sin(lat2)
        - std::sin(lat1) * std::cos(lat2) * std::cos(dlon);
    double bearing = rad_to_deg(std::atan2(y, x));
    bearing = std::fmod(bearing, 360.0);
    if (bearing < 0.0) bearing += 360.0;
    return bearing;
}

struct SolarObserverMetrics {
    double overlap_margin;
    double central_margin;
    double magnitude;
};

inline SolarObserverMetrics solar_observer_metrics(
    const Vec3& sun_xyz,
    const Vec3& moon_xyz,
    double gast_deg,
    double lat_deg,
    double lon_deg,
    double sun_radius_km,
    double moon_radius_km,
    double horizon_sin_min
) {
    constexpr double f  = 1.0 / 298.257223563;
    constexpr double a  = 6378.137;
    constexpr double e2 = 1.0 - (1.0 - f) * (1.0 - f);
    constexpr double hidden = -1e18;

    const double lat_r = deg_to_rad(lat_deg);
    const double lon_r = deg_to_rad(lon_deg);
    const double lst_r = deg_to_rad(gast_deg) + lon_r;
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
    const double s_ra = std::atan2(s_topo[1], s_topo[0]);
    const double ha_s = lst_r - s_ra;
    const double sin_alt = sin_lat * std::sin(s_dec) + cos_lat * std::cos(s_dec) * std::cos(ha_s);
    if (sin_alt <= horizon_sin_min) {
        return {hidden, hidden, 0.0};
    }

    const double m_dec = std::asin(std::clamp(m_topo[2] / rm, -1.0, 1.0));
    const double m_ra = std::atan2(m_topo[1], m_topo[0]);
    const double cos_sep = std::sin(s_dec) * std::sin(m_dec)
        + std::cos(s_dec) * std::cos(m_dec) * std::cos(s_ra - m_ra);
    const double sep_deg = rad_to_deg(std::acos(std::clamp(cos_sep, -1.0, 1.0)));
    const double app_rs = rad_to_deg(std::asin(std::clamp(sun_radius_km / rs, -1.0, 1.0)));
    const double app_rm = rad_to_deg(std::asin(std::clamp(moon_radius_km / rm, -1.0, 1.0)));
    const double overlap = (app_rs + app_rm) - sep_deg;
    const double central = std::abs(app_rm - app_rs) - sep_deg;
    const double magnitude = std::max(0.0, (app_rs + app_rm - sep_deg) / std::max(2.0 * app_rs, 1e-9));
    return {overlap, central, magnitude};
}

inline Vec3 apply_aberration_velocity(const Vec3& xyz, const Vec3& velocity_xyz_per_day) {
    constexpr double c_km_per_day = 299792.458 * 86400.0;
    const double dist = xyz.norm();
    if (dist < 1e-10) return xyz;

    const double ux = xyz[0] / dist;
    const double uy = xyz[1] / dist;
    const double uz = xyz[2] / dist;

    const double bx = velocity_xyz_per_day[0] / c_km_per_day;
    const double by = velocity_xyz_per_day[1] / c_km_per_day;
    const double bz = velocity_xyz_per_day[2] / c_km_per_day;

    const double beta2 = bx * bx + by * by + bz * bz;
    const double gamma = 1.0 / std::sqrt(1.0 - beta2);
    const double dot = ux * bx + uy * by + uz * bz;
    const double factor1 = 1.0 + dot / (1.0 + gamma);
    const double factor2 = gamma * (1.0 + dot);

    double ax = (ux + factor1 * bx) / factor2;
    double ay = (uy + factor1 * by) / factor2;
    double az = (uz + factor1 * bz) / factor2;

    const double scale = dist / std::sqrt(ax * ax + ay * ay + az * az);
    return {ax * scale, ay * scale, az * scale};
}

inline Vec3 observer_position_icrf(double latitude_deg, double lst_deg, double elevation_m = 0.0) {
    constexpr double f = 1.0 / 298.257223563;
    constexpr double a = 6378.137;
    const double h = elevation_m / 1000.0;
    const double lat = deg_to_rad(latitude_deg);
    const double lst = deg_to_rad(lst_deg);
    const double cos_lat = std::cos(lat);
    const double sin_lat = std::sin(lat);
    const double C = 1.0 / std::sqrt(cos_lat * cos_lat + (1.0 - f) * (1.0 - f) * sin_lat * sin_lat);
    const double S = (1.0 - f) * (1.0 - f) * C;
    return {
        (a * C + h) * cos_lat * std::cos(lst),
        (a * C + h) * cos_lat * std::sin(lst),
        (a * S + h) * sin_lat,
    };
}

inline Vec3 observer_velocity_icrf(const Vec3& observer_position_icrf) {
    constexpr double earth_rotation_rate_rad_per_sec = 7.2921150e-5;
    constexpr double seconds_per_day = 86400.0;
    const double vx = -earth_rotation_rate_rad_per_sec * observer_position_icrf[1] * seconds_per_day;
    const double vy = earth_rotation_rate_rad_per_sec * observer_position_icrf[0] * seconds_per_day;
    return {vx, vy, 0.0};
}

inline double atmospheric_refraction_deg(double altitude_deg, double pressure_mbar = 1013.25, double temperature_c = 10.0) {
    const double alt = std::max(altitude_deg, -5.0);
    const double theta = alt + 7.31 / (alt + 4.4);
    const double ref_arcmin = 1.0 / std::tan(deg_to_rad(theta));
    const double pressure_term = pressure_mbar / 1010.0;
    const double temperature_term = 283.0 / (273.0 + temperature_c);
    return (ref_arcmin * pressure_term * temperature_term) / 60.0;
}

inline SolarObserverMetrics solar_observer_metrics_limit_semantics(
    const Vec3& sun_xyz,
    const Vec3& moon_xyz,
    double gast_deg,
    double lat_deg,
    double lon_deg,
    double sun_radius_km,
    double moon_radius_km
) {
    const double hidden = -std::numeric_limits<double>::infinity();
    const double lst_deg = gast_deg + lon_deg;
    const Vec3 observer_position = observer_position_icrf(lat_deg, lst_deg, 0.0);
    const Vec3 observer_velocity = observer_velocity_icrf(observer_position);

    Vec3 s_topo = {sun_xyz[0] - observer_position[0], sun_xyz[1] - observer_position[1], sun_xyz[2] - observer_position[2]};
    Vec3 m_topo = {moon_xyz[0] - observer_position[0], moon_xyz[1] - observer_position[1], moon_xyz[2] - observer_position[2]};
    s_topo = apply_aberration_velocity(s_topo, observer_velocity);
    m_topo = apply_aberration_velocity(m_topo, observer_velocity);

    const double rs = s_topo.norm();
    const double rm = m_topo.norm();
    const auto [s_ra_deg, s_dec_deg, _sdist] = vec3_to_radec(s_topo);
    const auto [m_ra_deg, m_dec_deg, _mdist] = vec3_to_radec(m_topo);
    const double ha_deg = std::fmod(lst_deg - s_ra_deg, 360.0);
    const double ha_r = deg_to_rad(ha_deg < 0.0 ? ha_deg + 360.0 : ha_deg);
    const double lat_r = deg_to_rad(lat_deg);
    const double s_dec_r = deg_to_rad(s_dec_deg);
    const double sin_alt = std::sin(s_dec_r) * std::sin(lat_r)
        + std::cos(s_dec_r) * std::cos(lat_r) * std::cos(ha_r);
    double alt_deg = rad_to_deg(std::asin(std::clamp(sin_alt, -1.0, 1.0)));
    alt_deg += atmospheric_refraction_deg(alt_deg);
    if (alt_deg <= 0.0) {
        return {hidden, hidden, 0.0};
    }

    const double cos_sep = std::sin(deg_to_rad(s_dec_deg)) * std::sin(deg_to_rad(m_dec_deg))
        + std::cos(deg_to_rad(s_dec_deg)) * std::cos(deg_to_rad(m_dec_deg))
        * std::cos(deg_to_rad(s_ra_deg - m_ra_deg));
    const double sep_deg = rad_to_deg(std::acos(std::clamp(cos_sep, -1.0, 1.0)));
    const double app_rs = rad_to_deg(std::asin(std::clamp(sun_radius_km / rs, -1.0, 1.0)));
    const double app_rm = rad_to_deg(std::asin(std::clamp(moon_radius_km / rm, -1.0, 1.0)));
    const double overlap = (app_rs + app_rm) - sep_deg;
    const double central = std::abs(app_rm - app_rs) - sep_deg;
    const double magnitude = std::max(0.0, (app_rs + app_rm - sep_deg) / std::max(2.0 * app_rs, 1e-9));
    return {overlap, central, magnitude};
}

} // namespace detail

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

inline std::vector<SolarCrossTrackRoot> solar_cross_track_limit_band(
    const IEvaluator& sun_eval,
    const IEvaluator& moon_eval,
    const double* jds,
    const double* gasts_deg,
    const double* center_lats_deg,
    const double* center_lons_deg,
    size_t count,
    int margin_kind,
    double max_distance_km,
    double sun_radius_km,
    double moon_radius_km
) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    std::vector<SolarCrossTrackRoot> roots(count, {nan, nan, nan, nan});
    if (count < 2) return roots;

    for (size_t index = 0; index < count; ++index) {
        const size_t forward_index = index == count - 1 ? index : index + 1;
        const size_t backward_index = index == 0 ? index : index - 1;
        const double track_bearing = detail::bearing_deg(
            center_lats_deg[backward_index], center_lons_deg[backward_index],
            center_lats_deg[forward_index], center_lons_deg[forward_index]
        );
        const double normals[2] = {
            std::fmod(track_bearing + 90.0, 360.0),
            std::fmod(track_bearing + 270.0, 360.0)
        };

        double s_geo[6], m_geo[6];
        sun_eval.evaluate(jds[index], s_geo);
        moon_eval.evaluate(jds[index], m_geo);
        const Vec3 sun_xyz = {s_geo[0], s_geo[1], s_geo[2]};
        const Vec3 moon_xyz = {m_geo[0], m_geo[1], m_geo[2]};

        double out_lat[2] = {nan, nan};
        double out_lon[2] = {nan, nan};
        for (int side = 0; side < 2; ++side) {
            const auto value_at = [&](double distance_km) -> double {
                const auto [lat, lon] = detail::offset_point_deg(
                    center_lats_deg[index], center_lons_deg[index], normals[side], distance_km
                );
                const auto metrics = detail::solar_observer_metrics(
                    sun_xyz, moon_xyz, gasts_deg[index], lat, lon, sun_radius_km, moon_radius_km, 0.0
                );
                return margin_kind == 0 ? metrics.overlap_margin : metrics.central_margin;
            };

            const double center_value = value_at(0.0);
            if (!std::isfinite(center_value) || center_value < 0.0) continue;

            double left = 0.0;
            double right = std::min(max_distance_km, 40.0);
            double right_value = value_at(right);
            while (std::isfinite(right_value) && right_value >= 0.0 && right < max_distance_km) {
                left = right;
                right = std::min(max_distance_km, right * 1.7);
                right_value = value_at(right);
            }
            if (!std::isfinite(right_value)) {
                double probe = right;
                bool found_finite = false;
                for (int i = 0; i < 6; ++i) {
                    probe = (left + probe) / 2.0;
                    const double probe_value = value_at(probe);
                    if (std::isfinite(probe_value)) {
                        right = probe;
                        right_value = probe_value;
                        found_finite = true;
                        break;
                    }
                }
                if (!found_finite) continue;
            }
            if (right_value > 0.0) continue;

            for (int i = 0; i < 40; ++i) {
                const double mid = (left + right) / 2.0;
                const double mid_value = value_at(mid);
                if (mid_value == 0.0) {
                    left = right = mid;
                    break;
                }
                if ((value_at(left) <= 0.0 && mid_value <= 0.0)
                    || (value_at(left) >= 0.0 && mid_value >= 0.0)) {
                    left = mid;
                } else {
                    right = mid;
                }
            }
            const auto [lat, lon] = detail::offset_point_deg(
                center_lats_deg[index], center_lons_deg[index], normals[side], (left + right) / 2.0
            );
            out_lat[side] = lat;
            out_lon[side] = lon;
        }

        roots[index] = {out_lat[0], out_lon[0], out_lat[1], out_lon[1]};
    }
    return roots;
}

inline std::vector<SolarCrossTrackRoot> solar_cross_track_magnitude_contour(
    const IEvaluator& sun_eval,
    const IEvaluator& moon_eval,
    const double* jds,
    const double* gasts_deg,
    const double* center_lats_deg,
    const double* center_lons_deg,
    size_t count,
    double threshold,
    double max_distance_km,
    double sun_radius_km,
    double moon_radius_km
) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    std::vector<SolarCrossTrackRoot> roots(count, {nan, nan, nan, nan});
    if (count < 2) return roots;

    for (size_t index = 0; index < count; ++index) {
        const size_t forward_index = index == count - 1 ? index : index + 1;
        const size_t backward_index = index == 0 ? index : index - 1;
        const double track_bearing = detail::bearing_deg(
            center_lats_deg[backward_index], center_lons_deg[backward_index],
            center_lats_deg[forward_index], center_lons_deg[forward_index]
        );
        const double normals[2] = {
            std::fmod(track_bearing + 90.0, 360.0),
            std::fmod(track_bearing + 270.0, 360.0)
        };

        double s_geo[6], m_geo[6];
        sun_eval.evaluate(jds[index], s_geo);
        moon_eval.evaluate(jds[index], m_geo);
        const Vec3 sun_xyz = {s_geo[0], s_geo[1], s_geo[2]};
        const Vec3 moon_xyz = {m_geo[0], m_geo[1], m_geo[2]};

        double out_lat[2] = {nan, nan};
        double out_lon[2] = {nan, nan};
        for (int side = 0; side < 2; ++side) {
            const auto value_at = [&](double distance_km) -> double {
                const auto [lat, lon] = detail::offset_point_deg(
                    center_lats_deg[index], center_lons_deg[index], normals[side], distance_km
                );
                const auto metrics = detail::solar_observer_metrics(
                    sun_xyz, moon_xyz, gasts_deg[index], lat, lon, sun_radius_km, moon_radius_km, -0.01003
                );
                return metrics.magnitude;
            };

            const double center_value = value_at(0.0);
            if (!std::isfinite(center_value) || center_value < threshold) continue;

            double left = 0.0;
            double right = std::min(max_distance_km, 40.0);
            double right_value = value_at(right);
            while (std::isfinite(right_value) && right_value >= threshold && right < max_distance_km) {
                left = right;
                right = std::min(max_distance_km, right * 1.7);
                right_value = value_at(right);
            }
            if (!std::isfinite(right_value)) {
                double probe = right;
                bool found_finite = false;
                for (int i = 0; i < 6; ++i) {
                    probe = (left + probe) / 2.0;
                    const double probe_value = value_at(probe);
                    if (std::isfinite(probe_value)) {
                        right = probe;
                        right_value = probe_value;
                        found_finite = true;
                        break;
                    }
                }
                if (!found_finite) continue;
            }
            if (right_value > threshold) continue;

            for (int i = 0; i < 40; ++i) {
                const double mid = (left + right) / 2.0;
                const double left_value = value_at(left) - threshold;
                const double mid_value = value_at(mid) - threshold;
                if (mid_value == 0.0) {
                    left = right = mid;
                    break;
                }
                if ((left_value <= 0.0 && mid_value <= 0.0)
                    || (left_value >= 0.0 && mid_value >= 0.0)) {
                    left = mid;
                } else {
                    right = mid;
                }
            }
            const auto [lat, lon] = detail::offset_point_deg(
                center_lats_deg[index], center_lons_deg[index], normals[side], (left + right) / 2.0
            );
            out_lat[side] = lat;
            out_lon[side] = lon;
        }

        roots[index] = {out_lat[0], out_lon[0], out_lat[1], out_lon[1]};
    }
    return roots;
}

inline std::vector<SolarCrossTrackRoot> solar_cross_track_limit_band_vectors(
    const double* sun_xyz_series,
    const double* moon_xyz_series,
    const double* gasts_deg,
    const double* center_lats_deg,
    const double* center_lons_deg,
    size_t count,
    int margin_kind,
    double max_distance_km,
    double sun_radius_km,
    double moon_radius_km
) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    std::vector<SolarCrossTrackRoot> roots(count, {nan, nan, nan, nan});
    if (count < 2) return roots;

    for (size_t index = 0; index < count; ++index) {
        const size_t forward_index = index == count - 1 ? index : index + 1;
        const size_t backward_index = index == 0 ? index : index - 1;
        const double track_bearing = detail::bearing_deg(
            center_lats_deg[backward_index], center_lons_deg[backward_index],
            center_lats_deg[forward_index], center_lons_deg[forward_index]
        );
        const double left_normal = std::fmod(track_bearing - 90.0 + 360.0, 360.0);
        const double right_normal = std::fmod(track_bearing + 90.0, 360.0);
        const double normals[2] = {left_normal, right_normal};

        const Vec3 sun_xyz = {
            sun_xyz_series[index * 3 + 0],
            sun_xyz_series[index * 3 + 1],
            sun_xyz_series[index * 3 + 2],
        };
        const Vec3 moon_xyz = {
            moon_xyz_series[index * 3 + 0],
            moon_xyz_series[index * 3 + 1],
            moon_xyz_series[index * 3 + 2],
        };

        double out_lat[2] = {nan, nan};
        double out_lon[2] = {nan, nan};
        for (int side = 0; side < 2; ++side) {
            const auto value_at = [&](double distance_km) -> double {
                const auto [lat, lon] = detail::offset_point_deg(
                    center_lats_deg[index], center_lons_deg[index], normals[side], distance_km
                );
                const auto metrics = detail::solar_observer_metrics_limit_semantics(
                    sun_xyz, moon_xyz, gasts_deg[index], lat, lon, sun_radius_km, moon_radius_km
                );
                return margin_kind == 0 ? metrics.overlap_margin : metrics.central_margin;
            };

            const double center_value = value_at(0.0);
            if (!std::isfinite(center_value) || center_value < 0.0) continue;

            double left = 0.0;
            double right = std::min(max_distance_km, 40.0);
            double right_value = value_at(right);
            while (std::isfinite(right_value) && right_value >= 0.0 && right < max_distance_km) {
                left = right;
                right = std::min(max_distance_km, right * 1.7);
                right_value = value_at(right);
            }
            if (!std::isfinite(right_value)) {
                double probe = right;
                bool found_finite = false;
                for (int i = 0; i < 6; ++i) {
                    probe = (left + probe) / 2.0;
                    const double probe_value = value_at(probe);
                    if (std::isfinite(probe_value)) {
                        right = probe;
                        right_value = probe_value;
                        found_finite = true;
                        break;
                    }
                }
                if (!found_finite) continue;
            }
            if (right_value > 0.0) continue;

            for (int i = 0; i < 40; ++i) {
                const double mid = (left + right) / 2.0;
                const double left_value = value_at(left);
                const double mid_value = value_at(mid);
                if (mid_value == 0.0) {
                    left = right = mid;
                    break;
                }
                if ((left_value <= 0.0 && mid_value <= 0.0) || (left_value >= 0.0 && mid_value >= 0.0)) {
                    left = mid;
                } else {
                    right = mid;
                }
            }
            const auto [lat, lon] = detail::offset_point_deg(
                center_lats_deg[index], center_lons_deg[index], normals[side], (left + right) / 2.0
            );
            out_lat[side] = lat;
            out_lon[side] = lon;
        }

        roots[index] = {out_lat[1], out_lon[1], out_lat[0], out_lon[0]};
    }
    return roots;
}

inline std::vector<SolarCrossTrackRoot> solar_cross_track_magnitude_contour_vectors(
    const double* sun_xyz_series,
    const double* moon_xyz_series,
    const double* gasts_deg,
    const double* center_lats_deg,
    const double* center_lons_deg,
    size_t count,
    double threshold,
    double max_distance_km,
    double sun_radius_km,
    double moon_radius_km
) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    std::vector<SolarCrossTrackRoot> roots(count, {nan, nan, nan, nan});
    if (count < 2) return roots;

    for (size_t index = 0; index < count; ++index) {
        const size_t forward_index = index == count - 1 ? index : index + 1;
        const size_t backward_index = index == 0 ? index : index - 1;
        const double track_bearing = detail::bearing_deg(
            center_lats_deg[backward_index], center_lons_deg[backward_index],
            center_lats_deg[forward_index], center_lons_deg[forward_index]
        );
        const double left_normal = std::fmod(track_bearing - 90.0 + 360.0, 360.0);
        const double right_normal = std::fmod(track_bearing + 90.0, 360.0);
        const double normals[2] = {left_normal, right_normal};

        const Vec3 sun_xyz = {
            sun_xyz_series[index * 3 + 0],
            sun_xyz_series[index * 3 + 1],
            sun_xyz_series[index * 3 + 2],
        };
        const Vec3 moon_xyz = {
            moon_xyz_series[index * 3 + 0],
            moon_xyz_series[index * 3 + 1],
            moon_xyz_series[index * 3 + 2],
        };

        double out_lat[2] = {nan, nan};
        double out_lon[2] = {nan, nan};
        for (int side = 0; side < 2; ++side) {
            const auto value_at = [&](double distance_km) -> double {
                const auto [lat, lon] = detail::offset_point_deg(
                    center_lats_deg[index], center_lons_deg[index], normals[side], distance_km
                );
                const auto metrics = detail::solar_observer_metrics(
                    sun_xyz, moon_xyz, gasts_deg[index], lat, lon, sun_radius_km, moon_radius_km, -0.01003
                );
                return metrics.magnitude;
            };

            const double center_value = value_at(0.0);
            if (!std::isfinite(center_value) || center_value < threshold) continue;

            double left = 0.0;
            double right = std::min(max_distance_km, 40.0);
            double right_value = value_at(right);
            while (std::isfinite(right_value) && right_value >= threshold && right < max_distance_km) {
                left = right;
                right = std::min(max_distance_km, right * 1.7);
                right_value = value_at(right);
            }
            if (!std::isfinite(right_value)) continue;
            if (right_value > threshold) continue;

            for (int i = 0; i < 40; ++i) {
                const double mid = (left + right) / 2.0;
                const double left_value = value_at(left) - threshold;
                const double mid_value = value_at(mid) - threshold;
                if (mid_value == 0.0) {
                    left = right = mid;
                    break;
                }
                if ((left_value <= 0.0 && mid_value <= 0.0) || (left_value >= 0.0 && mid_value >= 0.0)) {
                    left = mid;
                } else {
                    right = mid;
                }
            }
            const auto [lat, lon] = detail::offset_point_deg(
                center_lats_deg[index], center_lons_deg[index], normals[side], (left + right) / 2.0
            );
            out_lat[side] = lat;
            out_lon[side] = lon;
        }

        roots[index] = {out_lat[1], out_lon[1], out_lat[0], out_lon[0]};
    }
    return roots;
}

} // namespace native
} // namespace moira

#endif
