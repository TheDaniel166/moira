#ifndef MOIRA_NATIVE_NUTATION_HPP
#define MOIRA_NATIVE_NUTATION_HPP

#include <array>
#include <cstddef>
#include <mutex>
#include <unordered_map>
#include <vector>

#include "geometry.hpp"

namespace moira {
namespace native {

/** One source-table term from IERS 2010 Table 5.3a or 5.3b. */
struct NutationSeriesTerm {
    double c1 = 0.0;
    double c2 = 0.0;
    std::array<int, 14> arguments{};
    std::size_t argument_count = 0;
};

/** IERS 2000_R06 nutation result in radians. */
struct NutationResult {
    double longitude = 0.0;
    double obliquity = 0.0;
};

/**
 * Register one validated immutable snapshot of the packaged IERS tables.
 *
 * Python owns table discovery and parsing. Native callers receive a published
 * read-only snapshot so dense evaluation does not perform file I/O or hold a
 * mutex. Re-registration atomically replaces the complete snapshot.
 */
void register_nutation_2000r06_series(
    std::vector<NutationSeriesTerm> longitude_terms,
    std::vector<NutationSeriesTerm> obliquity_terms,
    std::size_t longitude_j0_count,
    std::size_t obliquity_j0_count
);

bool nutation_2000r06_series_ready() noexcept;

/** Evaluate the registered IERS 2000_R06 series at TT Julian date. */
NutationResult nutation_2000r06(double jd_tt);

/** Request-scoped exact-epoch cache for repeated batch nutation evaluation. */
class NutationEpochCache {
public:
    NutationResult evaluate(double jd_tt);
    std::size_t size() const;

private:
    mutable std::mutex mutex_;
    std::unordered_map<double, NutationResult> values_;
};

/** Mean-to-true equatorial nutation rotation. */
inline Mat3 nutation_matrix(double eps, double dpsi, double deps) {
    const double se = std::sin(eps);
    const double ce = std::cos(eps);
    const double sed = std::sin(eps + deps);
    const double ced = std::cos(eps + deps);
    const double sp = std::sin(-dpsi);
    const double cp = std::cos(-dpsi);

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
