#ifndef MOIRA_NATIVE_CONSTANTS_HPP
#define MOIRA_NATIVE_CONSTANTS_HPP

#include <cmath>

namespace moira {
namespace native {

// Mathematical Constants
constexpr double PI         = 3.14159265358979323846;
constexpr double TAU        = 6.28318530717958647692;
constexpr double DEG2RAD    = PI / 180.0;
constexpr double RAD2DEG    = 180.0 / PI;
constexpr double ARCSEC2RAD = DEG2RAD / 3600.0;

// Time Constants
constexpr double J2000          = 2451545.0;
constexpr double JULIAN_CENTURY = 36525.0;
constexpr double JULIAN_YEAR    = 365.25;

// Physical Constants
constexpr double C_KM_PER_DAY   = 299792.458 * 86400.0;
constexpr double KM_PER_AU      = 149597870.700;
constexpr double C_AU_PER_DAY   = C_KM_PER_DAY / KM_PER_AU;
constexpr double EARTH_RADIUS_KM = 6378.137;

// IAU 2009/2012 Planetary Radii (Equatorial, km)
constexpr double SUN_RADIUS_KM     = 695700.0;
constexpr double MOON_RADIUS_KM    = 1737.4;
constexpr double MERCURY_RADIUS_KM = 2439.7;
constexpr double VENUS_RADIUS_KM   = 6051.8;
constexpr double MARS_RADIUS_KM    = 3396.19;
constexpr double JUPITER_RADIUS_KM = 71492.0;
constexpr double SATURN_RADIUS_KM  = 60268.0;
constexpr double URANUS_RADIUS_KM  = 25559.0;
constexpr double NEPTUNE_RADIUS_KM = 24764.0;
constexpr double PLUTO_RADIUS_KM   = 1188.3;

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_CONSTANTS_HPP
