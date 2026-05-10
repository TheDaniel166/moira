#ifndef MOIRA_NATIVE_COORDINATES_HPP
#define MOIRA_NATIVE_COORDINATES_HPP

#include <cmath>
#include "geometry.hpp"
#include "math_utils.hpp"

namespace moira {
namespace native {

/**
 * @brief Convert RA/Dec (degrees) and distance to a Cartesian vector.
 */
inline Vec3 radec_to_vec3(double ra_deg, double dec_deg, double dist = 1.0) {
    double ra = deg_to_rad(ra_deg);
    double dec = deg_to_rad(dec_deg);
    double cos_dec = std::cos(dec);
    return Vec3({
        dist * cos_dec * std::cos(ra),
        dist * cos_dec * std::sin(ra),
        dist * std::sin(dec)
    });
}

/**
 * @brief Convert a Cartesian vector to RA/Dec (degrees) and distance.
 */
inline std::tuple<double, double, double> vec3_to_radec(const Vec3& v) {
    double x = v[0];
    double y = v[1];
    double z = v[2];
    double dist = v.norm();
    if (dist == 0.0) return {0.0, 0.0, 0.0};

    double ra = normalize_deg_360(rad_to_deg(std::atan2(y, x)));
    double dec = rad_to_deg(std::asin(clamp(z / dist, -1.0, 1.0)));
    return {ra, dec, dist};
}

/**
 * @brief Convert ecliptic longitude/latitude (degrees) and distance to a Cartesian vector.
 */
inline Vec3 lonlat_to_vec3(double lon_deg, double lat_deg, double dist = 1.0) {
    // Math is identical to radec_to_vec3
    return radec_to_vec3(lon_deg, lat_deg, dist);
}

/**
 * @brief Convert a Cartesian vector to ecliptic longitude/latitude (degrees) and distance.
 */
inline std::tuple<double, double, double> vec3_to_lonlat(const Vec3& v) {
    // Math is identical to vec3_to_radec
    return vec3_to_radec(v);
}

/**
 * @brief Convert a Cartesian vector to signed longitude/latitude (degrees) and distance.
 *
 * Longitude follows the SPICE reclat/atan2 convention in [-180, 180].
 */
inline std::tuple<double, double, double> vec3_to_lonlat_signed(const Vec3& v) {
    double x = v[0];
    double y = v[1];
    double z = v[2];
    double dist = v.norm();
    if (dist == 0.0) return {0.0, 0.0, 0.0};

    double lon = rad_to_deg(std::atan2(y, x));
    double lat = rad_to_deg(std::asin(clamp(z / dist, -1.0, 1.0)));
    return {lon, lat, dist};
}

/**
 * @brief Convert WGS-84 geodetic longitude/latitude/elevation to Cartesian coordinates.
 *
 * This is the admitted native replacement for the narrow SPICE georec usage in
 * the lunar-limb path. Output axes follow the standard body-fixed rectangular
 * convention: x toward lon=0, y toward lon=90E, z toward north pole.
 */
inline Vec3 geodetic_to_cartesian_wgs84(
    double lon_deg,
    double lat_deg,
    double elevation_m = 0.0
) {
    constexpr double f = 1.0 / 298.257223563;
    constexpr double a = EARTH_RADIUS_KM;

    const double lon = deg_to_rad(lon_deg);
    const double lat = deg_to_rad(lat_deg);
    const double h = elevation_m / 1000.0;

    const double cos_lat = std::cos(lat);
    const double sin_lat = std::sin(lat);
    const double e2 = 2.0 * f - f * f;
    const double n = a / std::sqrt(1.0 - e2 * sin_lat * sin_lat);

    return Vec3({
        (n + h) * cos_lat * std::cos(lon),
        (n + h) * cos_lat * std::sin(lon),
        ((1.0 - e2) * n + h) * sin_lat
    });
}

/**
 * @brief THEOREM: Cartesian State to Spherical with Rates.
 */
inline void vec3_to_lonlat_with_rates(
    const Vec3& pos, 
    const Vec3& vel,
    double& lon, double& lat, double& dist,
    double& dlon, double& dlat, double& ddist
) {
    double x = pos[0], y = pos[1], z = pos[2];
    double vx = vel[0], vy = vel[1], vz = vel[2];
    
    double rho2 = x * x + y * y;
    double r2 = rho2 + z * z;
    double r = std::sqrt(r2);
    dist = r;

    if (r == 0.0) {
        lon = lat = dist = dlon = dlat = ddist = 0.0;
        return;
    }

    lon = normalize_deg_360(rad_to_deg(std::atan2(y, x)));
    lat = rad_to_deg(std::asin(clamp(z / r, -1.0, 1.0)));

    ddist = (x * vx + y * vy + z * vz) / r;

    // Singularity guard for pole (rho=0)
    if (rho2 < 1e-25) {
        dlon = 0.0;
        dlat = 0.0;
    } else {
        dlon = rad_to_deg((x * vy - y * vx) / rho2);
        dlat = rad_to_deg((vz * rho2 - z * (x * vx + y * vy)) / (r2 * std::sqrt(rho2)));
    }
}

/**
 * @brief THEOREM: Ecliptic to Equatorial conversion.
 */
inline std::pair<double, double> ecliptic_to_equatorial(double lon_deg, double lat_deg, double obliquity_deg) {
    double eps = deg_to_rad(obliquity_deg);
    double lon = deg_to_rad(lon_deg);
    double lat = deg_to_rad(lat_deg);

    double sin_dec = std::sin(lat) * std::cos(eps) + std::cos(lat) * std::sin(eps) * std::sin(lon);
    double dec = rad_to_deg(std::asin(clamp(sin_dec, -1.0, 1.0)));

    double y = std::sin(lon) * std::cos(eps) - std::tan(lat) * std::sin(eps);
    double x = std::cos(lon);
    double ra = normalize_deg_360(rad_to_deg(std::atan2(y, x)));

    return {ra, dec};
}

/**
 * @brief THEOREM: Equatorial to Ecliptic conversion.
 */
inline std::pair<double, double> equatorial_to_ecliptic(double ra_deg, double dec_deg, double obliquity_deg) {
    double eps = deg_to_rad(obliquity_deg);
    double ra = deg_to_rad(ra_deg);
    double dec = deg_to_rad(dec_deg);

    double sin_lat = std::sin(dec) * std::cos(eps) - std::cos(dec) * std::sin(eps) * std::sin(ra);
    double lat = rad_to_deg(std::asin(clamp(sin_lat, -1.0, 1.0)));

    double y = std::sin(ra) * std::cos(eps) + std::tan(dec) * std::sin(eps);
    double x = std::cos(ra);
    double lon = normalize_deg_360(rad_to_deg(std::atan2(y, x)));

    return {lon, lat};
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_COORDINATES_HPP
