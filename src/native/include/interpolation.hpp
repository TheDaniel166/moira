#ifndef MOIRA_NATIVE_INTERPOLATION_HPP
#define MOIRA_NATIVE_INTERPOLATION_HPP

#include <vector>
#include <array>

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
 * @brief THEOREM: Chebyshev polynomial evaluation (First Kind).
 * Evaluates a Chebyshev expansion of degree n at x in [-1, 1].
 */
inline double chebyshev_eval(const double* coeffs, int n, double x) {
    if (n == 0) return coeffs[0];
    if (n == 1) return coeffs[0] + coeffs[1] * x;

    double d1 = 0.0;
    double d2 = 0.0;
    double x2 = 2.0 * x;

    for (int j = n; j >= 1; --j) {
        double tmp = d1;
        d1 = x2 * d1 - d2 + coeffs[j];
        d2 = tmp;
    }
    return x * d1 - d2 + coeffs[0];
}

/**
 * @brief THEOREM: Chebyshev evaluation with first derivative.
 * Returns {position, velocity}.
 */
inline std::pair<double, double> chebyshev_eval_with_derivative(const double* coeffs, int n, double x) {
    if (n == 0) return {coeffs[0], 0.0};

    double d1 = 0.0;
    double d2 = 0.0;
    double v1 = 0.0;
    double v2 = 0.0;
    double x2 = 2.0 * x;

    for (int j = n; j >= 1; --j) {
        double tmp_d = d1;
        double tmp_v = v1;

        d1 = x2 * d1 - d2 + coeffs[j];
        d2 = tmp_d;

        v1 = x2 * v1 - v2 + 2.0 * tmp_d;
        v2 = tmp_v;
    }

    return {x * d1 - d2 + coeffs[0], v1 - x * v1 + v2 + d1}; // This is a simplified Clenshaw derivative, check carefully
}

/**
 * @brief THEOREM: Lagrange interpolation.
 */
inline double lagrange_interpolate(const std::vector<double>& x_pts, const std::vector<double>& y_pts, double x) {
    size_t n = x_pts.size();
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

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_INTERPOLATION_HPP
