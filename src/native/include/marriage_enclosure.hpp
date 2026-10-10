#ifndef MOIRA_NATIVE_MARRIAGE_ENCLOSURE_HPP
#define MOIRA_NATIVE_MARRIAGE_ENCLOSURE_HPP

#include <array>
#include <utility>
#include <vector>

namespace moira::native {

// Private transport for the Python-owned Differential:
// value.lo/hi, rate.lo/hi, center.lo/hi, common-variable radius; centered flag.
using MarriageDifferentialState = std::pair<std::array<double, 7>, bool>;
using MarriageChebyshevEnclosure =
    std::pair<MarriageDifferentialState, MarriageDifferentialState>;

// Exact operation-schedule translation of _cheb_python, not a new polynomial
// or motion model. The caller owns record selection, units and event policy.
MarriageChebyshevEnclosure marriage_chebyshev_enclosure(
    const std::vector<double>& coefficients,
    const std::array<double, 7>& argument,
    bool centered
);

} // namespace moira::native

#endif
