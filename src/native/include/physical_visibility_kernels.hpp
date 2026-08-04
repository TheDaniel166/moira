#ifndef MOIRA_NATIVE_PHYSICAL_VISIBILITY_KERNELS_HPP
#define MOIRA_NATIVE_PHYSICAL_VISIBILITY_KERNELS_HPP

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace moira::native {

struct PhysicalVisibilityResponseWeights {
    double scotopic_to_photopic_ratio = 0.0;
    std::vector<double> photopic;
    std::vector<double> scotopic;
};

struct PhysicalVisibilityDirectExtinction {
    std::vector<double> extinction_magnitude;
    std::vector<double> transmission;
};

class PhysicalVisibilityDirectExtinctionKernel {
public:
    PhysicalVisibilityDirectExtinctionKernel(
        std::vector<double> extinction_magnitude,
        std::size_t spectral_bin_count
    )
        : extinction_magnitude_(std::move(extinction_magnitude)),
          spectral_bin_count_(spectral_bin_count) {
        if (
            spectral_bin_count_ == 0
            || extinction_magnitude_.empty()
            || extinction_magnitude_.size() % spectral_bin_count_ != 0
        ) {
            throw std::invalid_argument(
                "direct-extinction storage must contain complete nonempty rows"
            );
        }
        for (double value : extinction_magnitude_) {
            if (!std::isfinite(value) || value < 0.0) {
                throw std::invalid_argument(
                    "direct-extinction storage must be finite and nonnegative"
                );
            }
        }
    }

    PhysicalVisibilityDirectExtinction interpolate(
        std::size_t low,
        std::size_t high,
        double fraction
    ) const {
        const std::size_t row_count =
            extinction_magnitude_.size() / spectral_bin_count_;
        if (
            low >= row_count
            || high >= row_count
            || high < low
            || !std::isfinite(fraction)
            || fraction < 0.0
            || fraction > 1.0
        ) {
            throw std::out_of_range(
                "direct-extinction interpolation bracket is invalid"
            );
        }
        PhysicalVisibilityDirectExtinction result;
        result.extinction_magnitude.reserve(spectral_bin_count_);
        result.transmission.reserve(spectral_bin_count_);
        const std::size_t low_offset = low * spectral_bin_count_;
        const std::size_t high_offset = high * spectral_bin_count_;
        for (std::size_t index = 0; index < spectral_bin_count_; ++index) {
            const double low_value = extinction_magnitude_[low_offset + index];
            const double magnitude = low == high
                ? low_value
                : low_value
                    + fraction
                        * (
                            extinction_magnitude_[high_offset + index]
                            - low_value
                        );
            result.extinction_magnitude.push_back(magnitude);
            result.transmission.push_back(std::pow(10.0, -0.4 * magnitude));
        }
        return result;
    }

private:
    std::vector<double> extinction_magnitude_;
    std::size_t spectral_bin_count_ = 0;
};

inline double compensated_sum_products(
    const std::vector<double>& left,
    const std::vector<double>& right
) {
    double sum = 0.0;
    double compensation = 0.0;
    for (std::size_t index = 0; index < left.size(); ++index) {
        const double product = left[index] * right[index];
        const double adjusted = product - compensation;
        const double next = sum + adjusted;
        compensation = (next - sum) - adjusted;
        sum = next;
    }
    return sum;
}

inline PhysicalVisibilityResponseWeights
resolve_physical_visibility_response_weights(
    const std::vector<double>& band_wavelength_nm,
    const std::vector<double>& band_differential_magnitude,
    const std::vector<double>& spectral_bin_start_nm,
    double base_scotopic_to_photopic_ratio,
    const std::vector<double>& base_photopic,
    const std::vector<double>& base_scotopic
) {
    if (
        band_wavelength_nm.size() < 2
        || band_wavelength_nm.size() != band_differential_magnitude.size()
    ) {
        throw std::invalid_argument(
            "band wavelengths and differential magnitudes must have equal length >= 2"
        );
    }
    if (
        spectral_bin_start_nm.empty()
        || spectral_bin_start_nm.size() != base_photopic.size()
        || spectral_bin_start_nm.size() != base_scotopic.size()
    ) {
        throw std::invalid_argument(
            "spectral bins and response weights must have equal nonzero length"
        );
    }
    if (
        !std::isfinite(base_scotopic_to_photopic_ratio)
        || base_scotopic_to_photopic_ratio <= 0.0
    ) {
        throw std::invalid_argument(
            "base scotopic-to-photopic ratio must be positive and finite"
        );
    }
    for (std::size_t index = 0; index < band_wavelength_nm.size(); ++index) {
        if (
            !std::isfinite(band_wavelength_nm[index])
            || !std::isfinite(band_differential_magnitude[index])
            || (
                index > 0
                && band_wavelength_nm[index] <= band_wavelength_nm[index - 1]
            )
        ) {
            throw std::invalid_argument(
                "band wavelengths must be finite and strictly increasing; magnitudes must be finite"
            );
        }
    }
    for (std::size_t index = 0; index < spectral_bin_start_nm.size(); ++index) {
        if (
            !std::isfinite(spectral_bin_start_nm[index])
            || !std::isfinite(base_photopic[index])
            || base_photopic[index] < 0.0
            || !std::isfinite(base_scotopic[index])
            || base_scotopic[index] < 0.0
        ) {
            throw std::invalid_argument(
                "spectral bins and response weights must be finite; weights must be nonnegative"
            );
        }
    }

    constexpr double magnitude_to_natural_log =
        -0.4 * 2.3025850929940456840179914546843642;
    std::vector<double> log_correction;
    log_correction.reserve(spectral_bin_start_nm.size());
    for (double wavelength_nm : spectral_bin_start_nm) {
        const auto high = std::upper_bound(
            band_wavelength_nm.begin(),
            band_wavelength_nm.end(),
            wavelength_nm
        );
        if (
            high == band_wavelength_nm.begin()
            || high == band_wavelength_nm.end()
        ) {
            throw std::out_of_range(
                "spectral wavelength is outside the color-warp domain"
            );
        }
        const std::size_t high_index = static_cast<std::size_t>(
            high - band_wavelength_nm.begin()
        );
        const std::size_t low_index = high_index - 1;
        const double fraction =
            (wavelength_nm - band_wavelength_nm[low_index])
            / (band_wavelength_nm[high_index] - band_wavelength_nm[low_index]);
        const double interpolated =
            band_differential_magnitude[low_index]
            + fraction
                * (
                    band_differential_magnitude[high_index]
                    - band_differential_magnitude[low_index]
                );
        const double value = magnitude_to_natural_log * interpolated;
        if (!std::isfinite(value)) {
            throw std::runtime_error(
                "color warp produced a nonfinite logarithmic correction"
            );
        }
        log_correction.push_back(value);
    }

    const double maximum_log_correction = *std::max_element(
        log_correction.begin(), log_correction.end()
    );
    std::vector<double> correction;
    correction.reserve(log_correction.size());
    for (double value : log_correction) {
        correction.push_back(std::exp(value - maximum_log_correction));
    }
    const double photopic_scale = compensated_sum_products(
        base_photopic, correction
    );
    const double scotopic_scale = compensated_sum_products(
        base_scotopic, correction
    );
    if (
        !std::isfinite(photopic_scale)
        || !std::isfinite(scotopic_scale)
        || photopic_scale <= 0.0
        || scotopic_scale <= 0.0
    ) {
        throw std::runtime_error(
            "resolved response integral is nonpositive or nonfinite"
        );
    }

    PhysicalVisibilityResponseWeights result;
    result.scotopic_to_photopic_ratio =
        base_scotopic_to_photopic_ratio * scotopic_scale / photopic_scale;
    if (
        !std::isfinite(result.scotopic_to_photopic_ratio)
        || result.scotopic_to_photopic_ratio <= 0.0
    ) {
        throw std::runtime_error(
            "resolved scotopic-to-photopic ratio is nonpositive or nonfinite"
        );
    }
    result.photopic.reserve(base_photopic.size());
    result.scotopic.reserve(base_scotopic.size());
    for (std::size_t index = 0; index < correction.size(); ++index) {
        result.photopic.push_back(
            base_photopic[index] * correction[index] / photopic_scale
        );
        result.scotopic.push_back(
            base_scotopic[index] * correction[index] / scotopic_scale
        );
    }
    return result;
}

}  // namespace moira::native

#endif  // MOIRA_NATIVE_PHYSICAL_VISIBILITY_KERNELS_HPP
