#ifndef MOIRA_NATIVE_SIDEREAL_HPP
#define MOIRA_NATIVE_SIDEREAL_HPP

#include <cmath>
#include "constants.hpp"
#include "math_utils.hpp"
#include "precession.hpp"

namespace moira {
namespace native {

// SOFA iauEra00 evaluation order: whole turns carried by the Julian-day
// fraction are taken exactly and only the 0.0027378... excess rate multiplies
// the long baseline (a full 1.0027378... * D loses ~0.3 mas at -2000).
inline double earth_rotation_angle(double jd_ut) {
    double D = jd_ut - J2000;
    double era_turns = std::fmod(jd_ut, 1.0) + 0.7790572732640 + 0.00273781191135448 * D;
    return mod_floor(era_turns, 1.0) * 360.0;
}

// IAU 2006 GMST (SOFA iauGmst06): ERA at UT1, equinox polynomial at TT.
inline double greenwich_mean_sidereal_time(double jd_ut, double jd_tt) {
    double D = jd_tt - J2000;
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

inline double gast_complementary_terms(double jd_tt) {
    double T = (jd_tt - J2000) / JULIAN_CENTURY;
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

// SOFA iauGst06a/iauEe00: the equation of the equinoxes uses the IAU 2006
// *mean* obliquity and the complementary terms, both at TT; Earth rotation
// uses UT1.  Mirrors moira.julian._apparent_sidereal_time_at_tt.
inline double apparent_sidereal_time(double jd_ut, double jd_tt, double nutation_longitude) {
    double gmst = greenwich_mean_sidereal_time(jd_ut, jd_tt);
    double ee = nutation_longitude * std::cos(mean_obliquity_p03(jd_tt) * DEG2RAD)
              + gast_complementary_terms(jd_tt);
    return mod_floor(gmst + ee, 360.0);
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_SIDEREAL_HPP
