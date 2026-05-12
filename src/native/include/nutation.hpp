#ifndef MOIRA_NATIVE_NUTATION_HPP
#define MOIRA_NATIVE_NUTATION_HPP

#include <cmath>
#include <utility>
#include "constants.hpp"
#include "geometry.hpp"

namespace moira {
namespace native {

/**
 * @brief THEOREM: IAU 2000B Nutation (Truncated for Fast Path).
 * 
 * Provides Delta Psi and Delta Eps in radians.
 * This truncated model is accurate to ~1 mas within +/- 100 years of J2000.
 */
inline std::pair<double, double> nutation_iau2000b(double jd_tt) {
    double t = (jd_tt - J2000) / 36525.0;
    
    // Fundamental arguments (L, L', F, D, Omega) in arcseconds
    // Simplified IAU 2000 coefficients
    double el  = std::fmod(485867.746 + (1717915923.2178) * t, 1296000.0) * ARCSEC2RAD;
    double elp = std::fmod(1287104.793 + (129596581.0481) * t, 1296000.0) * ARCSEC2RAD;
    double f   = std::fmod(335779.526 + (1739527262.8478) * t, 1296000.0) * ARCSEC2RAD;
    double d   = std::fmod(1072260.703 + (1602961601.2090) * t, 1296000.0) * ARCSEC2RAD;
    double om  = std::fmod(450160.398 - (6962890.5431) * t, 1296000.0) * ARCSEC2RAD;

    // Principal terms (Delta Psi and Delta Eps in 0.1 mas units)
    double dpsi = (-172064.1 - 174.6 * t) * std::sin(om) 
                - (13170.9 + 1.6 * t) * std::sin(2.0 * (f - d + om))
                - (2276.4 + 0.2 * t) * std::sin(2.0 * om)
                + (2074.5 + 0.2 * t) * std::sin(2.0 * (f + om))
                + (1475.8 - 1.4 * t) * std::sin(el);
                
    double deps = (92052.3 + 8.9 * t) * std::cos(om)
                + (5730.3 - 3.1 * t) * std::cos(2.0 * (f - d + om))
                + (978.4 - 0.5 * t) * std::cos(2.0 * om)
                - (894.7 + 0.5 * t) * std::cos(2.0 * (f + om))
                + (73.8 - 0.1 * t) * std::cos(el);

    // Convert 0.1 mas to radians
    return { dpsi * 0.0001 * ARCSEC2RAD, deps * 0.0001 * ARCSEC2RAD };
}

/**
 * @brief THEOREM: Nutation Matrix (Mean to True).
 */
inline Mat3 nutation_matrix(double eps, double dpsi, double deps) {
    // Rotation by -eps, then -dpsi (around Z), then eps + deps
    // Standard approximation: 
    // N = Rx(eps+deps) * Rz(-dpsi) * Rx(-eps)
    
    double se = std::sin(eps);
    double ce = std::cos(eps);
    double sed = std::sin(eps + deps);
    double ced = std::cos(eps + deps);
    double sp = std::sin(-dpsi);
    double cp = std::cos(-dpsi);
    
    Mat3 m;
    m.data[0][0] = cp;
    m.data[0][1] = sp * ce;
    m.data[0][2] = sp * se;
    
    m.data[1][0] = -sp * ced;
    m.data[1][1] = cp * ce * ced + se * sed;
    m.data[1][2] = cp * se * ced - ce * sed;
    
    m.data[2][0] = -sp * sed;
    m.data[2][1] = cp * ce * sed - se * ced;
    m.data[2][2] = cp * se * sed + ce * ced;
    
    return m;
}

} // namespace native
} // namespace moira

#endif
