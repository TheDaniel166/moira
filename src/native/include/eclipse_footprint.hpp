#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <map>
#include <optional>
#include <stdexcept>
#include <utility>
#include <vector>

#include "constants.hpp"

namespace moira {
namespace native {

/**
 * One terrestrial penumbral-cone state sufficient for fixed-site clearance.
 *
 * Python owns construction of this state, including ephemeris identity,
 * light-time, UT1/TT policy, Earth orientation, and public product meaning.
 * Native owns only the repeated Euclidean clearance evaluation.
 */
struct PenumbralClearanceShadow {
    std::array<double, 3> fundamental_plane_point_xyz_km{};
    std::array<double, 3> axis_unit_away_from_sun{};
    double penumbral_radius_km = 0.0;
    double penumbral_cone_slope = 0.0;
};

struct PenumbralClearanceScan {
    double sampled_maximum = -std::numeric_limits<double>::infinity();
    std::vector<std::array<double, 3>> local_maximum_brackets;
};

class PenumbralClearanceScanner {
public:
    PenumbralClearanceScanner(
        std::vector<double> epochs,
        std::vector<PenumbralClearanceShadow> shadows
    ) : epochs_(std::move(epochs)), shadows_(std::move(shadows)) {
        if (epochs_.size() < 3 || epochs_.size() != shadows_.size()) {
            throw std::invalid_argument(
                "penumbral clearance scanner requires at least three paired epochs and shadows"
            );
        }
        for (std::size_t index = 0; index < epochs_.size(); ++index) {
            if (!std::isfinite(epochs_[index])) {
                throw std::invalid_argument("penumbral clearance epochs must be finite");
            }
            if (index > 0 && !(epochs_[index - 1] < epochs_[index])) {
                throw std::invalid_argument(
                    "penumbral clearance epochs must be strictly increasing"
                );
            }
            validate_shadow(shadows_[index]);
        }
    }

    [[nodiscard]] std::size_t size() const noexcept { return epochs_.size(); }

    [[nodiscard]] PenumbralClearanceScan scan(
        const std::array<double, 3>& site_xyz_itrf_km,
        double witness_epoch,
        const PenumbralClearanceShadow& witness_shadow
    ) const {
        for (double component : site_xyz_itrf_km) {
            if (!std::isfinite(component)) {
                throw std::invalid_argument("penumbral clearance site must be finite");
            }
        }
        if (!std::isfinite(witness_epoch)) {
            throw std::invalid_argument("penumbral clearance witness epoch must be finite");
        }
        if (witness_epoch < epochs_.front() || witness_epoch > epochs_.back()) {
            throw std::invalid_argument(
                "penumbral clearance witness epoch must lie inside the scanner interval"
            );
        }
        validate_shadow(witness_shadow);

        std::vector<std::pair<double, double>> samples;
        samples.reserve(epochs_.size() + 1);
        bool witness_present = false;
        for (std::size_t index = 0; index < epochs_.size(); ++index) {
            samples.emplace_back(
                epochs_[index],
                clearance(shadows_[index], site_xyz_itrf_km)
            );
            if (epochs_[index] == witness_epoch) {
                witness_present = true;
            }
        }
        if (!witness_present) {
            samples.emplace_back(
                witness_epoch,
                clearance(witness_shadow, site_xyz_itrf_km)
            );
            std::sort(
                samples.begin(),
                samples.end(),
                [](const auto& left, const auto& right) {
                    return left.first < right.first;
                }
            );
        }

        PenumbralClearanceScan result;
        for (const auto& sample : samples) {
            result.sampled_maximum = std::max(result.sampled_maximum, sample.second);
        }
        for (std::size_t index = 1; index + 1 < samples.size(); ++index) {
            if (
                samples[index].second < samples[index - 1].second
                || samples[index].second < samples[index + 1].second
            ) {
                continue;
            }
            result.local_maximum_brackets.push_back({
                samples[index - 1].first,
                samples[index].first,
                samples[index + 1].first,
            });
        }
        return result;
    }

private:
    std::vector<double> epochs_;
    std::vector<PenumbralClearanceShadow> shadows_;

    static void validate_shadow(const PenumbralClearanceShadow& shadow) {
        for (double component : shadow.fundamental_plane_point_xyz_km) {
            if (!std::isfinite(component)) {
                throw std::invalid_argument("penumbral shadow plane point must be finite");
            }
        }
        double axis_norm_sq = 0.0;
        for (double component : shadow.axis_unit_away_from_sun) {
            if (!std::isfinite(component)) {
                throw std::invalid_argument("penumbral shadow axis must be finite");
            }
            axis_norm_sq += component * component;
        }
        if (
            !std::isfinite(axis_norm_sq)
            || std::abs(axis_norm_sq - 1.0) > 1.0e-12
        ) {
            throw std::invalid_argument("penumbral shadow axis must be unit length");
        }
        if (
            !std::isfinite(shadow.penumbral_radius_km)
            || !std::isfinite(shadow.penumbral_cone_slope)
        ) {
            throw std::invalid_argument("penumbral shadow cone terms must be finite");
        }
    }

    static double clearance(
        const PenumbralClearanceShadow& shadow,
        const std::array<double, 3>& site
    ) {
        std::array<double, 3> offset{};
        double axial_km = 0.0;
        for (std::size_t index = 0; index < 3; ++index) {
            offset[index] = site[index] - shadow.fundamental_plane_point_xyz_km[index];
            axial_km += offset[index] * shadow.axis_unit_away_from_sun[index];
        }
        double perpendicular_sq_km2 = 0.0;
        for (std::size_t index = 0; index < 3; ++index) {
            const double perpendicular =
                offset[index] - axial_km * shadow.axis_unit_away_from_sun[index];
            perpendicular_sq_km2 += perpendicular * perpendicular;
        }
        const double cone_radius_km =
            shadow.penumbral_radius_km
            + shadow.penumbral_cone_slope * axial_km;
        return cone_radius_km - std::sqrt(perpendicular_sq_km2);
    }
};

/**
 * Python-owned terrestrial shadow state needed by the generator kernel.
 *
 * The extra basis and Moon-axis coordinate are deliberately absent from the
 * clearance scanner above: this larger vessel is admitted only for bounded
 * WGS-84 cone-generator candidate discovery.
 */
struct PenumbralEnvelopeShadow : PenumbralClearanceShadow {
    double axis_projection_km = 0.0;
    std::array<double, 3> fundamental_east_unit_itrf{};
    std::array<double, 3> fundamental_north_unit_itrf{};
};

struct PenumbralEnvelopeCandidate {
    double azimuth_rad = 0.0;
    std::array<double, 3> xyz_itrf_km{};
    double latitude_deg = 0.0;
    double longitude_deg = 0.0;
    double signed_half_chord_sq_km2 = 0.0;
};

namespace eclipse_footprint_detail {

constexpr double WGS84_FLATTENING = 1.0 / 298.257223563;
constexpr double WGS84_POLAR_RADIUS_KM =
    EARTH_RADIUS_KM * (1.0 - WGS84_FLATTENING);
constexpr double WGS84_AXIS_TANGENCY_TOLERANCE_KM2 = 1.0e-6;
constexpr std::size_t PENUMBRAL_AZIMUTH_BRACKETS = 360;

inline double dot(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right
) {
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

inline std::array<double, 3> add(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right
) {
    return {left[0] + right[0], left[1] + right[1], left[2] + right[2]};
}

inline std::array<double, 3> subtract(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right
) {
    return {left[0] - right[0], left[1] - right[1], left[2] - right[2]};
}

inline std::array<double, 3> scale(
    const std::array<double, 3>& value,
    double factor
) {
    return {value[0] * factor, value[1] * factor, value[2] * factor};
}

inline double normalize_angle(double angle) {
    angle = std::fmod(angle, TAU);
    return angle < 0.0 ? angle + TAU : angle;
}

inline double wrap_longitude_deg(double longitude) {
    longitude = std::fmod(longitude + 180.0, 360.0);
    if (longitude < 0.0) {
        longitude += 360.0;
    }
    return longitude - 180.0;
}

inline void validate_clearance_shadow(const PenumbralClearanceShadow& shadow) {
    for (double component : shadow.fundamental_plane_point_xyz_km) {
        if (!std::isfinite(component)) {
            throw std::invalid_argument("penumbral shadow plane point must be finite");
        }
    }
    double axis_norm_sq = 0.0;
    for (double component : shadow.axis_unit_away_from_sun) {
        if (!std::isfinite(component)) {
            throw std::invalid_argument("penumbral shadow axis must be finite");
        }
        axis_norm_sq += component * component;
    }
    if (
        !std::isfinite(axis_norm_sq)
        || std::abs(axis_norm_sq - 1.0) > 1.0e-12
    ) {
        throw std::invalid_argument("penumbral shadow axis must be unit length");
    }
    if (
        !std::isfinite(shadow.penumbral_radius_km)
        || !std::isfinite(shadow.penumbral_cone_slope)
    ) {
        throw std::invalid_argument("penumbral shadow cone terms must be finite");
    }
}

inline void validate_envelope_shadow(const PenumbralEnvelopeShadow& shadow) {
    validate_clearance_shadow(shadow);
    if (!std::isfinite(shadow.axis_projection_km)) {
        throw std::invalid_argument("penumbral shadow axis projection must be finite");
    }
    for (const auto* basis : {
        &shadow.fundamental_east_unit_itrf,
        &shadow.fundamental_north_unit_itrf,
    }) {
        for (double component : *basis) {
            if (!std::isfinite(component)) {
                throw std::invalid_argument("penumbral shadow basis must be finite");
            }
        }
        if (std::abs(dot(*basis, *basis) - 1.0) > 1.0e-12) {
            throw std::invalid_argument("penumbral shadow basis must be unit length");
        }
        if (std::abs(dot(*basis, shadow.axis_unit_away_from_sun)) > 1.0e-12) {
            throw std::invalid_argument("penumbral shadow basis must be axis-orthogonal");
        }
    }
    if (
        std::abs(
            dot(
                shadow.fundamental_east_unit_itrf,
                shadow.fundamental_north_unit_itrf
            )
        ) > 1.0e-12
    ) {
        throw std::invalid_argument("penumbral shadow basis must be orthogonal");
    }
}

inline double clearance(
    const PenumbralClearanceShadow& shadow,
    const std::array<double, 3>& site
) {
    const auto offset = subtract(site, shadow.fundamental_plane_point_xyz_km);
    const double axial_km = dot(offset, shadow.axis_unit_away_from_sun);
    const auto perpendicular = subtract(
        offset,
        scale(shadow.axis_unit_away_from_sun, axial_km)
    );
    const double cone_radius_km =
        shadow.penumbral_radius_km
        + shadow.penumbral_cone_slope * axial_km;
    return cone_radius_km - std::sqrt(dot(perpendicular, perpendicular));
}

inline std::pair<std::array<double, 3>, std::array<double, 3>> generator_line(
    const PenumbralEnvelopeShadow& shadow,
    double azimuth
) {
    const auto radial = add(
        scale(shadow.fundamental_east_unit_itrf, std::cos(azimuth)),
        scale(shadow.fundamental_north_unit_itrf, std::sin(azimuth))
    );
    return {
        add(
            shadow.fundamental_plane_point_xyz_km,
            scale(radial, shadow.penumbral_radius_km)
        ),
        add(
            shadow.axis_unit_away_from_sun,
            scale(radial, shadow.penumbral_cone_slope)
        ),
    };
}

struct LineIntersection {
    double signed_parameter_half_chord_sq = 0.0;
    double coefficient_a = 0.0;
    double coefficient_b = 0.0;
    std::optional<std::array<double, 2>> roots;
};

inline LineIntersection line_intersection(
    const std::array<double, 3>& point,
    const std::array<double, 3>& direction
) {
    const double a2 = EARTH_RADIUS_KM * EARTH_RADIUS_KM;
    const double b2 = WGS84_POLAR_RADIUS_KM * WGS84_POLAR_RADIUS_KM;
    const double coefficient_a =
        (direction[0] * direction[0] + direction[1] * direction[1]) / a2
        + direction[2] * direction[2] / b2;
    if (coefficient_a <= 0.0 || !std::isfinite(coefficient_a)) {
        throw std::runtime_error("ellipsoid-intersection line has no finite direction");
    }
    const double coefficient_b =
        (point[0] * direction[0] + point[1] * direction[1]) / a2
        + point[2] * direction[2] / b2;
    const double coefficient_c =
        (point[0] * point[0] + point[1] * point[1]) / a2
        + point[2] * point[2] / b2
        - 1.0;
    const double discriminant = std::fma(
        -coefficient_a,
        coefficient_c,
        coefficient_b * coefficient_b
    );
    const double signed_half_chord_sq =
        discriminant / (coefficient_a * coefficient_a);
    LineIntersection result{
        signed_half_chord_sq,
        coefficient_a,
        coefficient_b,
        std::nullopt,
    };
    if (signed_half_chord_sq < -WGS84_AXIS_TANGENCY_TOLERANCE_KM2) {
        return result;
    }
    const double half_chord_km = std::sqrt(std::max(0.0, signed_half_chord_sq));
    const double chord_center_km = -coefficient_b / coefficient_a;
    result.roots = std::array<double, 2>{
        chord_center_km - half_chord_km,
        chord_center_km + half_chord_km,
    };
    return result;
}

inline double generator_margin(
    const PenumbralEnvelopeShadow& shadow,
    double azimuth
) {
    const auto [origin, direction] = generator_line(shadow, azimuth);
    const auto intersection = line_intersection(origin, direction);
    return intersection.signed_parameter_half_chord_sq * dot(direction, direction);
}

inline std::optional<PenumbralEnvelopeCandidate> generator_point(
    const PenumbralEnvelopeShadow& shadow,
    double azimuth,
    bool tangent = false
) {
    azimuth = normalize_angle(azimuth);
    const auto [origin, direction] = generator_line(shadow, azimuth);
    const auto intersection = line_intersection(origin, direction);
    const double signed_half_chord_sq =
        intersection.signed_parameter_half_chord_sq * dot(direction, direction);
    if (!intersection.roots.has_value()) {
        return std::nullopt;
    }
    double parameter = 0.0;
    if (tangent) {
        parameter = -intersection.coefficient_b / intersection.coefficient_a;
    } else {
        const auto& roots = *intersection.roots;
        const bool first_lawful = roots[0] >= shadow.axis_projection_km;
        const bool second_lawful = roots[1] >= shadow.axis_projection_km;
        if (!first_lawful && !second_lawful) {
            return std::nullopt;
        }
        parameter = first_lawful ? roots[0] : roots[1];
    }
    if (parameter < shadow.axis_projection_km) {
        return std::nullopt;
    }
    if (parameter - shadow.axis_projection_km <= MOON_RADIUS_KM) {
        throw std::runtime_error(
            "penumbral generator has no physical Earth intersection beyond the Moon"
        );
    }
    const auto xyz = add(origin, scale(direction, parameter));
    const double radial_xy = std::hypot(xyz[0], xyz[1]);
    const double longitude = radial_xy == 0.0
        ? 0.0
        : wrap_longitude_deg(std::atan2(xyz[1], xyz[0]) * RAD2DEG);
    const double latitude = std::atan2(
        xyz[2] / (WGS84_POLAR_RADIUS_KM * WGS84_POLAR_RADIUS_KM),
        radial_xy / (EARTH_RADIUS_KM * EARTH_RADIUS_KM)
    ) * RAD2DEG;
    return PenumbralEnvelopeCandidate{
        azimuth,
        xyz,
        latitude,
        longitude,
        signed_half_chord_sq,
    };
}

template <typename Function>
inline std::pair<double, double> periodic_extreme(
    Function&& function,
    bool maximize
) {
    const double step = TAU / static_cast<double>(PENUMBRAL_AZIMUTH_BRACKETS);
    std::array<double, PENUMBRAL_AZIMUTH_BRACKETS> values{};
    for (std::size_t index = 0; index < values.size(); ++index) {
        values[index] = function(static_cast<double>(index) * step);
        if (!std::isfinite(values[index])) {
            throw std::runtime_error("penumbral azimuth objective must remain finite");
        }
    }
    std::size_t best_index = 0;
    for (std::size_t index = 1; index < values.size(); ++index) {
        if (
            (maximize && values[index] > values[best_index])
            || (!maximize && values[index] < values[best_index])
        ) {
            best_index = index;
        }
    }
    double left = (static_cast<double>(best_index) - 1.0) * step;
    double right = (static_cast<double>(best_index) + 1.0) * step;
    const auto objective = [&](double angle) {
        const double value = function(normalize_angle(angle));
        return maximize ? -value : value;
    };
    const double golden = (std::sqrt(5.0) - 1.0) / 2.0;
    double x1 = right - golden * (right - left);
    double x2 = left + golden * (right - left);
    double f1 = objective(x1);
    double f2 = objective(x2);
    for (int iteration = 0; iteration < 56; ++iteration) {
        if (f1 <= f2) {
            right = x2;
            x2 = x1;
            f2 = f1;
            x1 = right - golden * (right - left);
            f1 = objective(x1);
        } else {
            left = x1;
            x1 = x2;
            f1 = f2;
            x2 = left + golden * (right - left);
            f2 = objective(x2);
        }
    }
    const double azimuth = normalize_angle((left + right) / 2.0);
    return {azimuth, function(azimuth)};
}

template <typename Function>
inline double bisect_periodic_root(
    Function&& function,
    double left,
    double right
) {
    double f_left = function(normalize_angle(left));
    double f_right = function(normalize_angle(right));
    if (f_left == 0.0) {
        return normalize_angle(left);
    }
    if (f_right == 0.0) {
        return normalize_angle(right);
    }
    if (f_left * f_right > 0.0) {
        throw std::runtime_error("periodic azimuth root requires a sign-changing bracket");
    }
    for (int iteration = 0; iteration < 52; ++iteration) {
        const double midpoint = (left + right) / 2.0;
        const double f_midpoint = function(normalize_angle(midpoint));
        if (f_midpoint == 0.0) {
            return normalize_angle(midpoint);
        }
        if (f_left * f_midpoint <= 0.0) {
            right = midpoint;
            f_right = f_midpoint;
        } else {
            left = midpoint;
            f_left = f_midpoint;
        }
    }
    return normalize_angle((left + right) / 2.0);
}

inline std::array<double, 3> lawful_azimuth_interval(
    const PenumbralEnvelopeShadow& shadow
) {
    const auto margin = [&](double azimuth) {
        return generator_margin(shadow, azimuth);
    };
    const auto maximum = periodic_extreme(margin, true);
    const auto minimum = periodic_extreme(margin, false);
    if (maximum.second <= 0.0) {
        throw std::runtime_error("penumbral cone has no strict WGS-84 intersection");
    }
    if (minimum.second >= 0.0) {
        return {maximum.first, maximum.first + TAU, 1.0};
    }
    const double step = TAU / static_cast<double>(PENUMBRAL_AZIMUTH_BRACKETS);
    const auto root_on_side = [&](double direction) {
        for (std::size_t index = 1; index <= PENUMBRAL_AZIMUTH_BRACKETS; ++index) {
            const double outside = maximum.first
                + direction * static_cast<double>(index) * step;
            if (margin(normalize_angle(outside)) <= 0.0) {
                const double left = direction < 0.0 ? outside : maximum.first;
                const double right = direction < 0.0 ? maximum.first : outside;
                const double root = bisect_periodic_root(margin, left, right);
                double delta = normalize_angle(root - maximum.first + PI) - PI;
                if (direction < 0.0 && delta > 0.0) {
                    delta -= TAU;
                } else if (direction > 0.0 && delta < 0.0) {
                    delta += TAU;
                }
                return maximum.first + delta;
            }
        }
        throw std::runtime_error("partial penumbral cone arc has no limb endpoint");
    };
    const double left = root_on_side(-1.0);
    const double right = root_on_side(1.0);
    if (!(left < maximum.first && maximum.first < right)) {
        throw std::runtime_error("lawful penumbral arc does not contain its maximum");
    }
    return {left, right, 0.0};
}

inline std::vector<double> deduplicate_azimuths(
    std::vector<double> values,
    double tolerance = 1.0e-9
) {
    for (double& value : values) {
        value = normalize_angle(value);
    }
    std::sort(values.begin(), values.end());
    std::vector<double> result;
    for (double value : values) {
        if (result.empty() || std::abs(value - result.back()) > tolerance) {
            result.push_back(value);
        }
    }
    if (
        result.size() > 1
        && std::min(
            result.front() + TAU - result.back(),
            result.back() - result.front()
        ) <= tolerance
    ) {
        result.pop_back();
    }
    return result;
}

template <typename Function>
inline std::vector<double> adaptive_azimuth_roots(
    Function&& function,
    double left,
    double right
) {
    if (!std::isfinite(left) || !std::isfinite(right) || left >= right) {
        throw std::runtime_error("azimuth root domain must be finite and ordered");
    }
    const double coarse_step = TAU / static_cast<double>(PENUMBRAL_AZIMUTH_BRACKETS);
    const std::size_t cell_count = std::max<std::size_t>(
        1,
        static_cast<std::size_t>(std::ceil((right - left) / coarse_step))
    );
    const double cell_step = (right - left) / static_cast<double>(cell_count);
    const double minimum_width = 1.0e-4 * DEG2RAD;
    const double root_tolerance = 1.0e-12;
    std::map<double, double> cache;
    std::vector<double> roots;

    const auto value = [&](double angle) {
        const double key = std::nearbyint(angle * 1.0e15) / 1.0e15;
        const auto found = cache.find(key);
        if (found != cache.end()) {
            return found->second;
        }
        const double result = function(normalize_angle(angle));
        if (!std::isfinite(result)) {
            throw std::runtime_error("azimuth root objective must remain finite");
        }
        cache.emplace(key, result);
        return result;
    };

    const auto bisect = [&](double a, double b, double fa, double fb) {
        if (std::abs(fa) <= root_tolerance) {
            return a;
        }
        if (std::abs(fb) <= root_tolerance) {
            return b;
        }
        if (fa * fb > 0.0) {
            throw std::runtime_error("azimuth root bisection lost its sign bracket");
        }
        for (int iteration = 0; iteration < 56; ++iteration) {
            const double midpoint = (a + b) / 2.0;
            const double fm = value(midpoint);
            if (std::abs(fm) <= root_tolerance) {
                return midpoint;
            }
            if (fa * fm <= 0.0) {
                b = midpoint;
                fb = fm;
            } else {
                a = midpoint;
                fa = fm;
            }
        }
        return (a + b) / 2.0;
    };

    const auto inspect = [&](
        auto&& self,
        double a,
        double b,
        double fa,
        double fb,
        int depth
    ) -> void {
        const double midpoint = (a + b) / 2.0;
        const double fm = value(midpoint);
        const bool left_crossing = fa * fm < 0.0;
        const bool right_crossing = fm * fb < 0.0;
        const bool exact =
            std::abs(fa) <= root_tolerance
            || std::abs(fm) <= root_tolerance
            || std::abs(fb) <= root_tolerance;
        const bool slope_reversal = (fm - fa) * (fb - fm) <= 0.0;
        const bool magnitude_valley =
            std::abs(fm) <= 0.8 * std::min(std::abs(fa), std::abs(fb));
        const bool should_split =
            left_crossing
            || right_crossing
            || exact
            || slope_reversal
            || magnitude_valley;
        if (should_split && b - a > minimum_width && depth < 24) {
            self(self, a, midpoint, fa, fm, depth + 1);
            self(self, midpoint, b, fm, fb, depth + 1);
            return;
        }
        if (left_crossing) {
            roots.push_back(bisect(a, midpoint, fa, fm));
        } else if (std::abs(fa) <= root_tolerance) {
            roots.push_back(a);
        }
        if (right_crossing) {
            roots.push_back(bisect(midpoint, b, fm, fb));
        } else if (std::abs(fm) <= root_tolerance) {
            roots.push_back(midpoint);
        }
        if (std::abs(fb) <= root_tolerance) {
            roots.push_back(b);
        }
    };

    const auto refine_extreme = [&](double a, double b, bool maximize) {
        const double golden = (std::sqrt(5.0) - 1.0) / 2.0;
        double x1 = b - golden * (b - a);
        double x2 = a + golden * (b - a);
        const auto score = [&](double angle) {
            const double result = value(angle);
            return maximize ? result : -result;
        };
        double f1 = score(x1);
        double f2 = score(x2);
        for (int iteration = 0; iteration < 56; ++iteration) {
            if (f1 >= f2) {
                b = x2;
                x2 = x1;
                f2 = f1;
                x1 = b - golden * (b - a);
                f1 = score(x1);
            } else {
                a = x1;
                x1 = x2;
                f1 = f2;
                x2 = a + golden * (b - a);
                f2 = score(x2);
            }
        }
        const double angle = (a + b) / 2.0;
        return std::pair<double, double>{angle, value(angle)};
    };

    std::vector<double> points(cell_count + 1);
    std::vector<double> values(cell_count + 1);
    for (std::size_t index = 0; index <= cell_count; ++index) {
        points[index] = left + static_cast<double>(index) * cell_step;
        values[index] = value(points[index]);
    }
    for (std::size_t index = 0; index < cell_count; ++index) {
        inspect(
            inspect,
            points[index],
            points[index + 1],
            values[index],
            values[index + 1],
            0
        );
    }
    for (std::size_t index = 1; index < cell_count; ++index) {
        const double left_value = values[index - 1];
        const double center_value = values[index];
        const double right_value = values[index + 1];
        if (center_value >= left_value && center_value >= right_value) {
            const auto [angle, extreme_value] = refine_extreme(
                points[index - 1],
                points[index + 1],
                true
            );
            if (extreme_value >= -root_tolerance) {
                if (left_value * extreme_value <= 0.0) {
                    roots.push_back(bisect(
                        points[index - 1], angle, left_value, extreme_value
                    ));
                }
                if (extreme_value * right_value <= 0.0) {
                    roots.push_back(bisect(
                        angle, points[index + 1], extreme_value, right_value
                    ));
                }
            }
        } else if (center_value <= left_value && center_value <= right_value) {
            const auto [angle, extreme_value] = refine_extreme(
                points[index - 1],
                points[index + 1],
                false
            );
            if (extreme_value <= root_tolerance) {
                if (left_value * extreme_value <= 0.0) {
                    roots.push_back(bisect(
                        points[index - 1], angle, left_value, extreme_value
                    ));
                }
                if (extreme_value * right_value <= 0.0) {
                    roots.push_back(bisect(
                        angle, points[index + 1], extreme_value, right_value
                    ));
                }
            }
        }
    }
    const double endpoint_span = std::min(coarse_step, (right - left) / 2.0);
    for (const auto [endpoint, direction] : std::array<std::array<double, 2>, 2>{
        std::array<double, 2>{left, 1.0},
        std::array<double, 2>{right, -1.0},
    }) {
        std::vector<double> offsets{0.0, endpoint_span};
        for (int power = 1; power < 45; ++power) {
            offsets.push_back(std::ldexp(endpoint_span, -power));
        }
        std::sort(offsets.begin(), offsets.end());
        offsets.erase(std::unique(offsets.begin(), offsets.end()), offsets.end());
        std::vector<double> endpoint_points;
        std::vector<double> endpoint_values;
        endpoint_points.reserve(offsets.size());
        endpoint_values.reserve(offsets.size());
        for (double offset : offsets) {
            const double point = endpoint + direction * offset;
            endpoint_points.push_back(point);
            endpoint_values.push_back(value(point));
        }
        for (std::size_t index = 0; index + 1 < endpoint_points.size(); ++index) {
            double a = endpoint_points[index];
            double b = endpoint_points[index + 1];
            double fa = endpoint_values[index];
            double fb = endpoint_values[index + 1];
            if (a > b) {
                std::swap(a, b);
                std::swap(fa, fb);
            }
            if (fa * fb < 0.0) {
                roots.push_back(bisect(a, b, fa, fb));
            } else if (std::abs(fa) <= root_tolerance) {
                roots.push_back(a);
            } else if (std::abs(fb) <= root_tolerance) {
                roots.push_back(b);
            }
        }
    }
    return deduplicate_azimuths(std::move(roots), minimum_width);
}

} // namespace eclipse_footprint_detail

inline std::vector<PenumbralEnvelopeCandidate> penumbral_envelope_candidates(
    const PenumbralEnvelopeShadow& shadow,
    const PenumbralClearanceShadow& before,
    const PenumbralClearanceShadow& after
) {
    using namespace eclipse_footprint_detail;
    validate_envelope_shadow(shadow);
    validate_clearance_shadow(before);
    validate_clearance_shadow(after);
    const auto interval = lawful_azimuth_interval(shadow);
    const auto derivative_at = [&](double azimuth) {
        auto point = generator_point(shadow, azimuth);
        if (!point.has_value()) {
            point = generator_point(shadow, azimuth, true);
        }
        if (!point.has_value()) {
            throw std::runtime_error("penumbral envelope root escaped its cone arc");
        }
        return clearance(after, point->xyz_itrf_km)
            - clearance(before, point->xyz_itrf_km);
    };
    const auto roots = adaptive_azimuth_roots(
        derivative_at,
        interval[0],
        interval[1]
    );
    std::vector<PenumbralEnvelopeCandidate> result;
    for (double azimuth : deduplicate_azimuths(roots)) {
        auto point = generator_point(shadow, azimuth);
        if (point.has_value()) {
            result.push_back(*point);
        }
    }
    return result;
}

} // namespace native
} // namespace moira
