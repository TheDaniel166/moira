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
constexpr double EARTH_RADIUS_KM = 6378.137;

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_CONSTANTS_HPP
