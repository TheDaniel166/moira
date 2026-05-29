#ifndef MOIRA_NATIVE_EVALUATORS_HPP
#define MOIRA_NATIVE_EVALUATORS_HPP

#include <cstdint>
#include <mutex>
#include <vector>
#include <memory>
#include "interpolation.hpp"
#include "sidereal.hpp"
#include "math_utils.hpp"
#include "geometry.hpp"

namespace moira {
namespace native {

/**
 * @brief ABSTRACT BASE: A native ephemeris evaluator with caching.
 */
class IEvaluator {
protected:
    mutable double last_jd = -1.0;
    mutable double last_result[6];
    mutable std::mutex cache_mutex;

public:
    virtual ~IEvaluator() = default;
    
    /**
     * @brief THEOREM: Single JD evaluation with 1-element cache.
     */
    void evaluate(double jd, double* result) const {
        {
            std::lock_guard<std::mutex> lock(cache_mutex);
            if (jd == last_jd) {
                for (int i = 0; i < 6; ++i) result[i] = last_result[i];
                return;
            }
        }

        compute(jd, result);

        {
            std::lock_guard<std::mutex> lock(cache_mutex);
            for (int i = 0; i < 6; ++i) last_result[i] = result[i];
            last_jd = jd;
        }
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
 * @brief Native-owned SPK segment evaluator for supported type-2/type-3/type-13 payloads.
 *
 * Keeps the segment payload resident in native memory so Python does not have
 * to materialize large intermediate structures for first-use segment evaluation.
 */
class SpkSegmentEvaluator : public IEvaluator {
public:
    int32_t data_type;
    bool coefficients_in_file_order;
    double init;
    double intlen;
    size_t record_count;
    size_t component_count;
    size_t coefficient_count;
    std::vector<double> coefficients;
    std::vector<double> type13_epochs_jd;
    std::vector<double> type13_states;
    size_t type13_window_size;

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
          coefficients(std::move(coeffs)),
          type13_window_size(0) {}

    SpkSegmentEvaluator(
        std::vector<double> epochs_jd,
        std::vector<double> states,
        size_t window_size
    )
        : data_type(13),
          coefficients_in_file_order(false),
          init(0.0),
          intlen(0.0),
          record_count(0),
          component_count(0),
          coefficient_count(0),
          type13_epochs_jd(std::move(epochs_jd)),
          type13_states(std::move(states)),
          type13_window_size(window_size) {}

    void compute(double jd, double* result) const override {
        double p[3], v[3];
        position_and_velocity(jd, p, v);
        result[0] = p[0]; result[1] = p[1]; result[2] = p[2];
        result[3] = v[0]; result[4] = v[1]; result[5] = v[2];
    }

    void position(double jd, double* result) const {
        position(jd, 0.0, result);
    }

    void position(double jd, double jd2, double* result) const {
        if (data_type == 13) {
            double full_state[6];
            spk_type13_record_inplace(
                type13_epochs_jd.data(),
                type13_states.data(),
                type13_epochs_jd.size(),
                type13_window_size,
                jd + jd2,
                full_state
            );
            result[0] = full_state[0];
            result[1] = full_state[1];
            result[2] = full_state[2];
            return;
        }

        if (data_type == 2) {
            const double* ptr = record_ptr(jd, jd2);
            const double s = normalized_time(jd, jd2);
            if (coefficients_in_file_order) {
                spk_chebyshev_record_avx2_reverse(ptr, coefficient_count, component_count, s, result, 1, coefficient_count);
            } else {
                spk_chebyshev_record_avx2(ptr, coefficient_count, component_count, s, result, 1, coefficient_count);
            }
            return;
        }

        double full_state[6];
        evaluate_type3(jd, jd2, full_state);
        result[0] = full_state[0];
        result[1] = full_state[1];
        result[2] = full_state[2];
    }

    void position_and_velocity(double jd, double* position_out, double* velocity_out) const {
        position_and_velocity(jd, 0.0, position_out, velocity_out);
    }

    void position_and_velocity(double jd, double jd2, double* position_out, double* velocity_out) const {
        if (data_type == 13) {
            double full_state[6];
            spk_type13_record_inplace(
                type13_epochs_jd.data(),
                type13_states.data(),
                type13_epochs_jd.size(),
                type13_window_size,
                jd + jd2,
                full_state
            );
            position_out[0] = full_state[0];
            position_out[1] = full_state[1];
            position_out[2] = full_state[2];
            velocity_out[0] = full_state[3];
            velocity_out[1] = full_state[4];
            velocity_out[2] = full_state[5];
            return;
        }

        if (data_type == 2) {
            const double* ptr = record_ptr(jd, jd2);
            const double s = normalized_time(jd, jd2);
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
        evaluate_type3(jd, jd2, full_state);
        position_out[0] = full_state[0];
        position_out[1] = full_state[1];
        position_out[2] = full_state[2];
        velocity_out[0] = full_state[3];
        velocity_out[1] = full_state[4];
        velocity_out[2] = full_state[5];
    }

private:
    std::pair<size_t, double> epoch_record_and_offset(double jd, double jd2) const {
        const double offset_seconds = (jd - 2451545.0) * 86400.0 - init;
        double index1;
        double offset1;
        {
            const double quotient = std::floor(offset_seconds / intlen);
            index1 = quotient;
            offset1 = offset_seconds - quotient * intlen;
        }

        double index2;
        double offset2;
        {
            const double split_seconds = jd2 * 86400.0;
            const double quotient = std::floor(split_seconds / intlen);
            index2 = quotient;
            offset2 = split_seconds - quotient * intlen;
        }

        const double combined_offset = offset1 + offset2;
        const double index3 = std::floor(combined_offset / intlen);
        double offset = combined_offset - index3 * intlen;
        int64_t index = static_cast<int64_t>(index1 + index2 + index3);
        if (index < 0) {
            index = 0;
            offset = 0.0;
        } else if (static_cast<size_t>(index) > record_count) {
            index = static_cast<int64_t>(record_count - 1);
            offset = intlen;
        } else if (static_cast<size_t>(index) == record_count) {
            index -= 1;
            offset += intlen;
        }

        return {static_cast<size_t>(index), offset};
    }

    double normalized_time(double jd, double jd2) const {
        const auto [index, offset] = epoch_record_and_offset(jd, jd2);
        (void)index;
        double s = offset / intlen;
        return 2.0 * s - 1.0;
    }

    const double* record_ptr(double jd, double jd2) const {
        const auto [index, offset] = epoch_record_and_offset(jd, jd2);
        (void)offset;
        return coefficients.data() + index * component_count * coefficient_count;
    }

    void evaluate_type3(double jd, double jd2, double* result) const {
        const double* ptr = record_ptr(jd, jd2);
        const double s = normalized_time(jd, jd2);
        if (coefficients_in_file_order) {
            spk_chebyshev_record_avx2_reverse(ptr, coefficient_count, component_count, s, result, 1, coefficient_count);
        } else {
            spk_chebyshev_record_avx2(ptr, coefficient_count, component_count, s, result, 1, coefficient_count);
        }
    }
};

/**
 * @brief THEOREM: Hermite Segment Evaluator (Type 13).
 */
class Type13Evaluator : public IEvaluator {
public:
    std::vector<double> epochs;
    std::vector<double> states;
    size_t window_size;

    Type13Evaluator(std::vector<double> epochs, std::vector<double> states, size_t window_size)
        : epochs(std::move(epochs)), states(std::move(states)), window_size(window_size) {}

    void compute(double jd, double* result) const override {
        spk_type13_record_inplace(epochs.data(), states.data(), epochs.size(), window_size, jd, result);
    }
};

/**
 * @brief THEOREM: Fixed Star Evaluator.
 * Propagates ICRS unit vector with proper motion, parallax, and radial velocity.
 */
class FixedStarEvaluator : public IEvaluator {
public:
    double ra0_rad, dec0_rad;
    double pmra_rad_yr, pmdec_rad_yr;
    double parallax_mas, rv_km_s;
    Vec3 p_hat, east_hat, north_hat;

    FixedStarEvaluator(double ra_deg, double dec_deg, double pmra_mas, double pmdec_mas, double parallax, double rv)
        : ra0_rad(deg_to_rad(ra_deg)), dec0_rad(deg_to_rad(dec_deg)),
          parallax_mas(parallax), rv_km_s(rv) {
        
        double cos_dec = std::cos(dec0_rad);
        double sin_dec = std::sin(dec0_rad);
        double cos_ra = std::cos(ra0_rad);
        double sin_ra = std::sin(ra0_rad);

        p_hat = {cos_dec * cos_ra, cos_dec * sin_ra, sin_dec};
        east_hat = {-sin_ra, cos_ra, 0.0};
        north_hat = {-sin_dec * cos_ra, -sin_dec * sin_ra, cos_dec};

        // pmra_mas is mu_alpha* (includes cos_dec factor)
        pmra_rad_yr = pmra_mas * ARCSEC2RAD / 1000.0;
        pmdec_rad_yr = pmdec_mas * ARCSEC2RAD / 1000.0;
    }

    void compute(double jd_tt, double* result) const override {
        double dt_yr = (jd_tt - 2451545.0) / 365.25;
        
        Vec3 v_tan = east_hat * pmra_rad_yr + north_hat * pmdec_rad_yr;
        Vec3 propagated;

        if (parallax_mas > 1e-9) {
            double dist_au = 1000.0 / parallax_mas * (1.0 / ARCSEC2RAD);
            double dist_km = dist_au * KM_PER_AU;
            
            // km/s to km/yr
            double rv_km_yr = rv_km_s * (365.25 * 86400.0);
            
            propagated = (p_hat * dist_km) + (v_tan * dist_km + p_hat * rv_km_yr) * dt_yr;
        } else {
            // Effectively infinity: 1 million light years in KM
            double dist_km = 1e6 * 9.4607e12; 
            propagated = (p_hat + v_tan * dt_yr) * dist_km;
        }

        result[0] = propagated[0];
        result[1] = propagated[1];
        result[2] = propagated[2];
        result[3] = result[4] = result[5] = 0.0;
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
 * @brief THEOREM: Sum Evaluator (A + B).
 */
class SumEvaluator : public IEvaluator {
public:
    std::shared_ptr<IEvaluator> a;
    std::shared_ptr<IEvaluator> b;

    SumEvaluator(std::shared_ptr<IEvaluator> a, std::shared_ptr<IEvaluator> b)
        : a(std::move(a)), b(std::move(b)) {}

    void compute(double jd, double* result) const override {
        double r_a[6], r_b[6];
        a->evaluate(jd, r_a);
        b->evaluate(jd, r_b);
        for (int i = 0; i < 6; ++i) result[i] = r_a[i] + r_b[i];
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
