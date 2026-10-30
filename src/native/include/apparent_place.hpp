#pragma once

// Apparent-place corrections shared by the native planetary and fixed-star
// evaluators: gravitational light deflection (IAU SOFA / ERFA Ld pattern,
// mirroring moira.corrections.apply_deflection) and relativistic annual
// aberration (mirroring moira.corrections.apply_aberration). One
// implementation serves every native apparent place.

#include <cmath>
#include <utility>
#include <vector>

#include "constants.hpp"
#include "geometry.hpp"

namespace moira {
namespace native {

/**
 * @brief THEOREM: relativistic annual aberration of a geocentric vector.
 * Velocity is Earth's barycentric velocity in km/day; the length is kept.
 */
inline Vec3 apparent_aberration(const Vec3& xyz, const Vec3& velocity_xyz_per_day) {
    const double dist = xyz.norm();
    if (dist < 1e-10) {
        return xyz;
    }

    const double ux = xyz[0] / dist;
    const double uy = xyz[1] / dist;
    const double uz = xyz[2] / dist;
    const double bx = velocity_xyz_per_day[0] / C_KM_PER_DAY;
    const double by = velocity_xyz_per_day[1] / C_KM_PER_DAY;
    const double bz = velocity_xyz_per_day[2] / C_KM_PER_DAY;
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

/**
 * @brief THEOREM: sequential point-mass light deflection of a geocentric vector.
 * Each deflector is (geocentric position km, Schwarzschild radius km).
 */
inline Vec3 apparent_deflection(
    const Vec3& xyz_body,
    const std::vector<std::pair<Vec3, double>>& deflectors
) {
    const double dist_body = xyz_body.norm();
    if (dist_body < 1e-10) {
        return xyz_body;
    }

    double px = xyz_body[0] / dist_body;
    double py = xyz_body[1] / dist_body;
    double pz = xyz_body[2] / dist_body;

    for (const auto& deflector : deflectors) {
        const Vec3& xyz_defl = deflector.first;
        const double rs = deflector.second;
        const double dist_defl = xyz_defl.norm();
        if (dist_defl < 1e-10) {
            continue;
        }

        const double ex = -xyz_defl[0] / dist_defl;
        const double ey = -xyz_defl[1] / dist_defl;
        const double ez = -xyz_defl[2] / dist_defl;

        const double qx_full = (px * dist_body) - xyz_defl[0];
        const double qy_full = (py * dist_body) - xyz_defl[1];
        const double qz_full = (pz * dist_body) - xyz_defl[2];
        
        const double q_dist = std::sqrt(qx_full * qx_full + qy_full * qy_full + qz_full * qz_full);
        if (q_dist < 1e-10) {
            continue;
        }

        const double qx = qx_full / q_dist;
        const double qy = qy_full / q_dist;
        const double qz = qz_full / q_dist;

        const double qdot_e = qx * ex + qy * ey + qz * ez;
        double qdot_qpe = 1.0 + qdot_e;
        if (qdot_qpe < 1e-8) {
            qdot_qpe = 1e-8;
        }

        const double w = rs / (dist_defl * qdot_qpe);

        const double eq_x = ey * qz - ez * qy;
        const double eq_y = ez * qx - ex * qz;
        const double eq_z = ex * qy - ey * qx;

        const double peq_x = py * eq_z - pz * eq_y;
        const double peq_y = pz * eq_x - px * eq_z;
        const double peq_z = px * eq_y - py * eq_x;

        const double nx = px + w * peq_x;
        const double ny = py + w * peq_y;
        const double nz = pz + w * peq_z;
        
        const double mag = std::sqrt(nx * nx + ny * ny + nz * nz);
        px = nx / mag;
        py = ny / mag;
        pz = nz / mag;
    }

    return {px * dist_body, py * dist_body, pz * dist_body};
}

}  // namespace native
}  // namespace moira
