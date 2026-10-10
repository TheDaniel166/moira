#include "marriage_enclosure.hpp"

#include <algorithm>
#include <cfenv>
#include <cmath>
#include <limits>
#include <stdexcept>

// This translation unit is compiled with contraction/reassociation disabled
// and without LTO. Python owns the reference operation schedule in
// _muhurta_marriage_astronomy._cheb_python, Differential and Interval. In
// particular a+b-c AND a+(b-c) remain distinct rounded branch families.
namespace moira::native {
namespace {

static_assert(std::numeric_limits<double>::is_iec559 &&
              std::numeric_limits<double>::digits == 53 &&
              std::numeric_limits<double>::radix == 2,
              "Marriage enclosures require IEEE binary64");

constexpr double infinity = std::numeric_limits<double>::infinity();

struct Interval {
    double lo;
    double hi;

    Interval(double lower, double upper) : lo(lower), hi(upper) {
        if (!std::isfinite(lo) || !std::isfinite(hi) || lo > hi) {
            throw std::invalid_argument("finite ordered interval required");
        }
    }
};

Interval point(double value) { return {value, value}; }

Interval add(const Interval& a, const Interval& b) {
    return {std::nextafter(a.lo + b.lo, -infinity),
            std::nextafter(a.hi + b.hi, infinity)};
}

Interval negate(const Interval& a) { return {-a.hi, -a.lo}; }

Interval multiply(const Interval& a, const Interval& b) {
    // Preserve Python's product order, including first-equal signed zeros.
    const auto products = {a.lo*b.lo, a.lo*b.hi, a.hi*b.lo, a.hi*b.hi};
    return {std::nextafter(std::min(products), -infinity),
            std::nextafter(std::max(products), infinity)};
}

Interval expand(const Interval& a, double radius) {
    if (!std::isfinite(radius) || radius < 0.) {
        throw std::invalid_argument("finite nonnegative radius required");
    }
    return {std::nextafter(a.lo-radius, -infinity),
            std::nextafter(a.hi+radius, infinity)};
}

double ulp(double value) {
    // Python math.ulp uses the upward binade spacing, including at powers of
    // two and DBL_MAX. nextafter(DBL_MAX,+inf)-DBL_MAX would be incorrect.
    int exponent = 0;
    std::frexp(std::abs(value), &exponent);
    return std::max(std::numeric_limits<double>::denorm_min(),
                    value == 0. ? 0. : std::ldexp(1., exponent-53));
}

struct Differential {
    Interval value;
    Interval rate;
    Interval center;
    double radius;
    bool centered;

    Differential(Interval v, Interval r, Interval c, double extent, bool common)
        : value(v), rate(r), center(c), radius(extent), centered(common) {
        if (!std::isfinite(radius) || radius < 0.) {
            throw std::invalid_argument("finite nonnegative radius required");
        }
        if (radius != 0. && centered) {
            const auto mean = add(center, multiply(rate, {-radius, radius}));
            const double lo = std::max(value.lo, mean.lo);
            const double hi = std::min(value.hi, mean.hi);
            if (lo > hi) {
                throw std::invalid_argument("inconsistent_centered_differential");
            }
            value = {lo, hi};
        }
    }
};

Differential constant(double value) {
    return {point(value), point(0.), point(value), 0., true};
}

Differential rounded(Interval value, Interval rate, Interval center,
                     double radius, bool centered) {
    const double guard = ulp(std::max(std::abs(value.lo), std::abs(value.hi)));
    return {expand(value, guard), rate, expand(center, guard), radius, centered};
}

Differential add(const Differential& a, const Differential& b) {
    return rounded(add(a.value, b.value), add(a.rate, b.rate),
                   add(a.center, b.center), std::max(a.radius, b.radius),
                   a.centered && b.centered);
}

Differential negate(const Differential& a) {
    // Construction performs the same centered intersection as Python __neg__.
    return {negate(a.value), negate(a.rate), negate(a.center), a.radius, a.centered};
}

Differential subtract(const Differential& a, const Differential& b) {
    return add(a, negate(b));
}

Differential multiply(const Differential& a, const Differential& b) {
    return rounded(multiply(a.value, b.value),
                   add(multiply(a.rate, b.value), multiply(a.value, b.rate)),
                   multiply(a.center, b.center), std::max(a.radius, b.radius),
                   a.centered && b.centered);
}

Interval hull(const Interval& a, const Interval& b) {
    return {std::min(a.lo, b.lo), std::max(a.hi, b.hi)};
}

Differential hull(const Differential& a, const Differential& b) {
    return {hull(a.value, b.value), hull(a.rate, b.rate), hull(a.center, b.center),
            std::max(a.radius, b.radius), a.centered && b.centered};
}

Differential recurrence(const Differential& a, const Differential& b,
                        const Differential& c) {
    return hull(subtract(add(a, b), c), add(a, subtract(b, c)));
}

MarriageDifferentialState transport(const Differential& a) {
    return {{{a.value.lo, a.value.hi, a.rate.lo, a.rate.hi,
              a.center.lo, a.center.hi, a.radius}}, a.centered};
}

void require_arithmetic_model() {
    // The existing proof is conditional on round-to-nearest and gradual
    // underflow. Refuse a changed host mode rather than silently certifying it.
    if (std::fegetround() != FE_TONEAREST) {
        throw std::invalid_argument("marriage_arithmetic_model_requires_round_to_nearest");
    }
    volatile double normal = std::numeric_limits<double>::min();
    volatile double half_normal = normal / 2.;
    volatile double tiny = std::numeric_limits<double>::denorm_min();
    volatile double twice_tiny = tiny + tiny;
    if (half_normal == 0. || twice_tiny != 2.*std::numeric_limits<double>::denorm_min()) {
        throw std::invalid_argument("marriage_arithmetic_model_requires_gradual_underflow");
    }
}

} // namespace

MarriageChebyshevEnclosure marriage_chebyshev_enclosure(
    const std::vector<double>& coefficients,
    const std::array<double, 7>& argument,
    bool centered
) {
    require_arithmetic_model();
    if (coefficients.empty()) {
        throw std::invalid_argument("nonempty Chebyshev coefficients required");
    }
    for (double coefficient : coefficients) {
        if (!std::isfinite(coefficient)) {
            throw std::invalid_argument("finite Chebyshev coefficients required");
        }
    }
    const Differential s({argument[0], argument[1]}, {argument[2], argument[3]},
                         {argument[4], argument[5]}, argument[6], centered);
    const auto two = constant(2.);
    const auto s2 = multiply(two, s);
    auto first = constant(0.);
    auto second = constant(0.);
    auto first_rate = constant(0.);
    auto second_rate = constant(0.);
    for (size_t index = coefficients.size()-1; index > 0; --index) {
        const auto next_rate = recurrence(multiply(two, first),
                                          multiply(s2, first_rate), second_rate);
        const auto next = recurrence(constant(coefficients[index]),
                                     multiply(s2, first), second);
        second_rate = first_rate;
        first_rate = next_rate;
        second = first;
        first = next;
    }
    return {transport(recurrence(constant(coefficients[0]), multiply(s, first), second)),
            transport(recurrence(first, multiply(s, first_rate), second_rate))};
}

} // namespace moira::native
