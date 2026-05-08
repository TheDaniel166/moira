#ifndef MOIRA_NATIVE_EVALUATORS_HPP
#define MOIRA_NATIVE_EVALUATORS_HPP

#include <vector>
#include <memory>
#include "interpolation.hpp"
#include "sidereal.hpp"

namespace moira {
namespace native {

/**
 * @brief ABSTRACT BASE: A native ephemeris evaluator with caching.
 */
class IEvaluator {
protected:
    mutable double last_jd = -1.0;
    mutable double last_result[6];

public:
    virtual ~IEvaluator() = default;
    
    /**
     * @brief THEOREM: Single JD evaluation with 1-element cache.
     */
    void evaluate(double jd, double* result) const {
        if (jd == last_jd) {
            for (int i = 0; i < 6; ++i) result[i] = last_result[i];
            return;
        }
        compute(jd, result);
        last_jd = jd;
        for (int i = 0; i < 6; ++i) last_result[i] = result[i];
    }

    /**
     * @brief THEOREM: Bulk evaluation of multiple JDs.
     */
    virtual void evaluate_batch(const double* jds, size_t count, double* results) const {
        for (size_t i = 0; i < count; ++i) {
            evaluate(jds[i], results + i * 6);
        }
    }

    virtual void compute(double jd, double* result) const = 0;
};

/**
 * @brief THEOREM: Chebyshev Segment Evaluator (Type 2/3).
 */
class ChebyshevEvaluator : public IEvaluator {
public:
    double init;
    double intlen;
    size_t record_count;
    size_t component_count;
    size_t coefficient_count;
    std::vector<double> coefficients;

    ChebyshevEvaluator(double init, double intlen, size_t rec_count, size_t comp_count, size_t coeff_count, std::vector<double> coeffs)
        : init(init), intlen(intlen), record_count(rec_count), component_count(comp_count), coefficient_count(coeff_count), coefficients(std::move(coeffs)) {}

    void compute(double jd, double* result) const override {
        // JPL SPK Type 2/3 uses seconds since J2000.0.
        // We convert JD to seconds to match the domain of the polynomial.
        double t_sec = (jd - 2451545.0) * 86400.0;
        double d_t = t_sec - init;
        size_t record_index = static_cast<size_t>(std::floor(d_t / intlen));
        if (record_index >= record_count) record_index = record_count - 1;

        double s = (d_t - (static_cast<double>(record_index) * intlen)) / intlen;
        s = 2.0 * s - 1.0;

        const double* ptr = coefficients.data() + record_index * component_count * coefficient_count;
        spk_chebyshev_record_avx2(ptr, coefficient_count, component_count, s, result, 1, coefficient_count);
    }
};

/**
 * @brief Native-owned SPK type-2/type-3 segment evaluator.
 *
 * Keeps the coefficient payload resident in native memory so Python does not
 * have to materialize a NumPy tensor for first-use segment evaluation.
 */
class SpkSegmentEvaluator {
public:
    int32_t data_type;
    bool coefficients_in_file_order;
    double init;
    double intlen;
    size_t record_count;
    size_t component_count;
    size_t coefficient_count;
    std::vector<double> coefficients;

    SpkSegmentEvaluator(
        int32_t data_type,
        bool coefficients_in_file_order,
        double init,
        double intlen,
        size_t rec_count,
        size_t comp_count,
        size_t coeff_count,
        std::vector<double> coeffs
    )
        : data_type(data_type),
          coefficients_in_file_order(coefficients_in_file_order),
          init(init),
          intlen(intlen),
          record_count(rec_count),
          component_count(comp_count),
          coefficient_count(coeff_count),
          coefficients(std::move(coeffs)) {}

    void position(double jd, double* result) const {
        if (data_type == 2) {
            const double* ptr = record_ptr(jd);
            const double s = normalized_time(jd);
            if (coefficients_in_file_order) {
                spk_chebyshev_record_avx2_reverse(ptr, coefficient_count, component_count, s, result, 1, coefficient_count);
            } else {
                spk_chebyshev_record_avx2(ptr, coefficient_count, component_count, s, result, 1, coefficient_count);
            }
            return;
        }

        double full_state[6];
        evaluate_type3(jd, full_state);
        result[0] = full_state[0];
        result[1] = full_state[1];
        result[2] = full_state[2];
    }

    void position_and_velocity(double jd, double* position_out, double* velocity_out) const {
        if (data_type == 2) {
            const double* ptr = record_ptr(jd);
            const double s = normalized_time(jd);
            const double derivative_scale = 2.0 * 86400.0 / intlen;
            if (coefficients_in_file_order) {
                spk_chebyshev_record_with_derivative_inplace_reverse(
                    ptr,
                    coefficient_count,
                    component_count,
                    s,
                    position_out,
                    velocity_out,
                    1,
                    coefficient_count
                );
            } else {
                spk_chebyshev_record_with_derivative_inplace(
                    ptr,
                    coefficient_count,
                    component_count,
                    s,
                    position_out,
                    velocity_out,
                    1,
                    coefficient_count
                );
            }
            for (size_t i = 0; i < 3; ++i) {
                velocity_out[i] *= derivative_scale;
            }
            return;
        }

        double full_state[6];
        evaluate_type3(jd, full_state);
        position_out[0] = full_state[0];
        position_out[1] = full_state[1];
        position_out[2] = full_state[2];
        velocity_out[0] = full_state[3];
        velocity_out[1] = full_state[4];
        velocity_out[2] = full_state[5];
    }

private:
    size_t record_index(double jd) const {
        double t_sec = (jd - 2451545.0) * 86400.0;
        double d_t = t_sec - init;
        size_t index = static_cast<size_t>(std::floor(d_t / intlen));
        if (index >= record_count) {
            index = record_count - 1;
        }
        return index;
    }

    double normalized_time(double jd) const {
        double t_sec = (jd - 2451545.0) * 86400.0;
        double d_t = t_sec - init;
        size_t index = record_index(jd);
        double s = (d_t - (static_cast<double>(index) * intlen)) / intlen;
        return 2.0 * s - 1.0;
    }

    const double* record_ptr(double jd) const {
        return coefficients.data() + record_index(jd) * component_count * coefficient_count;
    }

    void evaluate_type3(double jd, double* result) const {
        const double* ptr = record_ptr(jd);
        const double s = normalized_time(jd);
        if (coefficients_in_file_order) {
            spk_chebyshev_record_avx2_reverse(ptr, coefficient_count, component_count, s, result, 1, coefficient_count);
        } else {
            spk_chebyshev_record_avx2(ptr, coefficient_count, component_count, s, result, 1, coefficient_count);
        }
    }
};

/**
 * @brief THEOREM: Lagrange Segment Evaluator (Type 13).
 */
class LagrangeEvaluator : public IEvaluator {
public:
    std::vector<double> epochs;
    std::vector<double> states;
    size_t window_size;

    LagrangeEvaluator(std::vector<double> epochs, std::vector<double> states, size_t window_size)
        : epochs(std::move(epochs)), states(std::move(states)), window_size(window_size) {}

    void compute(double jd, double* result) const override {
        spk_type13_record_inplace(epochs.data(), states.data(), epochs.size(), window_size, jd, result);
    }
};

/**
 * @brief THEOREM: Difference Evaluator (Target - Observer).
 */
class RelativeEvaluator : public IEvaluator {
public:
    std::shared_ptr<IEvaluator> target;
    std::shared_ptr<IEvaluator> observer;

    RelativeEvaluator(std::shared_ptr<IEvaluator> t, std::shared_ptr<IEvaluator> o)
        : target(std::move(t)), observer(std::move(o)) {}

    void compute(double jd, double* result) const override {
        double r_t[6], r_o[6];
        target->evaluate(jd, r_t);
        observer->evaluate(jd, r_o);
        for (int i = 0; i < 6; ++i) result[i] = r_t[i] - r_o[i];
    }
};

/**
 * @brief THEOREM: Topocentric Observer Evaluator.
 * Transforms geocentric ICRF positions to topocentric observer positions.
 */
class TopocentricEvaluator : public IEvaluator {
public:
    std::shared_ptr<IEvaluator> target;
    double lat, lon, alt;

    TopocentricEvaluator(std::shared_ptr<IEvaluator> t, double lat, double lon, double alt)
        : target(std::move(t)), lat(lat), lon(lon), alt(alt) {}

    void compute(double jd_ut, double* result) const override {
        // 1. Get geocentric position
        double r_geo[6];
        target->evaluate(jd_ut, r_geo);

        // 2. Compute Observer position in ITRF
        // WGS84 Constants
        double a = 6378.137;
        double f = 1.0 / 298.257223563;
        double e2 = f * (2.0 - f);
        
        double phi = deg_to_rad(lat);
        double lambda = deg_to_rad(lon);
        double h = alt / 1000.0;
        
        double sin_phi = std::sin(phi);
        double N = a / std::sqrt(1.0 - e2 * sin_phi * sin_phi);
        
        Vec3 p_itrf = {
            (N + h) * std::cos(phi) * std::cos(lambda),
            (N + h) * std::cos(phi) * std::sin(lambda),
            (N * (1.0 - e2) + h) * sin_phi
        };

        // 3. Rotate ITRF to ICRF using ERA/GAST
        double gmst = greenwich_mean_sidereal_time(jd_ut);
        double theta = deg_to_rad(gmst);
        double cos_theta = std::cos(theta);
        double sin_theta = std::sin(theta);
        
        Vec3 p_icrf = {
            p_itrf[0] * cos_theta - p_itrf[1] * sin_theta,
            p_itrf[0] * sin_theta + p_itrf[1] * cos_theta,
            p_itrf[2]
        };

        // 4. Relative position (Target - Observer)
        result[0] = r_geo[0] - p_icrf[0];
        result[1] = r_geo[1] - p_icrf[1];
        result[2] = r_geo[2] - p_icrf[2];
        
        // Velocity (Approximate Earth rotation velocity)
        double omega = 7.292115e-5 * 86400.0; // rad/day
        Vec3 v_icrf = {
            -p_icrf[1] * omega,
            p_icrf[0] * omega,
            0.0
        };
        
        result[3] = r_geo[3] - v_icrf[0];
        result[4] = r_geo[4] - v_icrf[1];
        result[5] = r_geo[5] - v_icrf[2];
    }
};

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_EVALUATORS_HPP
