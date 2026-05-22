#ifndef MOIRA_NATIVE_PLANETARY_EVALUATOR_HPP
#define MOIRA_NATIVE_PLANETARY_EVALUATOR_HPP

#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

#include "constants.hpp"
#include "coordinates.hpp"
#include "daf.hpp"
#include "geometry.hpp"
#include "math_utils.hpp"

namespace moira {
namespace native {

struct NativePlanetaryPayload {
    std::string name;
    double longitude = 0.0;
    double latitude = 0.0;
    double distance = 0.0;
    double speed = 0.0;
    bool retrograde = false;
};

class NativePlanetaryEvaluator {
public:
    using SegmentSpec = std::tuple<int32_t, int32_t, int32_t>;
    using SegmentSpecMap = std::unordered_map<std::string, std::vector<SegmentSpec>>;

    explicit NativePlanetaryEvaluator(std::shared_ptr<NativeSpkKernelHandle> handle)
        : handle_(std::move(handle)) {
        if (!handle_) {
            throw std::runtime_error("NativePlanetaryEvaluator requires a live NativeSpkKernelHandle");
        }
    }

    std::vector<NativePlanetaryPayload> evaluate_all_planets_apparent_geocentric_ecliptic(
        const std::vector<std::string>& bodies,
        const std::vector<SegmentSpec>& public_specs,
        const SegmentSpecMap& body_specs,
        double jd_tt,
        double obliquity_deg,
        const Mat3& rotation_matrix
    ) const {
        if (public_specs.size() != 14) {
            throw std::runtime_error("admitted planetary evaluator requires 14 public route specs");
        }

        std::vector<std::pair<Vec3, Vec3>> pair_states;
        pair_states.reserve(public_specs.size());
        for (const SegmentSpec& spec : public_specs) {
            pair_states.push_back(route_state({spec}, jd_tt));
        }

        const std::pair<Vec3, Vec3>& ssb_sun = pair_states[0];
        const std::pair<Vec3, Vec3>& ssb_emb = pair_states[1];
        const std::pair<Vec3, Vec3>& emb_earth = pair_states[2];
        const std::pair<Vec3, Vec3>& emb_moon = pair_states[3];

        const Vec3 earth_pos = Vec3::add(ssb_emb.first, emb_earth.first);
        const Vec3 earth_vel = Vec3::add(ssb_emb.second, emb_earth.second);

        std::unordered_map<std::string, std::pair<Vec3, Vec3>> bary_states;
        bary_states.reserve(10);
        bary_states.emplace("Sun", ssb_sun);
        bary_states.emplace("Moon", std::make_pair(
            Vec3::add(ssb_emb.first, emb_moon.first),
            Vec3::add(ssb_emb.second, emb_moon.second)
        ));
        bary_states.emplace("Mercury", std::make_pair(
            Vec3::add(pair_states[4].first, pair_states[5].first),
            Vec3::add(pair_states[4].second, pair_states[5].second)
        ));
        bary_states.emplace("Venus", std::make_pair(
            Vec3::add(pair_states[6].first, pair_states[7].first),
            Vec3::add(pair_states[6].second, pair_states[7].second)
        ));
        bary_states.emplace("Mars", pair_states[8]);
        bary_states.emplace("Jupiter", pair_states[9]);
        bary_states.emplace("Saturn", pair_states[10]);
        bary_states.emplace("Uranus", pair_states[11]);
        bary_states.emplace("Neptune", pair_states[12]);
        bary_states.emplace("Pluto", pair_states[13]);

        std::unordered_map<std::string, std::pair<Vec3, Vec3>> geo_states;
        geo_states.reserve(bary_states.size());
        for (const auto& entry : bary_states) {
            geo_states.emplace(
                entry.first,
                std::make_pair(
                    Vec3::sub(entry.second.first, earth_pos),
                    Vec3::sub(entry.second.second, earth_vel)
                )
            );
        }

        std::unordered_map<std::string, double> light_times;
        std::unordered_map<std::string, Vec3> geocentric_lt;
        light_times.reserve(bodies.size());
        geocentric_lt.reserve(bodies.size());
        for (const std::string& body : bodies) {
            const auto it = bary_states.find(body);
            if (it == bary_states.end()) {
                throw std::runtime_error("admitted evaluator received unsupported body: " + body);
            }
            const Vec3 xyz = Vec3::sub(it->second.first, earth_pos);
            light_times.emplace(body, xyz.norm() / C_KM_PER_DAY);
            geocentric_lt.emplace(body, xyz);
        }

        for (int iter = 0; iter < 3; ++iter) {
            bool converged = true;
            for (const std::string& body : bodies) {
                const auto specs_it = body_specs.find(body);
                if (specs_it == body_specs.end()) {
                    throw std::runtime_error("missing admitted route specs for body: " + body);
                }
                const Vec3 bary_lt = route_position(specs_it->second, jd_tt - light_times.at(body));
                const Vec3 xyz_lt = Vec3::sub(bary_lt, earth_pos);
                const double next_lt = xyz_lt.norm() / C_KM_PER_DAY;
                if (std::abs(next_lt - light_times.at(body)) >= 1e-14) {
                    converged = false;
                }
                light_times[body] = next_lt;
                geocentric_lt[body] = xyz_lt;
            }
            if (converged) {
                break;
            }
        }

        const Vec3 sun_geo = geo_states.at("Sun").first;
        const Vec3 jupiter_geo = geo_states.at("Jupiter").first;
        const Vec3 saturn_geo = geo_states.at("Saturn").first;

        std::vector<NativePlanetaryPayload> out;
        out.reserve(bodies.size());
        for (const std::string& body : bodies) {
            Vec3 xyz = geocentric_lt.at(body);
            if (body != "Sun" && body != "Moon") {
                std::vector<std::pair<Vec3, double>> deflectors;
                deflectors.reserve(3);
                deflectors.emplace_back(sun_geo, 2.95325008);
                if (body != "Jupiter") {
                    deflectors.emplace_back(jupiter_geo, 0.00282);
                }
                if (body != "Saturn") {
                    deflectors.emplace_back(saturn_geo, 0.000838);
                }
                xyz = apply_deflection(xyz, deflectors);
            }

            xyz = apply_aberration_velocity(xyz, earth_vel);
            xyz = apply_frame_bias(xyz);
            xyz = Mat3::mul(rotation_matrix, xyz);

            const auto [longitude, latitude, distance] = equatorial_vector_to_ecliptic(xyz, obliquity_deg);
            const auto& geo_state = geo_states.at(body);
            const double speed = longitude_rate(geo_state.first, geo_state.second, obliquity_deg);
            out.push_back(NativePlanetaryPayload{
                body,
                longitude,
                latitude,
                distance,
                speed,
                speed < 0.0,
            });
        }
        return out;
    }

private:
    std::pair<Vec3, Vec3> route_state(const std::vector<SegmentSpec>& specs, double jd) const {
        Vec3 position;
        Vec3 velocity;
        for (const SegmentSpec& spec : specs) {
            double pos[3];
            double vel[3];
            handle_->segment_position_and_velocity(
                std::get<0>(spec),
                std::get<1>(spec),
                std::get<2>(spec),
                jd,
                pos,
                vel
            );
            position = Vec3::add(position, Vec3(pos[0], pos[1], pos[2]));
            velocity = Vec3::add(velocity, Vec3(vel[0], vel[1], vel[2]));
        }
        return {position, velocity};
    }

    Vec3 route_position(const std::vector<SegmentSpec>& specs, double jd) const {
        Vec3 out;
        for (const SegmentSpec& spec : specs) {
            double position[3];
            handle_->segment_position(
                std::get<0>(spec),
                std::get<1>(spec),
                std::get<2>(spec),
                jd,
                position
            );
            out = Vec3::add(out, Vec3(position[0], position[1], position[2]));
        }
        return out;
    }

    static Vec3 apply_aberration_velocity(const Vec3& xyz, const Vec3& velocity_xyz_per_day) {
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

    static Vec3 apply_deflection(
        const Vec3& xyz_body,
        const std::vector<std::pair<Vec3, double>>& deflectors
    ) {
        const double dist_body = xyz_body.norm();
        if (dist_body < 1e-10) {
            return xyz_body;
        }

        double ux = xyz_body[0] / dist_body;
        double uy = xyz_body[1] / dist_body;
        double uz = xyz_body[2] / dist_body;

        for (const auto& deflector : deflectors) {
            const Vec3& xyz_defl = deflector.first;
            const double rs = deflector.second;
            const double dist_defl = xyz_defl.norm();
            if (dist_defl < 1e-10) {
                continue;
            }

            const double ex = xyz_defl[0] / dist_defl;
            const double ey = xyz_defl[1] / dist_defl;
            const double ez = xyz_defl[2] / dist_defl;
            const double cos_psi = ux * ex + uy * ey + uz * ez;
            if (cos_psi < -0.9999999) {
                continue;
            }

            const double g1 = rs / dist_defl;
            const double f2 = cos_psi / (1.0 + cos_psi);
            const double dx = g1 * (ex - f2 * ux);
            const double dy = g1 * (ey - f2 * uy);
            const double dz = g1 * (ez - f2 * uz);

            const double nx = ux + dx;
            const double ny = uy + dy;
            const double nz = uz + dz;
            const double mag = std::sqrt(nx * nx + ny * ny + nz * nz);
            ux = nx / mag;
            uy = ny / mag;
            uz = nz / mag;
        }

        return {ux * dist_body, uy * dist_body, uz * dist_body};
    }

    static Vec3 apply_frame_bias(const Vec3& xyz) {
        constexpr double dA_r = (-14.6 / 1000.0) * ARCSEC2RAD;
        constexpr double xi0_r = (-16.6170 / 1000.0) * ARCSEC2RAD;
        constexpr double de0_r = (-6.8192 / 1000.0) * ARCSEC2RAD;
        const double xb = xyz[0] - de0_r * xyz[1] + xi0_r * xyz[2];
        const double yb = de0_r * xyz[0] + xyz[1] - dA_r * xyz[2];
        const double zb = -xi0_r * xyz[0] + dA_r * xyz[1] + xyz[2];
        return {xb, yb, zb};
    }

    static std::tuple<double, double, double> equatorial_vector_to_ecliptic(
        const Vec3& xyz,
        double obliquity_deg
    ) {
        const double eps = deg_to_rad(obliquity_deg);
        const double cos_eps = std::cos(eps);
        const double sin_eps = std::sin(eps);

        const double xe = xyz[0];
        const double ye = xyz[1] * cos_eps + xyz[2] * sin_eps;
        const double ze = -xyz[1] * sin_eps + xyz[2] * cos_eps;

        const double distance = std::sqrt(xe * xe + ye * ye + ze * ze);
        if (distance == 0.0) {
            throw std::runtime_error("native planetary evaluator received a zero-magnitude equatorial vector");
        }

        const double longitude = normalize_deg_360(rad_to_deg(std::atan2(ye, xe)));
        const double latitude = rad_to_deg(safe_asin(ze / distance));
        return {longitude, latitude, distance};
    }

    static double longitude_rate(const Vec3& xyz, const Vec3& velocity, double obliquity_deg) {
        const double eps = deg_to_rad(obliquity_deg);
        const double cos_eps = std::cos(eps);
        const double sin_eps = std::sin(eps);

        const double xe = xyz[0];
        const double ye = xyz[1] * cos_eps + xyz[2] * sin_eps;
        const double vxe = velocity[0];
        const double vye = velocity[1] * cos_eps + velocity[2] * sin_eps;
        const double denom = xe * xe + ye * ye;
        if (denom <= 1e-18) {
            return 0.0;
        }
        return ((xe * vye - ye * vxe) / denom) * RAD2DEG;
    }

    std::shared_ptr<NativeSpkKernelHandle> handle_;
};

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_PLANETARY_EVALUATOR_HPP
