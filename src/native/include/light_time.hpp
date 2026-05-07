#ifndef MOIRA_NATIVE_LIGHT_TIME_HPP
#define MOIRA_NATIVE_LIGHT_TIME_HPP

#include "geometry.hpp"
#include "constants.hpp"
#include <functional>

namespace moira {
namespace native {

/**
 * @brief THEOREM: Light-time correction (Geometric to Apparent).
 * Iteratively solves for tau such that:
 * tau = |r_target(t - tau) - r_observer(t)| / c
 */
inline double solve_light_time(
    std::function<Vec3(double)> target_ephemeris,
    const Vec3& observer_pos,
    double t_obs,
    double initial_tau = 0.0,
    double tol = 1e-12,
    int max_iter = 10
) {
    const double c_inv = 1.0 / C_AU_PER_DAY;
    double tau = initial_tau;
    
    for (int i = 0; i < max_iter; ++i) {
        Vec3 r_target = target_ephemeris(t_obs - tau);
        double dist = Vec3::sub(r_target, observer_pos).norm();
        double next_tau = dist * c_inv;
        
        if (std::abs(next_tau - tau) < tol) return next_tau;
        tau = next_tau;
    }
    return tau;
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_LIGHT_TIME_HPP
