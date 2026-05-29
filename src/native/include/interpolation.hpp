#ifndef MOIRA_NATIVE_INTERPOLATION_HPP
#define MOIRA_NATIVE_INTERPOLATION_HPP

#include <vector>
#include <array>
#include <utility>
#include <algorithm>
#include <cmath>
#include <stdexcept>

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
 * @brief THEOREM: SPK Type 13 Hermite state-vector evaluation.
 * Uses the same divided-difference Hermite interpolation doctrine as the
 * Python small-body path, over a centered sliding window of node states.
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

    constexpr double T0 = 2451545.0;
    constexpr double S_PER_DAY = 86400.0;

    const double* it = std::lower_bound(epochs, epochs + state_count, jd);
    size_t idx = std::distance(epochs, it);

    int start_idx = static_cast<int>(idx) - static_cast<int>(window_size) / 2;
    if (start_idx < 0) start_idx = 0;
    if (start_idx + static_cast<int>(window_size) > static_cast<int>(state_count)) {
        start_idx = static_cast<int>(state_count) - static_cast<int>(window_size);
    }
    if (start_idx < 0) start_idx = 0;

    size_t actual_window = std::min(window_size, state_count - start_idx);
    const size_t hermite_order = actual_window * 2;
    const double t_sec = (jd - T0) * S_PER_DAY;

    std::vector<double> z(hermite_order);
    for (size_t i = 0; i < actual_window; ++i) {
        const double epoch_sec = (epochs[start_idx + i] - T0) * S_PER_DAY;
        z[2 * i] = epoch_sec;
        z[2 * i + 1] = epoch_sec;
    }

    for (size_t axis = 0; axis < 3; ++axis) {
        std::vector<double> prev(hermite_order);
        std::vector<double> coeffs(hermite_order);
        for (size_t i = 0; i < actual_window; ++i) {
            const double position = states[axis * state_count + start_idx + i];
            prev[2 * i] = position;
            prev[2 * i + 1] = position;
        }
        coeffs[0] = prev[0];

        std::vector<double> curr(hermite_order - 1);
        for (size_t i = 0; i < hermite_order - 1; ++i) {
            if ((i % 2) == 0) {
                curr[i] = states[(axis + 3) * state_count + start_idx + i / 2];
            } else {
                const double denom = z[i + 1] - z[i];
                curr[i] = (prev[i + 1] - prev[i]) / denom;
            }
        }
        coeffs[1] = curr[0];
        prev = std::move(curr);

        for (size_t j = 2; j < hermite_order; ++j) {
            curr.assign(hermite_order - j, 0.0);
            for (size_t i = 0; i < hermite_order - j; ++i) {
                const double denom = z[i + j] - z[i];
                curr[i] = (prev[i + 1] - prev[i]) / denom;
            }
            coeffs[j] = curr[0];
            prev = std::move(curr);
        }

        double value = coeffs[hermite_order - 1];
        double derivative = 0.0;
        for (size_t j = hermite_order - 1; j-- > 0;) {
            const double delta = t_sec - z[j];
            derivative = value + delta * derivative;
            value = coeffs[j] + delta * value;
        }

        result[axis] = value;
        result[axis + 3] = derivative * S_PER_DAY;
    }
}

/**
 * @brief Natural cubic smoothing spline solver and evaluator.
 * Minimizes: sum((y_i - f(x_i))^2) + p * integral(f''(t)^2 dt)
 * Solves the interior second derivatives (M) using an O(n) pentadiagonal Cholesky solver.
 */
class CubicSmoothingSpline {
public:
    CubicSmoothingSpline(const std::vector<double>& x,
                         const std::vector<double>& y,
                         double p)
        : x_(x), y_(y), p_(p) {
        fit();
    }

    double evaluate(double target) const {
        if (x_.empty()) return 0.0;
        if (target <= x_.front()) return y_hat_.front();
        if (target >= x_.back()) return y_hat_.back();

        // Binary search to find containing interval [x_[idx], x_[idx+1]]
        auto it = std::upper_bound(x_.begin(), x_.end(), target);
        size_t idx = std::distance(x_.begin(), it) - 1;

        double hi = h_[idx];
        double xi = x_[idx];
        double xi1 = x_[idx + 1];
        double yi = y_hat_[idx];
        double yi1 = y_hat_[idx + 1];
        double mi = M_[idx];
        double mi1 = M_[idx + 1];

        double A = (xi1 - target) / hi;
        double B = (target - xi) / hi;
        return A * yi + B * yi1 + ((A * A * A - A) * mi + (B * B * B - B) * mi1) * (hi * hi) / 6.0;
    }

    std::vector<double> get_knots() const {
        return x_;
    }

    std::vector<double> get_y_hat() const {
        return y_hat_;
    }

    std::vector<double> get_M() const {
        return M_;
    }

private:
    std::vector<double> x_;
    std::vector<double> y_;
    double p_;
    std::vector<double> h_;
    std::vector<double> y_hat_;
    std::vector<double> M_;

    void fit() {
        size_t n = x_.size();
        if (n < 3) {
            y_hat_ = y_;
            M_.assign(n, 0.0);
            return;
        }

        h_.resize(n - 1);
        for (size_t i = 0; i < n - 1; ++i) {
            h_[i] = x_[i + 1] - x_[i];
            if (h_[i] <= 0.0) {
                throw std::invalid_argument("CubicSmoothingSpline: x values must be strictly increasing");
            }
        }

        size_t N = n - 2;
        std::vector<double> d(N, 0.0);
        std::vector<double> e(N - 1, 0.0);
        std::vector<double> f(N - 2, 0.0);

        for (size_t j = 0; j < N; ++j) {
            double qtq_j = 1.0 / (h_[j] * h_[j]) + 
                           (1.0 / h_[j] + 1.0 / h_[j+1]) * (1.0 / h_[j] + 1.0 / h_[j+1]) + 
                           1.0 / (h_[j+1] * h_[j+1]);
            d[j] = p_ * qtq_j + (h_[j] + h_[j+1]) / 3.0;

            if (j < N - 1) {
                double qtq_je = -1.0 / h_[j+1] * (1.0 / h_[j] + 2.0 / h_[j+1] + 1.0 / h_[j+2]);
                e[j] = p_ * qtq_je + h_[j+1] / 6.0;
            }

            if (j < N - 2) {
                double qtq_jf = 1.0 / (h_[j+1] * h_[j+2]);
                f[j] = p_ * qtq_jf;
            }
        }

        // b = Q.T * y
        std::vector<double> b(N, 0.0);
        for (size_t j = 0; j < N; ++j) {
            b[j] = y_[j] / h_[j] - 
                   y_[j+1] * (1.0 / h_[j] + 1.0 / h_[j+1]) + 
                   y_[j+2] / h_[j+1];
        }

        // Solve pentadiagonal system K * M = b via banded Cholesky (L * L^T)
        std::vector<double> M_int(N, 0.0);

        if (N == 1) {
            if (d[0] <= 0.0) {
                throw std::runtime_error("CubicSmoothingSpline Cholesky: system is not positive-definite");
            }
            double l0 = std::sqrt(d[0]);
            double z0 = b[0] / l0;
            M_int[0] = z0 / l0;
        } else if (N == 2) {
            if (d[0] <= 0.0) {
                throw std::runtime_error("CubicSmoothingSpline Cholesky: system is not positive-definite");
            }
            double l0 = std::sqrt(d[0]);
            double c0 = e[0] / l0;
            double d1_val = d[1] - c0 * c0;
            if (d1_val <= 0.0) {
                throw std::runtime_error("CubicSmoothingSpline Cholesky: system is not positive-definite");
            }
            double l1 = std::sqrt(d1_val);

            double z0 = b[0] / l0;
            double z1 = (b[1] - c0 * z0) / l1;

            M_int[1] = z1 / l1;
            M_int[0] = (z0 - c0 * M_int[1]) / l0;
        } else {
            std::vector<double> l(N, 0.0);
            std::vector<double> c(N - 1, 0.0);
            std::vector<double> g(N - 2, 0.0);

            if (d[0] <= 0.0) {
                throw std::runtime_error("CubicSmoothingSpline Cholesky: system is not positive-definite");
            }
            l[0] = std::sqrt(d[0]);
            c[0] = e[0] / l[0];
            g[0] = f[0] / l[0];

            double d1_val = d[1] - c[0] * c[0];
            if (d1_val <= 0.0) {
                throw std::runtime_error("CubicSmoothingSpline Cholesky: system is not positive-definite");
            }
            l[1] = std::sqrt(d1_val);
            c[1] = (e[1] - c[0] * g[0]) / l[1];
            if (N > 3) {
                g[1] = f[1] / l[1];
            }

            for (size_t i = 2; i < N; ++i) {
                double val = d[i] - c[i-1] * c[i-1] - g[i-2] * g[i-2];
                if (val <= 0.0) {
                    throw std::runtime_error("CubicSmoothingSpline Cholesky: system is not positive-definite");
                }
                l[i] = std::sqrt(val);
                if (i < N - 1) {
                    c[i] = (e[i] - c[i-1] * g[i-1]) / l[i];
                }
                if (i < N - 2) {
                    g[i] = f[i] / l[i];
                }
            }

            // Forward substitution: L * z = b
            std::vector<double> z(N, 0.0);
            z[0] = b[0] / l[0];
            z[1] = (b[1] - c[0] * z[0]) / l[1];
            for (size_t i = 2; i < N; ++i) {
                z[i] = (b[i] - c[i-1] * z[i-1] - g[i-2] * z[i-2]) / l[i];
            }

            // Backward substitution: L^T * M_int = z
            M_int[N - 1] = z[N - 1] / l[N - 1];
            M_int[N - 2] = (z[N - 2] - c[N - 2] * M_int[N - 1]) / l[N - 2];
            for (int i = static_cast<int>(N) - 3; i >= 0; --i) {
                M_int[i] = (z[i] - c[i] * M_int[i+1] - g[i] * M_int[i+2]) / l[i];
            }
        }

        M_.assign(n, 0.0);
        for (size_t i = 0; i < N; ++i) {
            M_[i + 1] = M_int[i];
        }

        // y_hat = y - p * Q * M_int
        y_hat_ = y_;
        for (size_t i = 0; i < n; ++i) {
            double qm = 0.0;
            if (i == 0) {
                qm = M_int[0] / h_[0];
            } else if (i == n - 1) {
                qm = M_int[N - 1] / h_[n - 2];
            } else {
                size_t j = i - 1;
                double val = 0.0;
                if (j > 0) {
                    val += M_int[j - 1] / h_[j];
                }
                val -= M_int[j] * (1.0 / h_[j] + 1.0 / h_[j+1]);
                if (j < N - 1) {
                    val += M_int[j + 1] / h_[j+1];
                }
                qm = val;
            }
            y_hat_[i] -= p_ * qm;
        }
    }
};

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_INTERPOLATION_HPP
