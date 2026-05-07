#ifndef MOIRA_NATIVE_SOLVERS_HPP
#define MOIRA_NATIVE_SOLVERS_HPP

#include <functional>
#include <cmath>
#include <stdexcept>

namespace moira {
namespace native {

/**
 * @brief THEOREM: Brent's Method for root finding.
 * Combines bisection, secant method, and inverse quadratic interpolation.
 * Guaranteed convergence for bracketed roots with superlinear performance.
 */
inline double brent_root(std::function<double(double)> f, double a, double b, double tol = 1e-12, int max_iter = 100) {
    double fa = f(a);
    double fb = f(b);

    if (fa * fb > 0) throw std::runtime_error("brent_root: root not bracketed");

    if (std::abs(fa) < std::abs(fb)) {
        std::swap(a, b);
        std::swap(fa, fb);
    }

    double c = a;
    double fc = fa;
    bool mflag = true;
    double d = 0;

    for (int i = 0; i < max_iter; ++i) {
        if (std::abs(fb) < tol || std::abs(b - a) < tol) return b;

        double s;
        if (fa != fc && fb != fc) {
            // Inverse quadratic interpolation
            s = (a * fb * fc) / ((fa - fb) * (fa - fc)) +
                (b * fa * fc) / ((fb - fa) * (fb - fc)) +
                (c * fa * fb) / ((fc - fa) * (fc - fb));
        } else {
            // Secant method
            s = b - fb * (b - a) / (fb - fa);
        }

        // Conditions to fall back to bisection
        if (((s < (3.0 * a + b) / 4.0) || (s > b)) ||
            (mflag && (std::abs(s - b) >= std::abs(b - c) / 2.0)) ||
            (!mflag && (std::abs(s - b) >= std::abs(c - d) / 2.0)) ||
            (mflag && (std::abs(b - c) < tol)) ||
            (!mflag && (std::abs(c - d) < tol))) {
            s = (a + b) / 2.0;
            mflag = true;
        } else {
            mflag = false;
        }

        double fs = f(s);
        d = c;
        c = b;
        fc = fb;

        if (fa * fs < 0) {
            b = s;
            fb = fs;
        } else {
            a = s;
            fa = fs;
        }

        if (std::abs(fa) < std::abs(fb)) {
            std::swap(a, b);
            std::swap(fa, fb);
        }
    }
    return b;
}

/**
 * @brief THEOREM: Brent's Method for 1D minimization.
 * Uses parabolic interpolation and golden section search.
 */
inline double brent_minimize(std::function<double(double)> f, double a, double b, double tol = 1e-12, int max_iter = 100) {
    const double c = (3.0 - std::sqrt(5.0)) / 2.0;
    double x = a + c * (b - a);
    double w = x;
    double v = x;
    double u, fx, fw, fv, fu;
    double d = 0, e = 0;

    fx = f(x);
    fw = fx;
    fv = fx;

    for (int i = 0; i < max_iter; ++i) {
        double mid = (a + b) / 2.0;
        double tol1 = tol * std::abs(x) + tol / 10.0;
        double tol2 = 2.0 * tol1;

        if (std::abs(x - mid) <= (tol2 - (b - a) / 2.0)) return x;

        if (std::abs(e) > tol1) {
            // Parabolic fit
            double r = (x - w) * (fx - fv);
            double q = (x - v) * (fx - fw);
            double p = (x - v) * q - (x - w) * r;
            q = 2.0 * (q - r);
            if (q > 0.0) p = -p;
            q = std::abs(q);
            double etemp = e;
            e = d;

            if (std::abs(p) >= std::abs(0.5 * q * etemp) || p <= q * (a - x) || p >= q * (b - x)) {
                e = (x >= mid) ? a - x : b - x;
                d = c * e;
            } else {
                d = p / q;
                u = x + d;
                if (u - a < tol2 || b - u < tol2) d = (mid - x >= 0) ? std::abs(tol1) : -std::abs(tol1);
            }
        } else {
            e = (x >= mid) ? a - x : b - x;
            d = c * e;
        }

        u = x + d;
        fu = f(u);

        if (fu <= fx) {
            if (u >= x) a = x; else b = x;
            v = w; fv = fw;
            w = x; fw = fx;
            x = u; fx = fu;
        } else {
            if (u < x) a = u; else b = u;
            if (fu <= fw || w == x) {
                v = w; fv = fw;
                w = u; fw = fu;
            } else if (fu <= fv || v == x || v == w) {
                v = u; fv = fu;
            }
        }
    }
    return x;
}

/**
 * @brief THEOREM: Newton-Raphson with bisection fallback (Safe Newton).
 */
inline double newton_safe(std::function<double(double)> f, std::function<double(double)> df, 
                         double a, double b, double tol = 1e-12, int max_iter = 100) {
    double x = (a + b) / 2.0;
    double fl = f(a);
    double fh = f(b);
    double fx = f(x);

    if (std::abs(fl) < tol) return a;
    if (std::abs(fh) < tol) return b;
    if (std::abs(fx) < tol) return x;
    if (fl * fh > 0) throw std::runtime_error("newton_safe: root not bracketed");

    for (int i = 0; i < max_iter; ++i) {
        fx = f(x);
        double dfx = df(x);

        // If Newton step is out of bounds or moving too slowly, bisect
        if (std::abs(dfx) < tol
            || (((x - b) * dfx - fx) * ((x - a) * dfx - fx) > 0.0)
            || (std::abs(2.0 * fx) > std::abs((b - a) * dfx))) {
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
 * @brief THEOREM: Interval scanning for roots.
 * Scans [a, b] with step dt to find all sign changes, then refines each with brent_root.
 */
inline std::vector<double> find_roots(std::function<double(double)> f, double a, double b, double dt, double tol = 1e-12) {
    std::vector<double> roots;
    double x1 = a;
    double y1 = f(x1);

    while (x1 < b) {
        double x2 = std::min(x1 + dt, b);
        double y2 = f(x2);

        if (y1 * y2 <= 0.0) {
            // Sign change detected, refine with Brent's method
            roots.push_back(brent_root(f, x1, x2, tol));
        }

        x1 = x2;
        y1 = y2;
    }
    return roots;
}

/**
 * @brief THEOREM: Interval scanning for extrema (Min/Max).
 * Scans [a, b] for derivative sign changes, then refines with brent_minimize.
 * If df is not provided, it uses a 3-point sign-change check.
 */
inline std::vector<double> find_extrema(std::function<double(double)> f, double a, double b, double dt, double tol = 1e-12) {
    std::vector<double> extrema;
    double x1 = a;
    double x2 = a + dt;
    double x3 = a + 2.0 * dt;

    if (x3 > b) return extrema;

    double f1 = f(x1);
    double f2 = f(x2);
    double f3;

    while (x3 <= b) {
        f3 = f(x3);

        // Check if f2 is a local min or max
        if ((f2 < f1 && f2 < f3) || (f2 > f1 && f2 > f3)) {
            extrema.push_back(brent_minimize(f, x1, x3, tol));
        }

        x1 = x2; f1 = f2;
        x2 = x3; f2 = f3;
        x3 += dt;
    }
    return extrema;
}

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_SOLVERS_HPP
