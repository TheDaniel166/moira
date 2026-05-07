#ifndef MOIRA_NATIVE_SEPARATION_HPP
#define MOIRA_NATIVE_SEPARATION_HPP

#include "evaluators.hpp"
#include "coordinates.hpp"
#include <cmath>

namespace moira {
namespace native {

inline double angular_separation(const Vec3& v1, const Vec3& v2) {
    return Vec3::angle_between(v1, v2) * RAD2DEG;
}

/**
 * @brief THEOREM: Geocentric Angular Separation.
 * Returns the angle (degrees) between two bodies as seen from an observer.
 */
inline double angular_separation(const IEvaluator& target1, const IEvaluator& target2, const IEvaluator& observer, double jd) {
    double r1_full[6], r2_full[6], ro_full[6];
    target1.evaluate(jd, r1_full);
    target2.evaluate(jd, r2_full);
    observer.evaluate(jd, ro_full);

    Vec3 v1 = {r1_full[0] - ro_full[0], r1_full[1] - ro_full[1], r1_full[2] - ro_full[2]};
    Vec3 v2 = {r2_full[0] - ro_full[0], r2_full[1] - ro_full[1], r2_full[2] - ro_full[2]};

    return angular_separation(v1, v2);
}

/**
 * @brief THEOREM: Longitude Difference.
 * Returns (lon1 - lon2) normalized to [-180, 180].
 */
inline double longitude_difference(const IEvaluator& target1, const IEvaluator& target2, const IEvaluator& observer, double jd) {
    double r1_full[6], r2_full[6], ro_full[6];
    target1.evaluate(jd, r1_full);
    target2.evaluate(jd, r2_full);
    observer.evaluate(jd, ro_full);

    Vec3 v1 = {r1_full[0] - ro_full[0], r1_full[1] - ro_full[1], r1_full[2] - ro_full[2]};
    Vec3 v2 = {r2_full[0] - ro_full[0], r2_full[1] - ro_full[1], r2_full[2] - ro_full[2]};

    auto radec1 = vec3_to_radec(v1);
    auto radec2 = vec3_to_radec(v2);

    double diff = std::get<0>(radec1) - std::get<0>(radec2);
    while (diff > 180.0) diff -= 360.0;
    while (diff <= -180.0) diff += 360.0;
    return diff;
}

/**
 * @brief THEOREM: Angular Separation with Rates.
 * Returns the separation (degrees) and its rate of change (deg/day).
 */
inline std::pair<double, double> angular_separation_with_rates(
    const IEvaluator& target1, 
    const IEvaluator& target2, 
    const IEvaluator& observer, 
    double jd
) {
    double r1_full[6], r2_full[6], ro_full[6];
    target1.evaluate(jd, r1_full);
    target2.evaluate(jd, r2_full);
    observer.evaluate(jd, ro_full);

    Vec3 p1 = {r1_full[0] - ro_full[0], r1_full[1] - ro_full[1], r1_full[2] - ro_full[2]};
    Vec3 p2 = {r2_full[0] - ro_full[0], r2_full[1] - ro_full[1], r2_full[2] - ro_full[2]};
    Vec3 v1 = {r1_full[3] - ro_full[3], r1_full[4] - ro_full[4], r1_full[5] - ro_full[5]};
    Vec3 v2 = {r2_full[3] - ro_full[3], r2_full[4] - ro_full[4], r2_full[5] - ro_full[5]};

    double r1 = p1.norm();
    double r2 = p2.norm();
    if (r1 == 0.0 || r2 == 0.0) return {0.0, 0.0};

    Vec3 u1 = p1.unit();
    Vec3 u2 = p2.unit();

    double cos_theta = clamp(u1.dot(u2), -1.0, 1.0);
    double theta = std::acos(cos_theta);

    // Rate: d/dt acos(u1 . u2) = -1/sqrt(1 - (u1.u2)^2) * d/dt(u1 . u2)
    // d/dt(u1 . u2) = u1' . u2 + u1 . u2'
    // u' = (v * (r.r) - r * (r.v)) / r^3
    Vec3 du1 = (v1 * (r1 * r1) - p1 * p1.dot(v1)) / (r1 * r1 * r1);
    Vec3 du2 = (v2 * (r2 * r2) - p2 * p2.dot(v2)) / (r2 * r2 * r2);

    double d_cos_theta = du1.dot(u2) + u1.dot(du2);

    double sin_theta = std::sqrt(std::max(0.0, 1.0 - cos_theta * cos_theta));

    double dtheta = 0.0;
    if (sin_theta > 1e-15) {
        dtheta = -d_cos_theta / sin_theta;
    }

    return {theta * RAD2DEG, dtheta * RAD2DEG};
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_SEPARATION_HPP
