#ifndef MOIRA_NATIVE_PRECESSION_HPP
#define MOIRA_NATIVE_PRECESSION_HPP

#include <cmath>
#include <tuple>
#include "geometry.hpp"
#include "constants.hpp"

namespace moira {
namespace native {

/**
 * @brief THEOREM: Vondrak 2011 Long-Term Precession.
 * 
 * Port of ERFA eraLtp / Vondrak, Capitaine & Wallace (2011).
 * Valid for +/- 200,000 years from J2000.
 */

// Obliquity at J2000.0 (arcseconds -> radians)
constexpr double VONDRAK_EPS0 = 84381.406 * ARCSEC2RAD;

/**
 * @brief THEOREM: IAU 2006 Mean Obliquity (eps_A).
 */
inline double mean_obliquity_p03(double jd_tt) {
    double T = (jd_tt - J2000) / 36525.0;
    double eps_a = (84381.406
             - 46.836769     * T
             -  0.0001831    * T * T
             +  0.00200340   * T * T * T
             -  0.000000576  * T * T * T * T
             -  0.0000000434 * T * T * T * T * T) / 3600.0;
    return eps_a;
}

struct VondrakPQ {
    double period;
    double pcos;
    double qcos;
    double psin;
    double qsin;
};

const VondrakPQ VONDRAK_PQPER[8] = {
    { 708.15, -5486.751211, -684.661560,  667.666730, -5523.863691},
    {2309.00,   -17.127623, 2446.283880, -2354.886252,  -549.747450},
    {1620.00,  -617.517403,  399.671049,  -428.152441,  -310.998056},
    { 492.20,   413.442940, -356.652376,   376.202861,   421.535876},
    {1183.00,    78.614193, -186.387003,   184.778874,   -36.776172},
    { 622.00,  -180.732815, -316.800070,   335.321713,  -145.278396},
    { 882.00,   -87.676083,  198.296701,  -185.138669,   -34.744450},
    { 547.00,    46.140315,  101.135679,  -120.972830,    22.885731}
};

const double VONDRAK_PQPOL[2][4] = {
    { 5851.607687, -0.1189000, -0.00028913,  0.000000101},  // P_A
    {-1600.886300,  1.1689818, -0.00000020, -0.000000437}   // Q_A
};

struct VondrakXY {
    double period;
    double xcos;
    double ycos;
    double xsin;
    double ysin;
};

const VondrakXY VONDRAK_XYPER[14] = {
    { 256.75,  -819.940624, 75004.344875, 81491.287984,  1558.515853},
    { 708.15, -8444.676815,   624.033993,   787.163481,  7774.939698},
    { 274.20,  2600.009459,  1251.136893,  1251.296102, -2219.534038},
    { 241.45,  2755.175630, -1102.212834, -1257.950837, -2523.969396},
    {2309.00,  -167.659835, -2660.664980, -2966.799730,   247.850422},
    { 492.20,   871.855056,   699.291817,   639.744522,  -846.485643},
    { 396.10,    44.769698,   153.167220,   131.600209, -1393.124055},
    { 288.90,  -512.313065,  -950.865637,  -445.040117,   368.526116},
    { 231.10,  -819.415595,   499.754645,   584.522874,   749.045012},
    {1610.00,  -538.071099,  -145.188210,   -89.756563,   444.704518},
    { 620.00,  -189.793622,   558.116553,   524.429630,   235.934465},
    { 157.87,  -402.922932,   -23.923029,   -13.549067,   374.049623},
    { 220.30,   179.516345,  -165.405086,  -210.157124,  -171.330180},
    {1200.00,    -9.814756,     9.344131,   -44.919798,   -22.899655}
};

const double VONDRAK_XYPOL[2][4] = {
    { 5453.282155,  0.4252841, -0.00037173, -0.000000152},  // X_A
    {-73750.930350, -0.7675452, -0.00018725,  0.000000231}   // Y_A
};

inline Vec3 vondrak_ltpecl(double T) {
    double w = 2.0 * PI * T;
    double p = 0.0;
    double q = 0.0;
    for (const auto& col : VONDRAK_PQPER) {
        double a = w / col.period;
        double s = std::sin(a);
        double c = std::cos(a);
        p += c * col.pcos + s * col.psin;
        q += c * col.qcos + s * col.qsin;
    }
    p += VONDRAK_PQPOL[0][0] + T * (VONDRAK_PQPOL[0][1] + T * (VONDRAK_PQPOL[0][2] + T * VONDRAK_PQPOL[0][3]));
    q += VONDRAK_PQPOL[1][0] + T * (VONDRAK_PQPOL[1][1] + T * (VONDRAK_PQPOL[1][2] + T * VONDRAK_PQPOL[1][3]));
    p *= ARCSEC2RAD;
    q *= ARCSEC2RAD;
    double w2 = 1.0 - p * p - q * q;
    w2 = (w2 < 0.0) ? 0.0 : std::sqrt(w2);
    double s0 = std::sin(VONDRAK_EPS0);
    double c0 = std::cos(VONDRAK_EPS0);
    return Vec3(p, -q * c0 - w2 * s0, -q * s0 + w2 * c0);
}

inline Vec3 vondrak_ltpequ(double T) {
    double w = 2.0 * PI * T;
    double x = 0.0;
    double y = 0.0;
    for (const auto& col : VONDRAK_XYPER) {
        double a = w / col.period;
        double s = std::sin(a);
        double c = std::cos(a);
        x += c * col.xcos + s * col.xsin;
        y += c * col.ycos + s * col.ysin;
    }
    x += VONDRAK_XYPOL[0][0] + T * (VONDRAK_XYPOL[0][1] + T * (VONDRAK_XYPOL[0][2] + T * VONDRAK_XYPOL[0][3]));
    y += VONDRAK_XYPOL[1][0] + T * (VONDRAK_XYPOL[1][1] + T * (VONDRAK_XYPOL[1][2] + T * VONDRAK_XYPOL[1][3]));
    x *= ARCSEC2RAD;
    y *= ARCSEC2RAD;
    double w2 = 1.0 - x * x - y * y;
    return Vec3(x, y, (w2 < 0.0) ? 0.0 : std::sqrt(w2));
}

inline Mat3 vondrak_precession_matrix(double jd_tt) {
    double T = (jd_tt - J2000) / 36525.0;
    Vec3 peqr = vondrak_ltpequ(T);
    Vec3 pecl = vondrak_ltpecl(T);
    
    // eqx = normalize(peqr x pecl)
    Vec3 eqx = Vec3::cross(peqr, pecl).unit();
    // mid = peqr x eqx
    Vec3 mid = Vec3::cross(peqr, eqx);
    
    Mat3 m;
    m.data[0][0] = eqx[0]; m.data[0][1] = eqx[1]; m.data[0][2] = eqx[2];
    m.data[1][0] = mid[0]; m.data[1][1] = mid[1]; m.data[1][2] = mid[2];
    m.data[2][0] = peqr[0]; m.data[2][1] = peqr[1]; m.data[2][2] = peqr[2];
    return m;
}

/**
 * @brief THEOREM: IAU 2006 Fukushima-Williams Precession.
 * 
 * Port of ERFA eraPfw06 / Fukushima-Williams (2006).
 * Valid for +/- 50 centuries from J2000.
 */
inline Mat3 precession_matrix_fw06(double jd_tt) {
    double T = (jd_tt - J2000) / 36525.0;

    double gamb = ( -0.052928
                  + T * (10.556403
                  + T * (0.4932044
                  + T * (-0.00031238
                  + T * (-0.000002788
                  + T * (0.0000000260)))))) * ARCSEC2RAD;

    double phib = ( 84381.412819
                  + T * (-46.811016
                  + T * (0.0511268
                  + T * (0.00053289
                  + T * (-0.000000440
                  + T * (-0.0000000176)))))) * ARCSEC2RAD;

    double psib = ( -0.041775
                  + T * (5038.481484
                  + T * (1.5584175
                  + T * (-0.00018522
                  + T * (-0.000026452
                  + T * (-0.0000000148)))))) * ARCSEC2RAD;

    double epsa = mean_obliquity_p03(jd_tt) * DEG2RAD;

    // Build matrix: R1(-epsa) * R3(-psib) * R1(phib) * R3(gamb)
    Mat3 r3g = Mat3::rot_z(gamb);
    Mat3 r1p = Mat3::rot_x(phib);
    Mat3 r3s = Mat3::rot_z(-psib);
    Mat3 r1e = Mat3::rot_x(-epsa);

    return Mat3::mul(r1e, Mat3::mul(r3s, Mat3::mul(r1p, r3g)));
}

/**
 * @brief THEOREM: Universal Precession Routing.
 */
inline Mat3 precession_matrix(double jd_tt) {
    double T = (jd_tt - J2000) / 36525.0;
    if (std::abs(T) <= 50.0) {
        return precession_matrix_fw06(jd_tt);
    } else {
        return vondrak_precession_matrix(jd_tt);
    }
}


} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_PRECESSION_HPP
