#ifndef MOIRA_NATIVE_VISIBILITY_HPP
#define MOIRA_NATIVE_VISIBILITY_HPP

#include "geometry.hpp"
#include "evaluators.hpp"
#include "coordinates.hpp"
#include "solvers.hpp"
#include "math_utils.hpp"
#include "sidereal.hpp"
#include "precession.hpp"
#include "nutation.hpp"
#include <optional>
#include <string>
#include <algorithm>

namespace moira {
namespace native {

// ---------------------------------------------------------------------------
// Enums and Policy Vessels
// ---------------------------------------------------------------------------

enum class LightPollutionClass {
    BORTLE_1 = 1, BORTLE_2, BORTLE_3, BORTLE_4, BORTLE_5,
    BORTLE_6, BORTLE_7, BORTLE_8, BORTLE_9
};

enum class ObserverAid {
    NAKED_EYE, BINOCULARS, TELESCOPE
};

enum class VisibilityCriterionFamily {
    LIMITING_MAGNITUDE_THRESHOLD,
    YALLOP_LUNAR_CRESCENT
};

struct ObserverVisibilityEnvironment {
    std::optional<LightPollutionClass> light_pollution_class = LightPollutionClass::BORTLE_3;
    std::optional<double> limiting_magnitude;
    double local_horizon_altitude_deg = 0.0;
    double temperature_c = 10.0;
    double pressure_mbar = 1013.25;
    double relative_humidity = 0.5;
    double observer_altitude_m = 0.0;
    ObserverAid observing_aid = ObserverAid::NAKED_EYE;
};

enum class VisibilityExtinctionModel {
    LEGACY_ARCUS_VISIONIS
};

enum class VisibilityTwilightModel {
    ARCUS_VISIONIS_SOLAR_DEPRESSION
};

enum class MoonlightPolicy {
    IGNORE,
    KRISCIUNAS_SCHAEFER_1991
};

struct VisibilityPolicy {
    VisibilityCriterionFamily criterion_family = VisibilityCriterionFamily::LIMITING_MAGNITUDE_THRESHOLD;
    ObserverVisibilityEnvironment environment;
    VisibilityExtinctionModel extinction_model = VisibilityExtinctionModel::LEGACY_ARCUS_VISIONIS;
    VisibilityTwilightModel twilight_model = VisibilityTwilightModel::ARCUS_VISIONIS_SOLAR_DEPRESSION;
    bool use_refraction = true;
    MoonlightPolicy moonlight_policy = MoonlightPolicy::IGNORE;
    double extinction_coefficient_k = 0.20;
};

// ---------------------------------------------------------------------------
// Core Algorithms
// ---------------------------------------------------------------------------

inline Vec3 apply_annual_aberration(
    const Vec3& target_icrf,
    const IEvaluator& earth_eval,
    double jd_tt
) {
    double earth_state[6];
    earth_eval.evaluate(jd_tt, earth_state);
    const Vec3 earth_velocity = {earth_state[3], earth_state[4], earth_state[5]};
    constexpr double c_km_per_day = 173.14463267424034 * KM_PER_AU;

    const double distance = target_icrf.norm();
    if (distance <= 1.0e-10) return target_icrf;

    const Vec3 unit = target_icrf * (1.0 / distance);
    const Vec3 beta = earth_velocity * (1.0 / c_km_per_day);
    const double beta2 = beta[0] * beta[0] + beta[1] * beta[1] + beta[2] * beta[2];
    const double gamma = 1.0 / std::sqrt(1.0 - beta2);
    const double dot = unit[0] * beta[0] + unit[1] * beta[1] + unit[2] * beta[2];
    const double factor1 = 1.0 + dot / (1.0 + gamma);
    const double factor2 = gamma * (1.0 + dot);
    Vec3 apparent = {
        (unit[0] + factor1 * beta[0]) / factor2,
        (unit[1] + factor1 * beta[1]) / factor2,
        (unit[2] + factor1 * beta[2]) / factor2,
    };
    return apparent * (distance / apparent.norm());
}

inline Vec3 apply_iau2006_frame_bias(const Vec3& icrf) noexcept {
    constexpr double d_alpha = (-14.6 / 1000.0) * ARCSEC2RAD;
    constexpr double xi0 = (-16.6170 / 1000.0) * ARCSEC2RAD;
    constexpr double eta0 = (-6.8192 / 1000.0) * ARCSEC2RAD;
    return {
        icrf[0] - eta0 * icrf[1] + xi0 * icrf[2],
        eta0 * icrf[0] + icrf[1] - d_alpha * icrf[2],
        -xi0 * icrf[0] + d_alpha * icrf[1] + icrf[2],
    };
}

/**
 * @brief Arcus Visionis calculation based on Ptolemy/Schoch table.
 * 
 * Scaled for non-standard limiting magnitude and extinction.
 */
inline double arcus_visionis(double mag, double limiting_mag, double extinction_k) {
    double base;
    if (mag <= -4.0)      base = 5.0;
    else if (mag <= -2.0) base = 6.5;
    else if (mag <= -1.0) base = 7.5;
    else if (mag <= 0.0)  base = 9.0;
    else if (mag <= 1.0)  base = 10.0;
    else if (mag <= 2.0)  base = 11.0;
    else if (mag <= 3.0)  base = 12.0;
    else if (mag <= 4.0)  base = 13.0;
    else                  base = 14.5;

    // Adjust for limiting magnitude (observer acuity) and extinction
    base += (6.5 - limiting_mag) * 0.8;
    base += (extinction_k - 0.25) * 4.0;
    return std::max(3.0, base);
}

/**
 * @brief THEOREM: Target Topocentric Altitude.
 * 
 * Computes the topocentric altitude of a target relative to an observer.
 * When earth_eval is provided, applies annual aberration using Earth's
 * barycentric velocity (IAU SOFA relativistic formula).
 */
inline double target_topocentric_altitude(
    const IEvaluator& target_eval,
    double jd_ut,
    double lat_deg,
    double lon_deg,
    double pressure_mbar = 1013.25,
    double temperature_c = 10.0,
    bool use_refraction = true,
    double delta_t = 64.184,
    const IEvaluator* earth_eval = nullptr
) {
    double jd_tt = jd_ut + (delta_t / 86400.0);

    // 1. Get geocentric position of target in ICRS
    double r_geo[6];
    target_eval.evaluate(jd_tt, r_geo);
    Vec3 target_icrf = {r_geo[0], r_geo[1], r_geo[2]};

    // 1b. Apparent observer correction for solar/planetary targets.
    if (earth_eval) {
        target_icrf = apply_iau2006_frame_bias(
            apply_annual_aberration(target_icrf, *earth_eval, jd_tt)
        );
    }

    // 2. Precess and Nutate target from ICRS to True Equatorial Frame of Date
    Mat3 prec = precession_matrix(jd_tt);
    double eps = mean_obliquity_p03(jd_tt) * DEG2RAD;
    const NutationResult nut = nutation_2000r06(jd_tt);
    Mat3 nut_mat = nutation_matrix(eps, nut.longitude, nut.obliquity);
    
    // Combined rotation: True = Nut * Prec * ICRS
    Mat3 rot = Mat3::mul(nut_mat, prec);
    Vec3 target_true = Mat3::mul(rot, target_icrf);

    // 3. Compute observer position in True Equatorial Frame
    // Use GAST (Apparent Sidereal Time)
    const double gast_deg = apparent_sidereal_time(
        jd_ut,
        nut.longitude * RAD2DEG,
        (eps + nut.obliquity) * RAD2DEG
    );
    double lst_rad = deg_to_rad(gast_deg + lon_deg);
    
    constexpr double f  = 1.0 / 298.257223563;
    constexpr double a  = 6378.137;
    constexpr double e2 = 1.0 - (1.0 - f) * (1.0 - f);

    double lat_r = deg_to_rad(lat_deg);
    double sin_lat = std::sin(lat_r);
    double cos_lat = std::cos(lat_r);
    double N = a / std::sqrt(1.0 - e2 * sin_lat * sin_lat);
    
    double obs_x = (N * cos_lat * std::cos(lst_rad)) / KM_PER_AU;
    double obs_y = (N * cos_lat * std::sin(lst_rad)) / KM_PER_AU;
    double obs_z = ((1.0 - e2) * N * sin_lat) / KM_PER_AU;

    // 4. Topocentric relative vector (both in TRUE EQ OF DATE, in AU)
    Vec3 rel_topo = {
        (target_true[0] / KM_PER_AU) - obs_x,
        (target_true[1] / KM_PER_AU) - obs_y,
        (target_true[2] / KM_PER_AU) - obs_z
    };
    double dist = rel_topo.norm();
    
    // 5. Transform to Alt/Az using spherical trig
    double dec_rad = std::asin(clamp(rel_topo[2] / dist, -1.0, 1.0));
    double ra_rad = std::atan2(rel_topo[1], rel_topo[0]);
    double ha_rad = lst_rad - ra_rad;
    
    double sin_alt = sin_lat * std::sin(dec_rad) + cos_lat * std::cos(dec_rad) * std::cos(ha_rad);
    double alt_deg = rad_to_deg(std::asin(clamp(sin_alt, -1.0, 1.0)));

    // 6. Apply Refraction
    if (use_refraction && alt_deg > -5.0) {
        // Saemundsson's formula for refraction
        double alt_eff = std::max(alt_deg, -5.0);
        double refr = 1.02 / std::tan(deg_to_rad(alt_eff + 10.3 / (alt_eff + 5.11))) / 60.0;
        
        // Pressure and Temperature correction
        refr *= (pressure_mbar / 1010.0) * (283.0 / (273.0 + temperature_c));
        alt_deg += refr;
    }

    return alt_deg;
}


/**
 * @brief THEOREM: Sun at Altitude Solver.
 * 
 * Finds the JD within a half-day window where the Sun reaches a target altitude.
 */
inline std::optional<double> find_sun_at_alt(
    const IEvaluator& sun_eval,
    double jd_midnight,
    double lat_deg,
    double lon_deg,
    double target_alt,
    bool morning,
    double delta_t = 64.184,
    const IEvaluator* earth_eval = nullptr
) {
    double t0 = morning ? jd_midnight : jd_midnight + 0.5;
    double t1 = t0 + 0.5;

    auto get_alt = [&](double jd) {
        return target_topocentric_altitude(sun_eval, jd, lat_deg, lon_deg, 1013.25, 10.0, false, delta_t, earth_eval);
    };

    double a0 = get_alt(t0);
    double a1 = get_alt(t1);

    if (morning) {
        // Morning: Sun rises from a0 to a1
        if (!(a0 <= target_alt && target_alt <= a1)) return std::nullopt;
    } else {
        // Evening: Sun sets from a0 to a1
        if (!(a1 <= target_alt && target_alt <= a0)) return std::nullopt;
    }

    auto f = [&](double jd) {
        return get_alt(jd) - target_alt;
    };

    try {
        return brent_root(f, t0, t1, 1e-10); // 1e-10 days ~ 8.6 microseconds
    } catch (...) {
        return std::nullopt;
    }
}


/**
 * @brief THEOREM: Heliacal Event Result Vessel.
 */
struct HeliacalEvent {
    std::string event_kind; // "heliacal_rising" or "heliacal_setting"
    double jd_ut = 0.0;
    bool is_found = false;
    double arcus_visionis = 0.0;
    double elongation = 0.0;
    double star_altitude = 0.0;
    int day_offset = 0;
};

/**
 * @brief Internal: Ecliptic longitude from ICRF vector.
 * Uses mean obliquity (P03) and Vondrak precession.
 */
inline double _true_ecliptic_longitude(
    const Vec3& icrf_xyz,
    double jd_tt,
    const NutationResult& nut
) {
    Mat3 prec = precession_matrix(jd_tt);
    double eps0 = mean_obliquity_p03(jd_tt) * DEG2RAD;
    Mat3 nut_mat = nutation_matrix(eps0, nut.longitude, nut.obliquity);
    
    Mat3 rot = Mat3::mul(nut_mat, prec);
    Vec3 true_equ = Mat3::mul(rot, icrf_xyz);
    
    // Convert true equatorial to true ecliptic of date
    double eps_true = eps0 + nut.obliquity;
    double ce = std::cos(eps_true);
    double se = std::sin(eps_true);
    
    double xe = true_equ[0];
    double ye = true_equ[1] * ce + true_equ[2] * se;
    
    return std::atan2(ye, xe) * RAD2DEG;
}

/**
 * @brief THEOREM: Heliacal Signed Elongation (Native).
 */
inline double heliacal_signed_elongation(
    const IEvaluator& star_eval,
    const IEvaluator& sun_eval,
    double jd_ut,
    double delta_t = 64.184,
    const IEvaluator* earth_eval = nullptr,
    NutationEpochCache* nutation_cache = nullptr
) {
    double jd_tt = jd_ut + (delta_t / 86400.0);
    double res_star[6], res_sun[6];
    star_eval.evaluate(jd_tt, res_star);
    sun_eval.evaluate(jd_tt, res_sun);
    
    Vec3 star_xyz = {res_star[0], res_star[1], res_star[2]};
    Vec3 sun_xyz = {res_sun[0], res_sun[1], res_sun[2]};
    if (earth_eval) {
        sun_xyz = apply_iau2006_frame_bias(
            apply_annual_aberration(sun_xyz, *earth_eval, jd_tt)
        );
    }
    
    const NutationResult nut = nutation_cache
        ? nutation_cache->evaluate(jd_tt)
        : nutation_2000r06(jd_tt);
    double star_lon = _true_ecliptic_longitude(star_xyz, jd_tt, nut);
    double sun_lon = _true_ecliptic_longitude(sun_xyz, jd_tt, nut);
    
    return normalize_deg_180(star_lon - sun_lon);
}

/**
 * @brief THEOREM: Heliacal Rising Search Engine.
 */
inline HeliacalEvent search_heliacal_rising(
    const IEvaluator& star_eval,
    const IEvaluator& sun_eval,
    double jd_start,
    double lat, double lon,
    double arcus_visionis_val,
    int search_days,
    double delta_t = 64.184,
    const IEvaluator* earth_eval = nullptr,
    double delta_t_rate_seconds_per_day = 0.0,
    NutationEpochCache* nutation_cache = nullptr
) {
    if (!std::isfinite(jd_start)) throw std::invalid_argument("jd_start must be finite");
    if (!std::isfinite(lat) || lat < -90.0 || lat > 90.0) {
        throw std::invalid_argument("latitude must be finite and in [-90, 90]");
    }
    if (!std::isfinite(lon) || lon < -180.0 || lon > 180.0) {
        throw std::invalid_argument("longitude must be finite and in [-180, 180]");
    }
    if (!std::isfinite(arcus_visionis_val) || arcus_visionis_val <= 0.0) {
        throw std::invalid_argument("arcus_visionis must be positive and finite");
    }
    if (search_days <= 0) throw std::invalid_argument("search_days must be positive");

    double jd_mid0 = std::floor(jd_start + 0.5) - 0.5;
    
    for (int day = 0; day < search_days; ++day) {
        double jd_midnight = jd_mid0 + day;
        
        // 1. Check signed elongation at Noon (approx middle of day)
        const double day_delta_t = delta_t
            + delta_t_rate_seconds_per_day * (jd_midnight + 0.5 - jd_start);
        double se = heliacal_signed_elongation(
            star_eval, sun_eval, jd_midnight + 0.5, day_delta_t, earth_eval,
            nutation_cache
        );
        if (se >= 0.0) continue;
        
        // 2. Find twilight JD when Sun is at -arcus_visionis (with aberration)
        auto twilight_jd = find_sun_at_alt(sun_eval, jd_midnight, lat, lon, -arcus_visionis_val, true, day_delta_t, earth_eval);
        if (!twilight_jd) continue;
        if (*twilight_jd < jd_start) continue;
        
        // 3. Check star altitude at twilight
        // star_alt must be geometric > -0.5667 (apparent horizon)
        double star_alt = target_topocentric_altitude(star_eval, *twilight_jd, lat, lon, 1013.25, 10.0, false, day_delta_t);
        
        if (star_alt > -0.5667) {
            HeliacalEvent ev;
            ev.event_kind = "heliacal_rising";
            ev.jd_ut = *twilight_jd;
            ev.is_found = true;
            ev.arcus_visionis = arcus_visionis_val;
            ev.elongation = se;
            ev.star_altitude = star_alt;
            ev.day_offset = day;
            return ev;
        }
    }
    
    HeliacalEvent nf;
    nf.event_kind = "heliacal_rising";
    nf.is_found = false;
    return nf;
}

/**
 * @brief THEOREM: Heliacal Setting Search Engine.
 */
inline HeliacalEvent search_heliacal_setting(
    const IEvaluator& star_eval,
    const IEvaluator& sun_eval,
    double jd_start,
    double lat, double lon,
    double arcus_visionis_val,
    int search_days,
    double delta_t = 64.184,
    const IEvaluator* earth_eval = nullptr,
    double setting_elongation_threshold = 12.0,
    double setting_visibility_factor = 0.5,
    double delta_t_rate_seconds_per_day = 0.0,
    NutationEpochCache* nutation_cache = nullptr
) {
    if (!std::isfinite(jd_start)) throw std::invalid_argument("jd_start must be finite");
    if (!std::isfinite(lat) || lat < -90.0 || lat > 90.0) {
        throw std::invalid_argument("latitude must be finite and in [-90, 90]");
    }
    if (!std::isfinite(lon) || lon < -180.0 || lon > 180.0) {
        throw std::invalid_argument("longitude must be finite and in [-180, 180]");
    }
    if (!std::isfinite(arcus_visionis_val) || arcus_visionis_val <= 0.0) {
        throw std::invalid_argument("arcus_visionis must be positive and finite");
    }
    if (search_days <= 0) throw std::invalid_argument("search_days must be positive");
    if (!std::isfinite(setting_elongation_threshold) || setting_elongation_threshold <= 0.0) {
        throw std::invalid_argument("setting_elongation_threshold must be positive and finite");
    }
    if (
        !std::isfinite(setting_visibility_factor)
        || setting_visibility_factor <= 0.0
        || setting_visibility_factor > 1.0
    ) {
        throw std::invalid_argument("setting_visibility_factor must be in (0, 1]");
    }

    double jd_mid0 = std::floor(jd_start + 0.5) - 0.5;
    std::optional<HeliacalEvent> last_visible;
    
    for (int day = 0; day < search_days; ++day) {
        double jd_midnight = jd_mid0 + day;
        const double day_delta_t = delta_t
            + delta_t_rate_seconds_per_day * (jd_midnight + 0.5 - jd_start);
        double se = heliacal_signed_elongation(
            star_eval, sun_eval, jd_midnight + 0.5, day_delta_t, earth_eval,
            nutation_cache
        );
        const double abs_se = std::abs(se);
        
        if (se < 0.0 && abs_se >= setting_elongation_threshold) {
            auto twilight_jd = find_sun_at_alt(sun_eval, jd_midnight, lat, lon, -arcus_visionis_val, true, day_delta_t, earth_eval);
            if (twilight_jd) {
                if (*twilight_jd < jd_start) continue;
                double star_alt = target_topocentric_altitude(star_eval, *twilight_jd, lat, lon, 1013.25, 10.0, false, day_delta_t);
                if (star_alt > -0.5667) {
                    HeliacalEvent ev;
                    ev.event_kind = "heliacal_setting";
                    ev.jd_ut = *twilight_jd;
                    ev.is_found = true;
                    ev.arcus_visionis = arcus_visionis_val;
                    ev.elongation = se;
                    ev.star_altitude = star_alt;
                    ev.day_offset = day;
                    last_visible = ev;
                    continue;
                }
            }
        } else if (
            last_visible
            && abs_se < setting_elongation_threshold * setting_visibility_factor
        ) {
            return *last_visible;
        }
    }
    
    if (last_visible) return *last_visible;
    
    HeliacalEvent nf;
    nf.event_kind = "heliacal_setting";
    nf.is_found = false;
    return nf;
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_VISIBILITY_HPP
