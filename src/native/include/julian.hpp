#ifndef MOIRA_NATIVE_JULIAN_HPP
#define MOIRA_NATIVE_JULIAN_HPP

#include <cmath>
#include <tuple>

namespace moira {
namespace native {

/**
 * @brief THEOREM: Julian Day Number conversion (Meeus).
 */
inline double julian_day(int year, int month, int day, double hour = 0.0) {
    if (month <= 2) {
        year -= 1;
        month += 12;
    }

    long A = std::floor(year / 100.0);
    long B = 2 - A + std::floor(A / 4.0);

    double jd = std::floor(365.25 * (year + 4716))
              + std::floor(30.6001 * (month + 1))
              + day + B - 1524.5
              + hour / 24.0;
    return jd;
}

/**
 * @brief THEOREM: Calendar date from Julian Day Number (Meeus inverse).
 */
inline std::tuple<int, int, int, double> calendar_from_jd(double jd) {
    jd = jd + 0.5;
    double Z = std::floor(jd);
    double F = jd - Z;

    long A;
    if (Z < 2299161.0) {
        A = static_cast<long>(Z);
    } else {
        long alpha = static_cast<long>(std::floor((Z - 1867216.25) / 36524.25));
        A = static_cast<long>(Z + 1 + alpha - std::floor(alpha / 4.0));
    }

    long B = A + 1524;
    long C = static_cast<long>(std::floor((B - 122.1) / 365.25));
    long D = static_cast<long>(std::floor(365.25 * C));
    long E = static_cast<long>(std::floor((B - D) / 30.6001));

    double day = B - D - std::floor(30.6001 * E);
    int month = (E < 14) ? static_cast<int>(E - 1) : static_cast<int>(E - 13);
    int year = (month > 2) ? static_cast<int>(C - 4716) : static_cast<int>(C - 4715);
    double hour = F * 24.0;

    return {year, month, static_cast<int>(day), hour};
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_JULIAN_HPP
