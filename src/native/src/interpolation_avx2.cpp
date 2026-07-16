#include "interpolation_simd.hpp"

#include <immintrin.h>

namespace moira {
namespace native {

namespace {

inline __m256d load_xyz(const double* values, size_t component_stride) {
    return _mm256_setr_pd(
        values[0], values[component_stride], values[2 * component_stride], 0.0
    );
}

inline void store_xyz(__m256d values, double* out) {
    alignas(32) double lanes[4];
    _mm256_store_pd(lanes, values);
    out[0] = lanes[0];
    out[1] = lanes[1];
    out[2] = lanes[2];
}

void evaluate(
    const double* coeffs,
    size_t coefficient_count,
    double s,
    double* result,
    double* derivative,
    size_t coeff_stride,
    size_t component_stride,
    bool reverse
) {
    const __m256d vs = _mm256_set1_pd(s);
    const __m256d s2 = _mm256_set1_pd(2.0 * s);
    const __m256d v2 = _mm256_set1_pd(2.0);
    __m256d w1 = _mm256_setzero_pd();
    __m256d w2 = _mm256_setzero_pd();
    __m256d dw1 = _mm256_setzero_pd();
    __m256d dw2 = _mm256_setzero_pd();

    for (size_t i = 0; i < coefficient_count - 1; ++i) {
        const size_t coefficient_index = reverse ? coefficient_count - 1 - i : i;
        const __m256d coefficient = load_xyz(
            coeffs + coefficient_index * coeff_stride, component_stride
        );
        if (derivative != nullptr) {
            const __m256d old_dw1 = dw1;
            dw1 = _mm256_add_pd(
                _mm256_mul_pd(v2, w1),
                _mm256_sub_pd(_mm256_mul_pd(s2, dw1), dw2)
            );
            dw2 = old_dw1;
        }
        const __m256d old_w1 = w1;
        w1 = _mm256_add_pd(
            coefficient,
            _mm256_sub_pd(_mm256_mul_pd(s2, w1), w2)
        );
        w2 = old_w1;
    }

    const double* final_coefficients = reverse
        ? coeffs
        : coeffs + (coefficient_count - 1) * coeff_stride;
    store_xyz(
        _mm256_add_pd(
            load_xyz(final_coefficients, component_stride),
            _mm256_sub_pd(_mm256_mul_pd(vs, w1), w2)
        ),
        result
    );
    if (derivative != nullptr) {
        store_xyz(
            _mm256_add_pd(w1, _mm256_sub_pd(_mm256_mul_pd(vs, dw1), dw2)),
            derivative
        );
    }
}

}  // namespace

void spk_chebyshev_record_avx2_impl(
    const double* coeffs, size_t coefficient_count, double s,
    double* result, size_t coeff_stride, size_t component_stride
) {
    evaluate(
        coeffs, coefficient_count, s, result, nullptr,
        coeff_stride, component_stride, false
    );
}

void spk_chebyshev_record_avx2_reverse_impl(
    const double* coeffs, size_t coefficient_count, double s,
    double* result, size_t coeff_stride, size_t component_stride
) {
    evaluate(
        coeffs, coefficient_count, s, result, nullptr,
        coeff_stride, component_stride, true
    );
}

void spk_chebyshev_record_with_derivative_avx2_impl(
    const double* coeffs, size_t coefficient_count, double s,
    double* result, double* derivative, size_t coeff_stride, size_t component_stride
) {
    evaluate(
        coeffs, coefficient_count, s, result, derivative,
        coeff_stride, component_stride, false
    );
}

void spk_chebyshev_record_with_derivative_avx2_reverse_impl(
    const double* coeffs, size_t coefficient_count, double s,
    double* result, double* derivative, size_t coeff_stride, size_t component_stride
) {
    evaluate(
        coeffs, coefficient_count, s, result, derivative,
        coeff_stride, component_stride, true
    );
}

}  // namespace native
}  // namespace moira
