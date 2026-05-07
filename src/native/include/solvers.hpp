#ifndef MOIRA_NATIVE_SOLVERS_HPP
#define MOIRA_NATIVE_SOLVERS_HPP

#include <functional>
#include <cmath>
#include <stdexcept>

namespace moira {
namespace native {

/**
 * @brief THEOREM: Bisection root finding.
 */
inline double bisect(std::function<double(double)> f, double a, double b, double tol = 1e-12, int max_iter = 100) {
    double fa = f(a);
    double fb = f(b);
    if (fa * fb > 0) throw std::runtime_error("bisect: root not bracketed");

    for (int i = 0; i < max_iter; ++i) {
        double c = (a + b) / 2.0;
        double fc = f(c);
        if (std::abs(fc) < tol || (b - a) / 2.0 < tol) return c;
        if (fa * fc < 0) {
            b = c;
            fb = fc;
        } else {
            a = c;
            fa = fc;
        }
    }
    return (a + b) / 2.0;
}

/**
 * @brief THEOREM: Newton-Raphson with bisection fallback (Safe Newton).
 */
inline double newton_safe(std::function<double(double)> f, std::function<double(double)> df, 
                         double a, double b, double tol = 1e-12, int max_iter = 100) {
    double x = (a + b) / 2.0;
    double fl = f(a);
    double fh = f(b);

    if (fl * fh > 0) throw std::runtime_error("newton_safe: root not bracketed");

    for (int i = 0; i < max_iter; ++i) {
        double fx = f(x);
        double dfx = df(x);

        // If Newton step is out of bounds or moving too slowly, bisect
        if ((((x - b) * dfx - fx) * ((x - a) * dfx - fx) > 0.0) || (std::abs(2.0 * fx) > std::abs((b - a) * dfx))) {
            double dx = (b - a) / 2.0;
            x = a + dx;
            if (a == x) return x;
        } else {
            x -= fx / dfx;
        }

        if (std::abs(b - a) < tol) return x;
        
        fx = f(x);
        if ((fx < 0 && fl < 0) || (fx > 0 && fl > 0)) {
            a = x;
            fl = fx;
        } else {
            b = x;
            fh = fx;
        }
    }
    return x;
}

/**
 * @brief THEOREM: Brent's method for 1D minimization (Golden section search).
 */
inline double minimize_bracketed(std::function<double(double)> f, double a, double b, double tol = 1e-12) {
    const double phi = (3.0 - std::sqrt(5.0)) / 2.0;
    double x = a + phi * (b - a);
    double y = a + (1.0 - phi) * (b - a);

    while (std::abs(b - a) > tol) {
        if (f(x) < f(y)) {
            b = y;
            y = x;
            x = a + phi * (b - a);
        } else {
            a = x;
            x = y;
            y = a + (1.0 - phi) * (b - a);
        }
    }
    return (a + b) / 2.0;
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_SOLVERS_HPP
