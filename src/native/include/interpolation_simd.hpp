#ifndef MOIRA_NATIVE_INTERPOLATION_SIMD_HPP
#define MOIRA_NATIVE_INTERPOLATION_SIMD_HPP

#include <cstddef>

namespace moira {
namespace native {

bool runtime_avx2_available() noexcept;

void spk_chebyshev_record_avx2_impl(
    const double* coeffs, size_t coefficient_count, double s,
    double* result, size_t coeff_stride, size_t component_stride
);
void spk_chebyshev_record_avx2_reverse_impl(
    const double* coeffs, size_t coefficient_count, double s,
    double* result, size_t coeff_stride, size_t component_stride
);
void spk_chebyshev_record_with_derivative_avx2_impl(
    const double* coeffs, size_t coefficient_count, double s,
    double* result, double* derivative, size_t coeff_stride, size_t component_stride
);
void spk_chebyshev_record_with_derivative_avx2_reverse_impl(
    const double* coeffs, size_t coefficient_count, double s,
    double* result, double* derivative, size_t coeff_stride, size_t component_stride
);

}  // namespace native
}  // namespace moira

#endif
