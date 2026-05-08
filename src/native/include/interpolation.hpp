#ifndef MOIRA_NATIVE_INTERPOLATION_HPP
#define MOIRA_NATIVE_INTERPOLATION_HPP

#include <vector>
#include <array>
#include <utility>
#include <algorithm>

namespace moira {
namespace native {

/**
 * @brief THEOREM: Horner's method for polynomial evaluation.
 * Evaluates a polynomial of the form: c0 + c1*x + c2*x^2 + ... + cn*x^n
 */
inline double horner(const std::vector<double>& coeffs, double x) {
    double res = 0.0;
    for (auto it = coeffs.rbegin(); it != coeffs.rend(); ++it) {
        res = res * x + (*it);
    }
    return res;
}

/**
 * @brief THEOREM: Chebyshev polynomial evaluation (First Kind) via Clenshaw recurrence.
 * Evaluates a Chebyshev expansion of degree n at x in [-1, 1].
 */
inline double chebyshev_eval(const double* coeffs, size_t n, double x, size_t stride = 1) {
    if (n == 0) return 0.0;
    if (n == 1) return coeffs[0];
    
    const double s2 = 2.0 * x;
    double w1 = 0.0;
    double w2 = 0.0;

    for (size_t i = 0; i < n - 1; ++i) {
        double tmp = w1;
        w1 = coeffs[i * stride] + s2 * w1 - w2;
        w2 = tmp;
    }
    
    return coeffs[(n - 1) * stride] + x * w1 - w2;
}

/**
 * @brief THEOREM: Lagrange interpolation.
 * Pointer-based version to avoid allocations in hot loops.
 */
inline double lagrange_interpolate(const double* x_pts, const double* y_pts, size_t n, double x) {
    double res = 0.0;
    for (size_t i = 0; i < n; ++i) {
        double term = y_pts[i];
        for (size_t j = 0; j < n; ++j) {
            if (i != j) {
                term *= (x - x_pts[j]) / (x_pts[i] - x_pts[j]);
            }
        }
        res += term;
    }
    return res;
}

/**
 * @brief Evaluate one SPK Chebyshev record in-place via Clenshaw recurrence.
 */
inline void spk_chebyshev_record_inplace(
    const double* coeffs,
    size_t coefficient_count,
    size_t component_count,
    double s,
    double* result,
    size_t coeff_stride = 1,
    size_t component_stride = 1
) {
    if (coefficient_count == 0) return;

    const double s2 = 2.0 * s;
    for (size_t j = 0; j < component_count; ++j) {
        double w1 = 0.0;
        double w2 = 0.0;
        for (size_t i = 0; i < coefficient_count - 1; ++i) {
            double c = coeffs[i * coeff_stride + j * component_stride];
            double tmp = w1;
            w1 = c + s2 * w1 - w2;
            w2 = tmp;
        }
        result[j] = coeffs[(coefficient_count - 1) * coeff_stride + j * component_stride] + s * w1 - w2;
    }
}

inline void spk_chebyshev_record_inplace_reverse(
    const double* coeffs,
    size_t coefficient_count,
    size_t component_count,
    double s,
    double* result,
    size_t coeff_stride = 1,
    size_t component_stride = 1
) {
    if (coefficient_count == 0) return;

    const double s2 = 2.0 * s;
    for (size_t j = 0; j < component_count; ++j) {
        double w1 = 0.0;
        double w2 = 0.0;
        for (size_t i = 0; i < coefficient_count - 1; ++i) {
            const size_t coeff_index = coefficient_count - 1 - i;
            double c = coeffs[coeff_index * coeff_stride + j * component_stride];
            double tmp = w1;
            w1 = c + s2 * w1 - w2;
            w2 = tmp;
        }
        result[j] = coeffs[j * component_stride] + s * w1 - w2;
    }
}

#if defined(__AVX2__)
#include <immintrin.h>
#endif

/**
 * @brief THEOREM: SIMD-Optimized SPK Chebyshev evaluation.
 * Evaluates XYZ components in parallel using AVX2.
 */
inline void spk_chebyshev_record_avx2(
    const double* coeffs,
    size_t coefficient_count,
    size_t component_count,
    double s,
    double* result,
    size_t coeff_stride = 1,
    size_t component_stride = 1
) {
#if defined(__AVX2__)
    if (component_count == 3 && component_stride == 1) {
        __m256d s2 = _mm256_set1_pd(2.0 * s);
        __m256d vs = _mm256_set1_pd(s);
        __m256d w1 = _mm256_setzero_pd();
        __m256d w2 = _mm256_setzero_pd();

        for (size_t i = 0; i < coefficient_count - 1; ++i) {
            const double* c_ptr = coeffs + i * coeff_stride;
            // Load 3 components (X, Y, Z) and pad with 0
            __m256d c = _mm256_setr_pd(c_ptr[0], c_ptr[1], c_ptr[2], 0.0);
            __m256d tmp = w1;
            // w1 = c + s2 * w1 - w2
            w1 = _mm256_add_pd(c, _mm256_sub_pd(_mm256_mul_pd(s2, w1), w2));
            w2 = tmp;
        }

        const double* cn_ptr = coeffs + (coefficient_count - 1) * coeff_stride;
        __m256d cn = _mm256_setr_pd(cn_ptr[0], cn_ptr[1], cn_ptr[2], 0.0);
        // res = cn + s * w1 - w2
        __m256d res = _mm256_add_pd(cn, _mm256_sub_pd(_mm256_mul_pd(vs, w1), w2));
        
        alignas(32) double out[4];
        _mm256_store_pd(out, res);
        result[0] = out[0]; result[1] = out[1]; result[2] = out[2];
        return;
    }
#endif
    // Fallback to scalar
    spk_chebyshev_record_inplace(coeffs, coefficient_count, component_count, s, result, coeff_stride, component_stride);
}

inline void spk_chebyshev_record_avx2_reverse(
    const double* coeffs,
    size_t coefficient_count,
    size_t component_count,
    double s,
    double* result,
    size_t coeff_stride = 1,
    size_t component_stride = 1
) {
#if defined(__AVX2__)
    if (component_count == 3 && component_stride == 1) {
        __m256d s2 = _mm256_set1_pd(2.0 * s);
        __m256d vs = _mm256_set1_pd(s);
        __m256d w1 = _mm256_setzero_pd();
        __m256d w2 = _mm256_setzero_pd();

        for (size_t i = 0; i < coefficient_count - 1; ++i) {
            const size_t coeff_index = coefficient_count - 1 - i;
            const double* c_ptr = coeffs + coeff_index * coeff_stride;
            __m256d c = _mm256_setr_pd(c_ptr[0], c_ptr[1], c_ptr[2], 0.0);
            __m256d tmp = w1;
            w1 = _mm256_add_pd(c, _mm256_sub_pd(_mm256_mul_pd(s2, w1), w2));
            w2 = tmp;
        }

        __m256d cn = _mm256_setr_pd(coeffs[0], coeffs[1], coeffs[2], 0.0);
        __m256d res = _mm256_add_pd(cn, _mm256_sub_pd(_mm256_mul_pd(vs, w1), w2));

        alignas(32) double out[4];
        _mm256_store_pd(out, res);
        result[0] = out[0]; result[1] = out[1]; result[2] = out[2];
        return;
    }
#endif
    spk_chebyshev_record_inplace_reverse(coeffs, coefficient_count, component_count, s, result, coeff_stride, component_stride);
}

/**
 * @brief Evaluate one SPK Chebyshev record and its derivative in-place via Clenshaw recurrence.
 */
inline void spk_chebyshev_record_with_derivative_inplace(
    const double* coeffs,
    size_t coefficient_count,
    size_t component_count,
    double s,
    double* result,
    double* derivative,
    size_t coeff_stride = 1,
    size_t component_stride = 1
) {
    if (coefficient_count == 0) return;

#if defined(__AVX2__)
    if (component_count == 3 && component_stride == 1) {
        __m256d vs = _mm256_set1_pd(s);
        __m256d s2 = _mm256_set1_pd(2.0 * s);
        __m256d v2 = _mm256_set1_pd(2.0);
        __m256d w1 = _mm256_setzero_pd(), w2 = _mm256_setzero_pd();
        __m256d dw1 = _mm256_setzero_pd(), dw2 = _mm256_setzero_pd();

        for (size_t i = 0; i < coefficient_count - 1; ++i) {
            const double* c_ptr = coeffs + i * coeff_stride;
            __m256d c = _mm256_setr_pd(c_ptr[0], c_ptr[1], c_ptr[2], 0.0);
            
            __m256d old_dw1 = dw1;
            // dw1 = (2.0 * w1) + (s2 * dw1 - dw2)
            dw1 = _mm256_add_pd(_mm256_mul_pd(v2, w1), _mm256_sub_pd(_mm256_mul_pd(s2, dw1), dw2));
            dw2 = old_dw1;

            __m256d old_w1 = w1;
            w1 = _mm256_add_pd(c, _mm256_sub_pd(_mm256_mul_pd(s2, w1), w2));
            w2 = old_w1;
        }
        const double* cn_ptr = coeffs + (coefficient_count - 1) * coeff_stride;
        __m256d cn = _mm256_setr_pd(cn_ptr[0], cn_ptr[1], cn_ptr[2], 0.0);

        __m256d res = _mm256_add_pd(cn, _mm256_sub_pd(_mm256_mul_pd(vs, w1), w2));
        __m256d d_res = _mm256_add_pd(w1, _mm256_sub_pd(_mm256_mul_pd(vs, dw1), dw2));

        alignas(32) double out_r[4], out_d[4];
        _mm256_store_pd(out_r, res);
        _mm256_store_pd(out_d, d_res);
        for(int i=0; i<3; ++i) { result[i] = out_r[i]; derivative[i] = out_d[i]; }
        return;
    }
#endif

    const double s2 = 2.0 * s;
    for (size_t j = 0; j < component_count; ++j) {
        double w1 = 0.0, w2 = 0.0;
        double dw1 = 0.0, dw2 = 0.0;
        for (size_t i = 0; i < coefficient_count - 1; ++i) {
            double c = coeffs[i * coeff_stride + j * component_stride];
            
            double old_dw1 = dw1;
            dw1 = (2.0 * w1) + (s2 * dw1 - dw2);
            dw2 = old_dw1;

            double old_w1 = w1;
            w1 = c + s2 * w1 - w2;
            w2 = old_w1;
        }
        result[j] = coeffs[(coefficient_count - 1) * coeff_stride + j * component_stride] + s * w1 - w2;
        derivative[j] = w1 + s * dw1 - dw2;
    }
}

inline void spk_chebyshev_record_with_derivative_inplace_reverse(
    const double* coeffs,
    size_t coefficient_count,
    size_t component_count,
    double s,
    double* result,
    double* derivative,
    size_t coeff_stride = 1,
    size_t component_stride = 1
) {
    if (coefficient_count == 0) return;

#if defined(__AVX2__)
    if (component_count == 3 && component_stride == 1) {
        __m256d vs = _mm256_set1_pd(s);
        __m256d s2 = _mm256_set1_pd(2.0 * s);
        __m256d v2 = _mm256_set1_pd(2.0);
        __m256d w1 = _mm256_setzero_pd(), w2 = _mm256_setzero_pd();
        __m256d dw1 = _mm256_setzero_pd(), dw2 = _mm256_setzero_pd();

        for (size_t i = 0; i < coefficient_count - 1; ++i) {
            const size_t coeff_index = coefficient_count - 1 - i;
            const double* c_ptr = coeffs + coeff_index * coeff_stride;
            __m256d c = _mm256_setr_pd(c_ptr[0], c_ptr[1], c_ptr[2], 0.0);

            __m256d old_dw1 = dw1;
            dw1 = _mm256_add_pd(_mm256_mul_pd(v2, w1), _mm256_sub_pd(_mm256_mul_pd(s2, dw1), dw2));
            dw2 = old_dw1;

            __m256d old_w1 = w1;
            w1 = _mm256_add_pd(c, _mm256_sub_pd(_mm256_mul_pd(s2, w1), w2));
            w2 = old_w1;
        }

        __m256d cn = _mm256_setr_pd(coeffs[0], coeffs[1], coeffs[2], 0.0);
        __m256d res = _mm256_add_pd(cn, _mm256_sub_pd(_mm256_mul_pd(vs, w1), w2));
        __m256d d_res = _mm256_add_pd(w1, _mm256_sub_pd(_mm256_mul_pd(vs, dw1), dw2));

        alignas(32) double out_r[4], out_d[4];
        _mm256_store_pd(out_r, res);
        _mm256_store_pd(out_d, d_res);
        for (int i = 0; i < 3; ++i) {
            result[i] = out_r[i];
            derivative[i] = out_d[i];
        }
        return;
    }
#endif

    const double s2 = 2.0 * s;
    for (size_t j = 0; j < component_count; ++j) {
        double w1 = 0.0, w2 = 0.0;
        double dw1 = 0.0, dw2 = 0.0;
        for (size_t i = 0; i < coefficient_count - 1; ++i) {
            const size_t coeff_index = coefficient_count - 1 - i;
            double c = coeffs[coeff_index * coeff_stride + j * component_stride];

            double old_dw1 = dw1;
            dw1 = (2.0 * w1) + (s2 * dw1 - dw2);
            dw2 = old_dw1;

            double old_w1 = w1;
            w1 = c + s2 * w1 - w2;
            w2 = old_w1;
        }
        result[j] = coeffs[j * component_stride] + s * w1 - w2;
        derivative[j] = w1 + s * dw1 - dw2;
    }
}

/**
 * @brief THEOREM: SPK Type 13 (Small Body) evaluation.
 * Uses Lagrange interpolation on a sliding window of points.
 */
inline void spk_type13_record_inplace(
    const double* epochs,
    const double* states, // Layout: [component][state_count]
    size_t state_count,
    size_t window_size,
    double jd,
    double* result
) {
    if (state_count == 0) return;

    // 1. Find the first epoch > jd
    const double* it = std::upper_bound(epochs, epochs + state_count, jd);
    size_t idx = std::distance(epochs, it);

    // 2. Determine window start
    // Window should be centered if possible
    int start_idx = static_cast<int>(idx) - static_cast<int>(window_size) / 2;
    if (start_idx < 0) start_idx = 0;
    if (start_idx + static_cast<int>(window_size) > static_cast<int>(state_count)) {
        start_idx = static_cast<int>(state_count) - static_cast<int>(window_size);
    }
    if (start_idx < 0) start_idx = 0; // Guard for state_count < window_size

    size_t actual_window = std::min(window_size, state_count - start_idx);

    // 3. Interpolate each component
    for (size_t j = 0; j < 6; ++j) {
        result[j] = lagrange_interpolate(
            epochs + start_idx,
            states + j * state_count + start_idx,
            actual_window,
            jd
        );
    }
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_INTERPOLATION_HPP
