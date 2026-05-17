#ifndef MOIRA_NATIVE_HARMOGRAMS_HPP
#define MOIRA_NATIVE_HARMOGRAMS_HPP

#include <cmath>
#include <complex>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include "math_utils.hpp"

#ifdef _OPENMP
#include <omp.h>
#endif

namespace moira {
namespace native {

// Matches Python's _normalize_angle_deg: clamps floating-point 360.0 → 0.0.
inline double normalize_phase_deg(double deg) {
    double n = normalize_deg_360(deg);
    if (std::abs(n - 360.0) < 1.0e-12) return 0.0;
    return n;
}

// ── Fourier kernel ────────────────────────────────────────────────────────────
//
// Computes the harmonic vector components for a set of ecliptic longitudes.
//
// For each harmonic h, accumulates:
//   z = Σ exp(i · h · θ_k)   (θ in radians)
// then optionally normalises by N (mean-resultant mode).
//
// Returns a vector of (harmonic, amplitude, phase_deg) tuples, one per
// harmonic in the supplied list, in the same order.
//
// Arguments:
//   longitudes_deg  ecliptic longitudes in degrees
//   harmonics       ordered list of positive harmonic numbers to analyse
//   raw_sum         if true, skip /N normalisation (RAW_SUM mode)

inline std::vector<std::tuple<int, double, double>>
harmogram_compute_components(
    const std::vector<double>& longitudes_deg,
    const std::vector<int>&    harmonics,
    bool                       raw_sum)
{
    if (longitudes_deg.empty()) {
        throw std::invalid_argument("longitudes_deg must not be empty");
    }
    const double n = static_cast<double>(longitudes_deg.size());

    std::vector<std::tuple<int, double, double>> result;
    result.reserve(harmonics.size());

    for (const int h : harmonics) {
        std::complex<double> total(0.0, 0.0);
        for (const double lon : longitudes_deg) {
            const double angle = deg_to_rad(static_cast<double>(h) * lon);
            total += std::complex<double>(std::cos(angle), std::sin(angle));
        }
        if (!raw_sum) {
            total /= n;
        }
        const double amp = std::abs(total);
        double phase_deg = 0.0;
        if (amp >= 1.0e-12) {
            phase_deg = normalize_phase_deg(
                rad_to_deg(std::atan2(total.imag(), total.real()))
            );
        }
        result.emplace_back(h, amp, phase_deg);
    }
    return result;
}

// ── Intensity function helpers ────────────────────────────────────────────────

namespace detail {

inline double signed_smallest_angle_deg(double angle_deg) {
    double n = normalize_deg_360(angle_deg);
    if (n >= 180.0) n -= 360.0;
    return n;
}

// Evaluate the intensity orb function at a single angle.
//
// orb_mode:        "cosine_bell" | "top_hat" | "triangular" | "gaussian"
// half_width_deg:  pre-computed half-orb (orb_width_deg / harmonic_number)
// sigma_deg:       pre-computed sigma for gaussian mode (ignored otherwise)
// centers_deg:     pre-computed peak centres

inline double intensity_at_angle(
    double                     angle_deg,
    const std::vector<double>& centers_deg,
    double                     half_width_deg,
    const std::string&         orb_mode,
    double                     sigma_deg)
{
    if (centers_deg.empty()) return 0.0;

    double best = 0.0;
    for (const double center : centers_deg) {
        const double delta = std::abs(signed_smallest_angle_deg(angle_deg - center));
        if (delta > half_width_deg) continue;

        double v = 0.0;
        if (orb_mode == "cosine_bell") {
            v = 0.5 * (1.0 + std::cos(PI * delta / half_width_deg));
        } else if (orb_mode == "top_hat") {
            v = 1.0;
        } else if (orb_mode == "triangular") {
            v = 1.0 - (delta / half_width_deg);
        } else if (orb_mode == "gaussian") {
            v = std::exp(-0.5 * (delta / sigma_deg) * (delta / sigma_deg));
        } else {
            throw std::invalid_argument("unknown orb_mode: " + orb_mode);
        }
        if (v > best) best = v;
    }
    return best;
}

} // namespace detail

// ── DFT intensity kernel ──────────────────────────────────────────────────────
//
// Samples the intensity orb function over [0°, 360°) and computes the DFT
// spectral components for each harmonic in [harmonic_start, harmonic_stop].
//
// This mirrors compute.py _compute_intensity_components exactly.
//
// Arguments:
//   harmonic_number       which harmonic the orb function is centred on
//   harmonic_start/stop   inclusive range of spectral harmonics to compute
//   sample_count          number of equidistant samples over 360°
//   orb_mode              "cosine_bell" | "top_hat" | "triangular" | "gaussian"
//   orb_width_deg         orb half-width at harmonic 1 (scaled by 1/h internally)
//   include_conjunction   whether to place a peak at 0°
//   orb_scaling_mode      must be "equated_to_harmonic_one" (only supported mode)
//   gaussian_width_deg    sigma (or FWHM) parameter used when orb_mode == "gaussian"
//   gaussian_fwhm_mode    if true, gaussian_width_deg is interpreted as FWHM
//
// Returns: (h0_amplitude, [(harmonic, amplitude, phase_deg), ...])

inline std::pair<double, std::vector<std::tuple<int, double, double>>>
harmogram_intensity_components(
    int                harmonic_number,
    int                harmonic_start,
    int                harmonic_stop,
    int                sample_count,
    const std::string& orb_mode,
    double             orb_width_deg,
    bool               include_conjunction,
    const std::string& orb_scaling_mode,
    double             gaussian_width_deg,
    bool               gaussian_fwhm_mode)
{
    if (harmonic_number <= 0) {
        throw std::invalid_argument("harmonic_number must be positive");
    }
    if (orb_scaling_mode != "equated_to_harmonic_one") {
        throw std::invalid_argument(
            "unsupported orb_scaling_mode: " + orb_scaling_mode
        );
    }

    // Build peak centres
    const double step = 360.0 / static_cast<double>(harmonic_number);
    std::vector<double> centers;
    if (include_conjunction) {
        for (int i = 0; i < harmonic_number; ++i) {
            centers.push_back(i * step);
        }
    } else {
        for (int i = 1; i < harmonic_number; ++i) {
            centers.push_back(i * step);
        }
    }

    const double half_width = orb_width_deg / static_cast<double>(harmonic_number);

    // Gaussian sigma
    double sigma_deg = 0.0;
    if (orb_mode == "gaussian") {
        double w = gaussian_width_deg / static_cast<double>(harmonic_number);
        if (gaussian_fwhm_mode) {
            sigma_deg = w / (2.0 * std::sqrt(2.0 * std::log(2.0)));
        } else {
            sigma_deg = w;
        }
    }

    // Sample the intensity function
    std::vector<double> samples(static_cast<size_t>(sample_count));
    double h0_sum = 0.0;
    for (int i = 0; i < sample_count; ++i) {
        const double angle = (360.0 * i) / static_cast<double>(sample_count);
        const double v = detail::intensity_at_angle(
            angle, centers, half_width, orb_mode, sigma_deg
        );
        samples[static_cast<size_t>(i)] = v;
        h0_sum += v;
    }
    const double h0_amplitude = h0_sum / static_cast<double>(sample_count);

    // DFT over [harmonic_start, harmonic_stop]
    const double inv_n = 1.0 / static_cast<double>(sample_count);
    std::vector<std::tuple<int, double, double>> components;
    components.reserve(static_cast<size_t>(harmonic_stop - harmonic_start + 1));

    for (int h = harmonic_start; h <= harmonic_stop; ++h) {
        std::complex<double> total(0.0, 0.0);
        for (int idx = 0; idx < sample_count; ++idx) {
            const double angle = deg_to_rad(
                (360.0 * idx) / static_cast<double>(sample_count)
            );
            total += samples[static_cast<size_t>(idx)]
                   * std::complex<double>(
                         std::cos(-static_cast<double>(h) * angle),
                         std::sin(-static_cast<double>(h) * angle));
        }
        total *= inv_n;
        const double amp = std::abs(total);
        double phase_deg = 0.0;
        if (amp >= 1.0e-12) {
            phase_deg = normalize_phase_deg(
                rad_to_deg(std::atan2(total.imag(), total.real()))
            );
        }
        components.emplace_back(h, amp, phase_deg);
    }

    return {h0_amplitude, std::move(components)};
}

// ── Batch trace kernel ────────────────────────────────────────────────────────
//
// Computes ZA-parts Fourier decomposition + intensity projection for N time
// samples in a single call, running samples in parallel via OpenMP when
// available.
//
// Each sample contributes:
//   ZA parts  = { normalize(source_lon[i] - target_lon[j]) }
//   z_src[h]  = Σ exp(i·h·part) / N_parts  (or raw sum)
//   term[h]   = 2·Re(z_src[h] · z_int[h])
//   strength  = h0_contribution + Σ term[h]
//
// Returns:
//   (total_strengths[N], source_components[N][H])
//
//   source_components[i][k] = (harmonic, amplitude, phase_deg)
//   These are returned so Python can build HarmogramProjectionTerm objects
//   without re-running the Fourier computation.
//
// Arguments:
//   samples_source_lons   outer index = sample, inner = source longitudes (deg)
//   samples_target_lons   outer index = sample, inner = target longitudes (deg)
//                         empty → same_source_target must be true (source used)
//   same_source_target    true → source == target (enables triangular mode)
//   ordered               true → full N×M cross-product; false → upper-triangular
//   include_self          whether to include i==j pairs (same-index positions)
//   raw_sum               false → divide by parts_count
//   h0_contribution       h0_source_amplitude × intensity_h0_amplitude (scalar,
//                         same for every sample in a trace)
//   harmonics             ordered list of positive harmonic numbers
//   intensity_components  (harmonic, amplitude, phase_deg) — intensity spectrum

struct HarmogramBatchResult {
    std::vector<double>                                        total_strengths;
    std::vector<std::vector<std::tuple<int, double, double>>>  sample_components;
};

inline HarmogramBatchResult harmogram_trace_batch(
    const std::vector<std::vector<double>>& samples_source_lons,
    const std::vector<std::vector<double>>& samples_target_lons,
    bool                                    same_source_target,
    bool                                    ordered,
    bool                                    include_self,
    bool                                    raw_sum,
    double                                  h0_contribution,
    const std::vector<int>&                 harmonics,
    const std::vector<std::tuple<int, double, double>>& intensity_components)
{
    const int N = static_cast<int>(samples_source_lons.size());
    const int H = static_cast<int>(harmonics.size());

    // Pre-convert intensity components to complex<double> — done once, shared.
    std::vector<std::complex<double>> intensity_z(static_cast<size_t>(H));
    for (int k = 0; k < H; ++k) {
        const double amp   = std::get<1>(intensity_components[static_cast<size_t>(k)]);
        const double phase = std::get<2>(intensity_components[static_cast<size_t>(k)]);
        intensity_z[static_cast<size_t>(k)] =
            std::polar(amp, deg_to_rad(phase));
    }

    HarmogramBatchResult result;
    result.total_strengths.resize(static_cast<size_t>(N));
    result.sample_components.resize(static_cast<size_t>(N));

#ifdef _OPENMP
#pragma omp parallel for schedule(static)
#endif
    for (int i = 0; i < N; ++i) {
        const std::vector<double>& src_lons = samples_source_lons[static_cast<size_t>(i)];
        const std::vector<double>& tgt_lons =
            same_source_target ? src_lons
                               : samples_target_lons[static_cast<size_t>(i)];

        // Compute ZA parts (angular differences, normalized to [0°, 360°))
        std::vector<double> parts;
        if (same_source_target && !ordered) {
            const int n = static_cast<int>(src_lons.size());
            for (int a = 0; a < n; ++a) {
                const int j_start = include_self ? a : a + 1;
                for (int b = j_start; b < n; ++b) {
                    parts.push_back(normalize_deg_360(src_lons[static_cast<size_t>(a)]
                                                    - src_lons[static_cast<size_t>(b)]));
                }
            }
        } else {
            const int ns = static_cast<int>(src_lons.size());
            const int nt = static_cast<int>(tgt_lons.size());
            for (int a = 0; a < ns; ++a) {
                for (int b = 0; b < nt; ++b) {
                    if (same_source_target && !include_self && a == b) continue;
                    parts.push_back(normalize_deg_360(src_lons[static_cast<size_t>(a)]
                                                    - tgt_lons[static_cast<size_t>(b)]));
                }
            }
        }

        const int    n_parts = static_cast<int>(parts.size());
        const double inv_n   = raw_sum ? 1.0 : (n_parts > 0 ? 1.0 / n_parts : 1.0);

        // Fused Fourier + projection: compute z_src[h] and immediately project.
        double total = h0_contribution;
        std::vector<std::tuple<int, double, double>> comps(static_cast<size_t>(H));

        for (int k = 0; k < H; ++k) {
            const int h = harmonics[static_cast<size_t>(k)];
            std::complex<double> z_src(0.0, 0.0);
            for (const double part : parts) {
                const double angle = deg_to_rad(static_cast<double>(h) * part);
                z_src += std::complex<double>(std::cos(angle), std::sin(angle));
            }
            z_src *= inv_n;

            // projection term: 2·Re(z_src · z_int)
            total += 2.0 * (z_src * intensity_z[static_cast<size_t>(k)]).real();

            // store source component for model building
            const double amp = std::abs(z_src);
            double phase_deg = 0.0;
            if (amp >= 1.0e-12) {
                phase_deg = normalize_phase_deg(
                    rad_to_deg(std::atan2(z_src.imag(), z_src.real()))
                );
            }
            comps[static_cast<size_t>(k)] = {h, amp, phase_deg};
        }

        result.total_strengths[static_cast<size_t>(i)]   = total;
        result.sample_components[static_cast<size_t>(i)] = std::move(comps);
    }

    return result;
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_HARMOGRAMS_HPP
