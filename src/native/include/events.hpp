#ifndef MOIRA_NATIVE_EVENTS_HPP
#define MOIRA_NATIVE_EVENTS_HPP

#include "evaluators.hpp"
#include "solvers.hpp"
#include "coordinates.hpp"
#include <vector>
#include <string>

namespace moira {
namespace native {

struct Event {
    std::string type;
    double t_mid;
    double t_start;
    double t_end;
    double value;
    std::string description;
};

/**
 * @brief THEOREM: Planetary Station Discovery.
 * Finds all points in [a, b] where the planetary velocity in longitude is zero.
 */
inline std::vector<double> find_stations(
    const IEvaluator& target,
    const IEvaluator& observer,
    double a, double b, double dt = 0.5
) {
    auto f = [&](double jd) {
        double r_full[6], ro_full[6];
        target.evaluate(jd, r_full);
        observer.evaluate(jd, ro_full);
        
        Vec3 rel_pos = {r_full[0] - ro_full[0], r_full[1] - ro_full[1], r_full[2] - ro_full[2]};
        Vec3 rel_vel = {r_full[3] - ro_full[3], r_full[4] - ro_full[4], r_full[5] - ro_full[5]};
        
        double lon, lat, dist, dlon, dlat, ddist;
        vec3_to_lonlat_with_rates(rel_pos, rel_vel, lon, lat, dist, dlon, dlat, ddist);
        return dlon;
    };
    
    return find_roots(f, a, b, dt);
}

/**
 * @brief THEOREM: Zodiacal Ingress Discovery.
 * Finds all points in [a, b] where the planet crosses a 30-degree boundary.
 */
inline std::vector<double> find_ingresses(
    const IEvaluator& target,
    const IEvaluator& observer,
    double a, double b, double dt = 0.5
) {
    auto f = [&](double jd) {
        double r_full[6], ro_full[6];
        target.evaluate(jd, r_full);
        observer.evaluate(jd, ro_full);
        
        Vec3 rel_pos = {r_full[0] - ro_full[0], r_full[1] - ro_full[1], r_full[2] - ro_full[2]};
        
        auto lonlat = vec3_to_lonlat(rel_pos);
        double lon = std::get<0>(lonlat);
        
        // Return (lon % 30) centered at 0
        double val = std::fmod(lon, 30.0);
        if (val > 15.0) val -= 30.0;
        if (val <= -15.0) val += 30.0;
        return val;
    };
    
    return find_roots(f, a, b, dt);
}

struct OccultationEvent {
    double t_mid;
    double separation_min;
    double t_start; 
    double t_end;   
    bool is_total;
};

/**
 * @brief THEOREM: Occultation/Eclipse Discovery.
 * Finds all occultations of target2 by target1 as seen from observer.
 */
inline std::vector<OccultationEvent> find_occultations(
    const IEvaluator& target1, double r1_km,
    const IEvaluator& target2, double r2_km,
    const IEvaluator& observer,
    double a, double b, double dt = 0.5
) {
    auto f_sep = [&](double jd) {
        return angular_separation(target1, target2, observer, jd);
    };
    
    // 1. Find all local minima of separation
    auto minima = find_extrema(f_sep, a, b, dt);
    std::vector<OccultationEvent> events;
    
    for (double t_mid : minima) {
        double sep_min = f_sep(t_mid);
        
        // Calculate apparent radii at t_mid
        double r1_full[6], r2_full[6], ro_full[6];
        target1.evaluate(t_mid, r1_full);
        target2.evaluate(t_mid, r2_full);
        observer.evaluate(t_mid, ro_full);
        
        double d1 = Vec3({r1_full[0]-ro_full[0], r1_full[1]-ro_full[1], r1_full[2]-ro_full[2]}).norm();
        double d2 = Vec3({r2_full[0]-ro_full[0], r2_full[1]-ro_full[1], r2_full[2]-ro_full[2]}).norm();
        
        double app_r1 = rad_to_deg(std::asin(clamp(r1_km / d1, 0.0, 1.0)));
        double app_r2 = rad_to_deg(std::asin(clamp(r2_km / d2, 0.0, 1.0)));
        
        if (sep_min < (app_r1 + app_r2)) {
            OccultationEvent ev;
            ev.t_mid = t_mid;
            ev.separation_min = sep_min;
            ev.is_total = sep_min < std::abs(app_r1 - app_r2);
            
            // Solve for contacts C1/C4: sep(t) = app_r1 + app_r2
            auto f_contact = [&](double jd) {
                return f_sep(jd) - (app_r1 + app_r2);
            };
            
            // Refine contacts around t_mid using a smaller window if needed
            double win = std::min(0.1, dt);
            try {
                // Ingress
                if (f_contact(t_mid - win) * f_contact(t_mid) < 0) {
                    ev.t_start = brent_root(f_contact, t_mid - win, t_mid, 1e-12);
                } else {
                    ev.t_start = t_mid; // Grazing or sub-window
                }
                
                // Egress
                if (f_contact(t_mid) * f_contact(t_mid + win) < 0) {
                    ev.t_end = brent_root(f_contact, t_mid, t_mid + win, 1e-12);
                } else {
                    ev.t_end = t_mid;
                }
            } catch (...) {
                ev.t_start = ev.t_end = t_mid;
            }
            
            events.push_back(ev);
        }
    }
    
    return events;
}

/**
 * @brief THEOREM: Discover Solar Eclipses (Geocentric or Topocentric).
 * Finds local minima in Sun-Moon separation and classifies them as eclipses if separation < radii sum.
 */
inline std::vector<Event> find_solar_eclipses(
    std::shared_ptr<IEvaluator> sun,
    std::shared_ptr<IEvaluator> moon,
    double jd_start, double jd_end,
    double sun_radius_km, double moon_radius_km,
    double dt = 15.0 // Scan once per half-lunation
) {
    auto f_ra_diff = [&](double jd) {
        double r_s[6], r_m[6];
        sun->evaluate(jd, r_s);
        moon->evaluate(jd, r_m);
        double ra_s = std::get<0>(vec3_to_radec(Vec3({r_s[0], r_s[1], r_s[2]})));
        double ra_m = std::get<0>(vec3_to_radec(Vec3({r_m[0], r_m[1], r_m[2]})));
        double diff = ra_s - ra_m;
        while (diff > 180.0) diff -= 360.0;
        while (diff <= -180.0) diff += 360.0;
        return diff;
    };

    auto f_sep = [&](double jd) {
        double r_s[6], r_m[6];
        sun->evaluate(jd, r_s);
        moon->evaluate(jd, r_m);
        return angular_separation(
            Vec3({r_s[0], r_s[1], r_s[2]}),
            Vec3({r_m[0], r_m[1], r_m[2]})
        );
    };

    auto conjunctions = find_roots(f_ra_diff, jd_start, jd_end, dt);
    std::vector<Event> events;

    for (auto t_conj : conjunctions) {
        // Refine to minimum separation near conjunction (+/- 1 day)
        double t_mid;
        try {
            t_mid = brent_minimize(f_sep, t_conj - 1.0, t_conj + 1.0, 1e-10);
        } catch (...) {
            t_mid = t_conj;
        }

        double sep = f_sep(t_mid);
        
        double r_s[6], r_m[6];
        sun->evaluate(t_mid, r_s);
        moon->evaluate(t_mid, r_m);
        
        double dist_s = Vec3({r_s[0], r_s[1], r_s[2]}).norm();
        double dist_m = Vec3({r_m[0], r_m[1], r_m[2]}).norm();
        
        double app_r_s = rad_to_deg(std::asin(clamp(sun_radius_km / dist_s, -1.0, 1.0)));
        double app_r_m = rad_to_deg(std::asin(clamp(moon_radius_km / dist_m, -1.0, 1.0)));

        if (sep < (app_r_s + app_r_m)) {
            Event ev;
            ev.type = "Solar Eclipse";
            ev.t_mid = t_mid;
            ev.value = sep;

            // Refine contacts
            auto f_contact = [&](double jd) {
                double rs[6], rm[6];
                sun->evaluate(jd, rs);
                moon->evaluate(jd, rm);
                double s = angular_separation(Vec3({rs[0], rs[1], rs[2]}), Vec3({rm[0], rm[1], rm[2]}));
                
                double ds = Vec3({rs[0], rs[1], rs[2]}).norm();
                double dm = Vec3({rm[0], rm[1], rm[2]}).norm();
                double ars = rad_to_deg(std::asin(clamp(sun_radius_km / ds, -1.0, 1.0)));
                double arm = rad_to_deg(std::asin(clamp(moon_radius_km / dm, -1.0, 1.0)));
                
                return s - (ars + arm);
            };

            double win = 0.1; // 2.4 hours
            try {
                if (f_contact(t_mid - win) * f_contact(t_mid) < 0) {
                    ev.t_start = brent_root(f_contact, t_mid - win, t_mid, 1e-12);
                } else {
                    ev.t_start = t_mid;
                }
                
                if (f_contact(t_mid) * f_contact(t_mid + win) < 0) {
                    ev.t_end = brent_root(f_contact, t_mid, t_mid + win, 1e-12);
                } else {
                    ev.t_end = t_mid;
                }
            } catch (...) {
                ev.t_start = ev.t_end = t_mid;
            }

            events.push_back(ev);
        }
    }
    return events;
}

/**
 * @brief THEOREM: Discover Lunar Eclipses.
 * Finds local minima in Moon-Shadow separation.
 */
inline std::vector<Event> find_lunar_eclipses(
    std::shared_ptr<IEvaluator> sun,
    std::shared_ptr<IEvaluator> moon,
    double jd_start, double jd_end,
    double sun_radius_km, double moon_radius_km, double earth_radius_km,
    double dt = 15.0 
) {
    auto f_ra_opp = [&](double jd) {
        double r_s[6], r_m[6];
        sun->evaluate(jd, r_s);
        moon->evaluate(jd, r_m);
        double ra_s = std::get<0>(vec3_to_radec(Vec3({r_s[0], r_s[1], r_s[2]})));
        double ra_m = std::get<0>(vec3_to_radec(Vec3({r_m[0], r_m[1], r_m[2]})));
        double diff = ra_s - ra_m - 180.0;
        while (diff > 180.0) diff -= 360.0;
        while (diff <= -180.0) diff += 360.0;
        return diff;
    };

    auto f_sep = [&](double jd) {
        double r_s[6], r_m[6];
        sun->evaluate(jd, r_s);
        moon->evaluate(jd, r_m);
        Vec3 shadow_axis = Vec3({-r_s[0], -r_s[1], -r_s[2]});
        return angular_separation(shadow_axis, Vec3({r_m[0], r_m[1], r_m[2]}));
    };

    auto oppositions = find_roots(f_ra_opp, jd_start, jd_end, dt);
    std::vector<Event> events;

    for (auto t_opp : oppositions) {
        // Refine to minimum separation near opposition (+/- 1 day)
        double t_mid;
        try {
            t_mid = brent_minimize(f_sep, t_opp - 1.0, t_opp + 1.0, 1e-10);
        } catch (...) {
            t_mid = t_opp;
        }

        double sep = f_sep(t_mid);
        
        double r_s[6], r_m[6];
        sun->evaluate(t_mid, r_s);
        moon->evaluate(t_mid, r_m);
        
        double dist_s = Vec3({r_s[0], r_s[1], r_s[2]}).norm();
        double dist_m = Vec3({r_m[0], r_m[1], r_m[2]}).norm();
        
        // Danjon-style Shadow Geometry
        double pm = rad_to_deg(std::asin(clamp(earth_radius_km / dist_m, -1.0, 1.0)));
        double ss = rad_to_deg(std::asin(clamp(sun_radius_km / dist_s, -1.0, 1.0)));
        double ps = rad_to_deg(std::asin(clamp(earth_radius_km / dist_s, -1.0, 1.0)));
        
        double penumbra_r = 1.01 * pm + ss + ps;
        double moon_r = rad_to_deg(std::asin(clamp(moon_radius_km / dist_m, -1.0, 1.0)));

        if (sep < (penumbra_r + moon_r)) {
            Event ev;
            ev.type = "Lunar Eclipse";
            ev.t_mid = t_mid;
            ev.value = sep;
            
            // Refine contacts (penumbral ingress/egress)
            auto f_contact = [&](double jd) {
                double rs[6], rm[6];
                sun->evaluate(jd, rs);
                moon->evaluate(jd, rm);
                Vec3 sa = Vec3({-rs[0], -rs[1], -rs[2]});
                double s = angular_separation(sa, Vec3({rm[0], rm[1], rm[2]}));
                
                double ds = Vec3({rs[0], rs[1], rs[2]}).norm();
                double dm = Vec3({rm[0], rm[1], rm[2]}).norm();
                
                double p_m = rad_to_deg(std::asin(clamp(earth_radius_km / dm, -1.0, 1.0)));
                double s_s = rad_to_deg(std::asin(clamp(sun_radius_km / ds, -1.0, 1.0)));
                double p_s = rad_to_deg(std::asin(clamp(earth_radius_km / ds, -1.0, 1.0)));
                double pr = 1.01 * p_m + s_s + p_s;
                double mr = rad_to_deg(std::asin(clamp(moon_radius_km / dm, -1.0, 1.0)));
                
                return s - (pr + mr);
            };

            double win = 0.2; // ~5 hours
            try {
                if (f_contact(t_mid - win) * f_contact(t_mid) < 0) {
                    ev.t_start = brent_root(f_contact, t_mid - win, t_mid, 1e-12);
                } else {
                    ev.t_start = t_mid;
                }
                
                if (f_contact(t_mid) * f_contact(t_mid + win) < 0) {
                    ev.t_end = brent_root(f_contact, t_mid, t_mid + win, 1e-12);
                } else {
                    ev.t_end = t_mid;
                }
            } catch (...) {
                ev.t_start = ev.t_end = t_mid;
            }

            events.push_back(ev);
        }
    }
    return events;
}


} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_EVENTS_HPP
