#ifndef MOIRA_NATIVE_SIDEREAL_HPP
#define MOIRA_NATIVE_SIDEREAL_HPP

#include <cmath>
#include "constants.hpp"
#include "math_utils.hpp"

namespace moira {
namespace native {

inline double earth_rotation_angle(double jd_ut) {
    double D = jd_ut - J2000;
    double era_turns = 0.7790572732640 + 1.00273781191135448 * D;
    return mod_floor(era_turns, 1.0) * 360.0;
}

inline double greenwich_mean_sidereal_time(double jd_ut) {
    double D = jd_ut - J2000;
    double T = D / JULIAN_CENTURY;

    double era_deg = earth_rotation_angle(jd_ut);
    double poly_arcsec = (
          0.014506
        + 4612.156534     * T
        +    1.3915817    * T * T
        -    0.00000044   * T * T * T
        -    0.000029956  * T * T * T * T
        -    0.0000000368 * T * T * T * T * T
    );

    return mod_floor(era_deg + poly_arcsec / 3600.0, 360.0);
}

inline double gast_complementary_terms(double jd_ut) {
    double T = (jd_ut - J2000) / JULIAN_CENTURY;
    double arcsec = PI / 648000.0;

    double Om = (450160.398036 + T * (-6962890.5431 + T * (7.4722 + T * 0.007702))) * arcsec;
    Om = mod_floor(Om, TAU);

    double F = mod_floor((335779.526232 + T * 1739527262.8478) * arcsec, TAU);
    double D = mod_floor((1072260.703692 + T * 1602961601.2090) * arcsec, TAU);

    double ct = (
          0.00264096 * std::sin(Om)
        + 0.00006352 * std::sin(2.0 * Om)
        + 0.00001175 * std::sin(2.0 * F - 2.0 * D + 3.0 * Om)
        + 0.00001121 * std::sin(2.0 * F - 2.0 * D + Om)
        - 0.00000455 * std::sin(2.0 * F - 2.0 * D + 2.0 * Om)
        + 0.00000202 * std::sin(2.0 * F + 3.0 * Om)
        + 0.00000198 * std::sin(2.0 * F + Om)
        - 0.00000172 * std::sin(3.0 * Om)
        - 0.00000087 * T * std::sin(Om)
    );

    return ct / 3600.0;
}

inline double apparent_sidereal_time(double jd_ut, double nutation_longitude, double obliquity) {
    double gmst = greenwich_mean_sidereal_time(jd_ut);
    double ee = nutation_longitude * std::cos(obliquity * DEG2RAD)
              + gast_complementary_terms(jd_ut);
    return mod_floor(gmst + ee, 360.0);
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_SIDEREAL_HPP
