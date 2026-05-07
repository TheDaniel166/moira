#ifndef MOIRA_NATIVE_GEOMETRY_HPP
#define MOIRA_NATIVE_GEOMETRY_HPP

#include <array>
#include <cmath>
#include <stdexcept>

namespace moira {
namespace native {

/**
 * @brief THEOREM: A 3-dimensional Euclidean vector.
 * Mirror of moira.coordinates.Vec3.
 */
struct Vec3 {
    std::array<double, 3> data;

    Vec3(double x = 0.0, double y = 0.0, double z = 0.0) : data{x, y, z} {}

    double& operator[](size_t i) { return data[i]; }
    const double& operator[](size_t i) const { return data[i]; }

    static Vec3 add(const Vec3& a, const Vec3& b) {
        return {a[0] + b[0], a[1] + b[1], a[2] + b[2]};
    }

    static Vec3 sub(const Vec3& a, const Vec3& b) {
        return {a[0] - b[0], a[1] - b[1], a[2] - b[2]};
    }

    static Vec3 scale(const Vec3& a, double s) {
        return {a[0] * s, a[1] * s, a[2] * s};
    }

    static double dot(const Vec3& a, const Vec3& b) {
        return a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
    }

    Vec3 operator+(const Vec3& other) const { return {data[0] + other[0], data[1] + other[1], data[2] + other[2]}; }
    Vec3 operator-(const Vec3& other) const { return {data[0] - other[0], data[1] - other[1], data[2] - other[2]}; }
    Vec3 operator*(double s) const { return {data[0] * s, data[1] * s, data[2] * s}; }
    Vec3 operator/(double s) const { return {data[0] / s, data[1] / s, data[2] / s}; }
    double dot(const Vec3& other) const { return dot(*this, other); }


    static Vec3 cross(const Vec3& a, const Vec3& b) {
        return {
            a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0]
        };
    }

    double norm() const {
        return std::sqrt(data[0]*data[0] + data[1]*data[1] + data[2]*data[2]);
    }

    Vec3 unit() const {
        double n = norm();
        if (n == 0.0) {
            throw std::runtime_error("Vec3::unit: cannot normalise a zero vector");
        }
        return {data[0] / n, data[1] / n, data[2] / n};
    }

    static double angle_between(const Vec3& a, const Vec3& b) {
        double d = dot(a, b);
        double n = a.norm() * b.norm();
        if (n == 0.0) return 0.0;
        return std::acos(std::max(-1.0, std::min(1.0, d / n)));
    }

    static Vec3 project(const Vec3& a, const Vec3& b) {
        double d = dot(b, b);
        if (d == 0.0) return {0.0, 0.0, 0.0};
        return scale(b, dot(a, b) / d);
    }

    static Vec3 reject(const Vec3& a, const Vec3& b) {
        Vec3 p = project(a, b);
        return sub(a, p);
    }

    static Vec3 lerp(const Vec3& a, const Vec3& b, double t) {
        return add(scale(a, 1.0 - t), scale(b, t));
    }
};

/**
 * @brief THEOREM: A 3x3 rotation or transformation matrix.
 * Mirror of moira.coordinates.Mat3.
 */
struct Mat3 {
    std::array<std::array<double, 3>, 3> data;

    std::array<double, 3>& operator[](size_t i) { return data[i]; }
    const std::array<double, 3>& operator[](size_t i) const { return data[i]; }

    static Mat3 identity() {
        return {{{
            {1.0, 0.0, 0.0},
            {0.0, 1.0, 0.0},
            {0.0, 0.0, 1.0}
        }}};
    }

    static Vec3 mul(const Mat3& m, const Vec3& v) {
        return {
            m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2]
        };
    }

    static Mat3 mul(const Mat3& a, const Mat3& b) {
        Mat3 res;
        for (int i = 0; i < 3; ++i) {
            for (int j = 0; j < 3; ++j) {
                res[i][j] = a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j];
            }
        }
        return res;
    }

    static Mat3 compose(const Mat3& a, const Mat3& b) {
        return mul(a, b);
    }

    Mat3 transpose() const {
        return {{{
            {data[0][0], data[1][0], data[2][0]},
            {data[0][1], data[1][1], data[2][1]},
            {data[0][2], data[1][2], data[2][2]}
        }}};
    }

    double determinant() const {
        return data[0][0] * (data[1][1] * data[2][2] - data[1][2] * data[2][1])
             - data[0][1] * (data[1][0] * data[2][2] - data[1][2] * data[2][0])
             + data[0][2] * (data[1][0] * data[2][1] - data[1][1] * data[2][0]);
    }

    Mat3 inverse() const {
        double det = determinant();
        if (std::abs(det) < 1e-18) {
            throw std::runtime_error("Mat3::inverse: matrix is singular");
        }
        double inv_det = 1.0 / det;
        Mat3 res;
        res[0][0] = (data[1][1] * data[2][2] - data[1][2] * data[2][1]) * inv_det;
        res[0][1] = (data[0][2] * data[2][1] - data[0][1] * data[2][2]) * inv_det;
        res[0][2] = (data[0][1] * data[1][2] - data[0][2] * data[1][1]) * inv_det;
        res[1][0] = (data[1][2] * data[2][0] - data[1][0] * data[2][2]) * inv_det;
        res[1][1] = (data[0][0] * data[2][2] - data[0][2] * data[2][0]) * inv_det;
        res[1][2] = (data[1][0] * data[0][2] - data[0][0] * data[1][2]) * inv_det;
        res[2][0] = (data[1][0] * data[2][1] - data[1][1] * data[2][0]) * inv_det;
        res[2][1] = (data[2][0] * data[0][1] - data[0][0] * data[2][1]) * inv_det;
        res[2][2] = (data[0][0] * data[1][1] - data[1][0] * data[0][1]) * inv_det;
        return res;
    }

    bool is_orthonormal(double epsilon = 1e-12) const {
        Mat3 m_mt = mul(*this, this->transpose());
        Mat3 id = identity();
        for (int i = 0; i < 3; ++i) {
            for (int j = 0; j < 3; ++j) {
                if (std::abs(m_mt[i][j] - id[i][j]) > epsilon) return false;
            }
        }
        return true;
    }

    Mat3 orthonormalize() const {
        // Gram-Schmidt process
        Vec3 r0 = {data[0][0], data[0][1], data[0][2]};
        Vec3 r1 = {data[1][0], data[1][1], data[1][2]};
        Vec3 r2 = {data[2][0], data[2][1], data[2][2]};

        Vec3 u0 = r0.unit();
        Vec3 u1 = Vec3::sub(r1, Vec3::project(r1, u0)).unit();
        Vec3 u2 = Vec3::sub(Vec3::sub(r2, Vec3::project(r2, u0)), Vec3::project(r2, u1)).unit();

        return Mat3{{{
            {u0[0], u0[1], u0[2]},
            {u1[0], u1[1], u1[2]},
            {u2[0], u2[1], u2[2]}
        }}};
    }

    static Mat3 rot_x(double angle_rad) {
        double c = std::cos(angle_rad);
        double s = std::sin(angle_rad);
        return {{{
            {1.0, 0.0, 0.0},
            {0.0, c,   s},
            {0.0, -s,  c}
        }}};
    }

    static Mat3 rot_y(double angle_rad) {
        double c = std::cos(angle_rad);
        double s = std::sin(angle_rad);
        return {{{
            {c,   0.0, -s},
            {0.0, 1.0, 0.0},
            {s,   0.0, c}
        }}};
    }

    static Mat3 rot_z(double angle_rad) {
        double c = std::cos(angle_rad);
        double s = std::sin(angle_rad);
        return {{{
            {c,   s,   0.0},
            {-s,  c,   0.0},
            {0.0, 0.0, 1.0}
        }}};
    }
};

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_GEOMETRY_HPP
