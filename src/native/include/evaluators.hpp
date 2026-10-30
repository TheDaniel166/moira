#ifndef MOIRA_NATIVE_EVALUATORS_HPP
#define MOIRA_NATIVE_EVALUATORS_HPP

#include <algorithm>
#include <cstdint>
#include <cmath>
#include <list>
#include <mutex>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
#include <memory>
#include "interpolation.hpp"
#include "sidereal.hpp"
#include "math_utils.hpp"
#include "geometry.hpp"
#include "apparent_place.hpp"

namespace moira {
namespace native {

inline size_t checked_payload_size(
    size_t first,
    size_t second,
    size_t third,
    const char* surface
) {
    if (
        first == 0 || second == 0 || third == 0
        || first > std::numeric_limits<size_t>::max() / second
        || first * second > std::numeric_limits<size_t>::max() / third
    ) {
        throw std::invalid_argument(std::string(surface) + ": invalid payload dimensions");
    }
    return first * second * third;
}

inline size_t validate_chebyshev_dimensions(
    double init,
    double intlen,
    size_t record_count,
    size_t component_count,
    size_t coefficient_count,
    const char* surface
) {
    if (!std::isfinite(init) || !std::isfinite(intlen) || intlen <= 0.0) {
        throw std::invalid_argument(std::string(surface) + ": init and interval must be finite with interval > 0");
    }
    if (component_count > 6) {
        throw std::invalid_argument(std::string(surface) + ": component count exceeds the six-value result vessel");
    }
    return checked_payload_size(
        record_count, component_count, coefficient_count, surface
    );
}

inline void validate_chebyshev_payload(
    double init,
    double intlen,
    size_t record_count,
    size_t component_count,
    size_t coefficient_count,
    const std::vector<double>& coefficients,
    const char* surface
) {
    const size_t expected = validate_chebyshev_dimensions(
        init, intlen, record_count, component_count, coefficient_count, surface
    );
    if (coefficients.size() != expected) {
        throw std::invalid_argument(std::string(surface) + ": coefficient payload size does not match dimensions");
    }
    for (double value : coefficients) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(std::string(surface) + ": coefficients must be finite");
        }
    }
}

inline void validate_type13_payload(
    const std::vector<double>& epochs,
    const std::vector<double>& states,
    size_t window_size,
    const char* surface
) {
    if (epochs.empty() || window_size == 0 || window_size > epochs.size()) {
        throw std::invalid_argument(std::string(surface) + ": window must be in [1, epoch_count]");
    }
    if (epochs.size() > std::numeric_limits<size_t>::max() / 6 || states.size() != epochs.size() * 6) {
        throw std::invalid_argument(std::string(surface) + ": states must contain six rows per epoch");
    }
    for (size_t i = 0; i < epochs.size(); ++i) {
        if (!std::isfinite(epochs[i]) || (i > 0 && epochs[i] <= epochs[i - 1])) {
            throw std::invalid_argument(std::string(surface) + ": epochs must be finite and strictly increasing");
        }
    }
    for (double value : states) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(std::string(surface) + ": states must be finite");
        }
    }
}

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
        if (!std::isfinite(jd)) {
            throw std::invalid_argument("native evaluator epoch must be finite");
        }
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
 * @brief Convert a TT Julian day to the pinned naif0012 TDB coordinate.
 *
 * The argument of the NAIF DELTET periodic term is expressed in TDB seconds
 * from J2000, so this is a bounded fixed-point calculation.  This helper is
 * intentionally local to the evaluator substrate: it adapts TT-facing native
 * searches without changing the raw SPK polynomial clock.
 */
inline double naif0012_tt_to_tdb(double jd_tt) {
    if (!std::isfinite(jd_tt)) {
        throw std::invalid_argument("TT evaluator epoch must be finite");
    }
    constexpr double j2000 = 2451545.0;
    constexpr double seconds_per_day = 86400.0;
    constexpr double k_seconds = 1.657e-3;
    constexpr double eb = 1.671e-2;
    constexpr double m0 = 6.239996;
    constexpr double m1_per_second = 1.99096871e-7;
    constexpr int max_iterations = 8;
    constexpr double residual_seconds = 1e-15;

    double jd_tdb = jd_tt;
    double previous_offset = std::numeric_limits<double>::quiet_NaN();
    for (int iteration = 0; iteration < max_iterations; ++iteration) {
        const double seconds_from_j2000 = (jd_tdb - j2000) * seconds_per_day;
        const double mean_anomaly = std::remainder(
            m0 + m1_per_second * seconds_from_j2000,
            2.0 * 3.141592653589793238462643383279502884
        );
        const double eccentric_anomaly = mean_anomaly + eb * std::sin(mean_anomaly);
        const double offset_seconds = k_seconds * std::sin(eccentric_anomaly);
        jd_tdb = jd_tt + offset_seconds / seconds_per_day;
        if (
            std::isfinite(previous_offset)
            && std::abs(offset_seconds - previous_offset) <= residual_seconds
        ) {
            return jd_tdb;
        }
        previous_offset = offset_seconds;
    }
    throw std::runtime_error("NAIF LSK TT-to-TDB fixed-point iteration did not converge");
}

/**
 * @brief TT-facing adapter around one raw TDB ephemeris evaluator.
 */
class TtToTdbEvaluator : public IEvaluator {
public:
    explicit TtToTdbEvaluator(std::shared_ptr<IEvaluator> raw_tdb_evaluator)
        : raw_tdb_evaluator_(std::move(raw_tdb_evaluator)) {
        if (!raw_tdb_evaluator_) {
            throw std::invalid_argument("TtToTdbEvaluator requires a raw evaluator");
        }
    }

    void compute(double jd_tt, double* result) const override {
        raw_tdb_evaluator_->evaluate(naif0012_tt_to_tdb(jd_tt), result);
    }

    static double convert(double jd_tt) {
        return naif0012_tt_to_tdb(jd_tt);
    }

private:
    std::shared_ptr<IEvaluator> raw_tdb_evaluator_;
};

// Shared time reduction for native Chebyshev segment evaluators.
inline std::pair<int64_t, double> chebyshev_epoch_record(
    double jd, double jd2, double init, double intlen
) {
    if (!std::isfinite(jd) || !std::isfinite(jd2)) {
        throw std::invalid_argument("Chebyshev evaluator epoch must be finite");
    }
    // Preserve the binary64 ET contract, but carry the TwoDiff residual of
    // ET-INIT into record-local time. A long segment must not quantize ET.
    const double epoch_seconds = (jd - 2451545.0) * 86400.0;
    const double offset_seconds = epoch_seconds - init;
    const double virtual_init = epoch_seconds - offset_seconds;
    const double roundoff_seconds =
        (epoch_seconds - (offset_seconds + virtual_init)) + (virtual_init - init);
    const double index1 = std::floor(offset_seconds / intlen);
    const double offset1 = offset_seconds - index1 * intlen;
    const double split_seconds = jd2 * 86400.0;
    const double index2 = std::floor(split_seconds / intlen);
    const double offset2 = split_seconds - index2 * intlen;
    const double combined_offset = (offset1 + offset2) + roundoff_seconds;
    const double index3 = std::floor(combined_offset / intlen);
    return {
        static_cast<int64_t>(index1 + index2 + index3),
        combined_offset - index3 * intlen
    };
}

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
        : init(init), intlen(intlen), record_count(rec_count), component_count(comp_count), coefficient_count(coeff_count), coefficients(std::move(coeffs)) {
        validate_chebyshev_payload(
            init, intlen, record_count, component_count, coefficient_count,
            coefficients, "ChebyshevEvaluator"
        );
    }

    void compute(double jd, double* result) const override {
        auto [record_index, offset] = chebyshev_epoch_record(jd, 0.0, init, intlen);
        if (record_index < 0 || static_cast<size_t>(record_index) > record_count
            || (static_cast<size_t>(record_index) == record_count && offset > 0.0)) {
            throw std::invalid_argument("ChebyshevEvaluator epoch is outside payload coverage");
        }
        if (static_cast<size_t>(record_index) == record_count) {
            record_index -= 1;
            offset += intlen;
        }
        const double radius = 0.5 * intlen;
        const double s = (offset - radius) / radius;

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
/**
 * @brief Supplies one SPK Chebyshev record's coefficient words on demand.
 *
 * A record of an SPK type 2/3 segment is [MID, RADIUS, coefficients...], with
 * the coefficients component-major in ascending degree. ``read_record`` copies
 * the coefficient words (MID and RADIUS excluded) of record ``index`` in that
 * file order into ``out[0 .. component_count * coefficient_count)``. It is the
 * same word sequence a whole-segment payload read with
 * ``reverse_coefficients = false`` stores for that record.
 */
class ChebyshevRecordSource {
public:
    virtual ~ChebyshevRecordSource() = default;
    virtual void read_record(size_t index, double* out) const = 0;
};

class SpkSegmentEvaluator : public IEvaluator {
public:
    int32_t data_type;
    bool coefficients_in_file_order;
    double coverage_start_jd;
    double coverage_end_jd;
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
        double coverage_start_jd,
        double coverage_end_jd,
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
          coverage_start_jd(coverage_start_jd),
          coverage_end_jd(coverage_end_jd),
          init(init),
          intlen(intlen),
          record_count(rec_count),
          component_count(comp_count),
          coefficient_count(coeff_count),
          coefficients(std::move(coeffs)),
          type13_window_size(0) {
        if (
            !std::isfinite(coverage_start_jd) || !std::isfinite(coverage_end_jd)
            || coverage_start_jd > coverage_end_jd
            || (data_type != 2 && data_type != 3)
        ) {
            throw std::invalid_argument("SpkSegmentEvaluator: invalid descriptor metadata");
        }
        validate_chebyshev_payload(
            init, intlen, record_count, component_count, coefficient_count,
            coefficients, "SpkSegmentEvaluator"
        );
    }

    /**
     * Record-level Chebyshev evaluator. Coefficients are not preloaded: each
     * evaluation fetches the one record covering the epoch from ``source``
     * (file order) and keeps up to ``cache_limit`` recent records. Record
     * selection, normalized time and the Chebyshev arithmetic are the ones the
     * whole-segment evaluator uses, applied to the same words, so results are
     * identical. A non-finite coefficient is reported when its record is first
     * read rather than when the segment is opened.
     */
    SpkSegmentEvaluator(
        double coverage_start_jd,
        double coverage_end_jd,
        int32_t data_type,
        double init,
        double intlen,
        size_t rec_count,
        size_t comp_count,
        size_t coeff_count,
        std::shared_ptr<const ChebyshevRecordSource> source,
        size_t cache_limit
    )
        : data_type(data_type),
          coefficients_in_file_order(true),
          coverage_start_jd(coverage_start_jd),
          coverage_end_jd(coverage_end_jd),
          init(init),
          intlen(intlen),
          record_count(rec_count),
          component_count(comp_count),
          coefficient_count(coeff_count),
          type13_window_size(0),
          record_source_(std::move(source)),
          record_cache_limit_(std::max<size_t>(1, cache_limit)) {
        if (
            !std::isfinite(coverage_start_jd) || !std::isfinite(coverage_end_jd)
            || coverage_start_jd > coverage_end_jd
            || (data_type != 2 && data_type != 3)
        ) {
            throw std::invalid_argument("SpkSegmentEvaluator: invalid descriptor metadata");
        }
        if (!record_source_) {
            throw std::invalid_argument("SpkSegmentEvaluator: record source is required");
        }
        validate_chebyshev_dimensions(
            init, intlen, record_count, component_count, coefficient_count,
            "SpkSegmentEvaluator"
        );
    }

    bool record_level() const {
        return static_cast<bool>(record_source_);
    }

    size_t cached_record_count() const {
        std::lock_guard<std::mutex> lock(record_cache_mutex_);
        return record_cache_.size();
    }

    /**
     * Copy record ``index``'s coefficient words, component-major, in this
     * evaluator's storage order (file order when ``coefficients_in_file_order``).
     */
    void copy_record(size_t index, double* out) const {
        if (data_type != 2 && data_type != 3) {
            throw std::invalid_argument("Chebyshev records require an SPK type 2 or 3 segment");
        }
        if (index >= record_count) {
            throw std::invalid_argument("SPK evaluator record index is outside descriptor payload");
        }
        const size_t words = component_count * coefficient_count;
        if (record_source_) {
            load_record(index, out);
            return;
        }
        std::copy_n(coefficients.data() + index * words, words, out);
    }

    SpkSegmentEvaluator(
        double coverage_start_jd,
        double coverage_end_jd,
        std::vector<double> epochs_jd,
        std::vector<double> states,
        size_t window_size
    )
        : data_type(13),
          coefficients_in_file_order(false),
          coverage_start_jd(coverage_start_jd),
          coverage_end_jd(coverage_end_jd),
          init(0.0),
          intlen(0.0),
          record_count(0),
          component_count(0),
          coefficient_count(0),
          type13_epochs_jd(std::move(epochs_jd)),
          type13_states(std::move(states)),
          type13_window_size(window_size) {
        if (
            !std::isfinite(coverage_start_jd) || !std::isfinite(coverage_end_jd)
            || coverage_start_jd > coverage_end_jd
        ) {
            throw std::invalid_argument("SpkSegmentEvaluator: invalid type-13 descriptor coverage");
        }
        validate_type13_payload(
            type13_epochs_jd, type13_states, type13_window_size,
            "SpkSegmentEvaluator"
        );
    }

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
        validate_descriptor_epoch(jd, jd2);
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
            std::vector<double> scratch;
            const double* ptr = record_ptr(jd, jd2, scratch);
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
        validate_descriptor_epoch(jd, jd2);
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
            std::vector<double> scratch;
            const double* ptr = record_ptr(jd, jd2, scratch);
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
    void validate_descriptor_epoch(double jd, double jd2) const {
        const double epoch = jd + jd2;
        if (
            !std::isfinite(epoch)
            || epoch < coverage_start_jd
            || epoch > coverage_end_jd
        ) {
            throw std::invalid_argument(
                "SPK evaluator epoch is outside descriptor coverage"
            );
        }
    }

    std::pair<size_t, double> epoch_record_and_offset(double jd, double jd2) const {
        auto [index, offset] = chebyshev_epoch_record(jd, jd2, init, intlen);
        if (index < 0 || static_cast<size_t>(index) > record_count) {
            throw std::invalid_argument(
                "SPK evaluator record index is outside descriptor payload"
            );
        } else if (static_cast<size_t>(index) == record_count) {
            index -= 1;
            offset += intlen;
        }

        return {static_cast<size_t>(index), offset};
    }

    double normalized_time(double jd, double jd2) const {
        const auto [index, offset] = epoch_record_and_offset(jd, jd2);
        (void)index;
        const double radius = 0.5 * intlen;
        return (offset - radius) / radius;
    }

    const double* record_ptr(double jd, double jd2, std::vector<double>& scratch) const {
        const auto [index, offset] = epoch_record_and_offset(jd, jd2);
        (void)offset;
        const size_t words = component_count * coefficient_count;
        if (!record_source_) {
            return coefficients.data() + index * words;
        }
        scratch.resize(words);
        load_record(index, scratch.data());
        return scratch.data();
    }

    void load_record(size_t index, double* out) const {
        const size_t words = component_count * coefficient_count;
        {
            std::lock_guard<std::mutex> lock(record_cache_mutex_);
            auto it = record_cache_.find(index);
            if (it != record_cache_.end()) {
                record_lru_.splice(record_lru_.begin(), record_lru_, it->second.second);
                std::copy_n(it->second.first.data(), words, out);
                return;
            }
        }
        std::vector<double> record(words);
        record_source_->read_record(index, record.data());
        for (double value : record) {
            if (!std::isfinite(value)) {
                throw std::invalid_argument("SpkSegmentEvaluator: coefficients must be finite");
            }
        }
        std::copy_n(record.data(), words, out);
        std::lock_guard<std::mutex> lock(record_cache_mutex_);
        if (record_cache_.find(index) != record_cache_.end()) {
            return;
        }
        record_lru_.push_front(index);
        record_cache_.emplace(index, std::make_pair(std::move(record), record_lru_.begin()));
        while (record_cache_.size() > record_cache_limit_) {
            record_cache_.erase(record_lru_.back());
            record_lru_.pop_back();
        }
    }

    std::shared_ptr<const ChebyshevRecordSource> record_source_;
    size_t record_cache_limit_ = 0;
    mutable std::mutex record_cache_mutex_;
    mutable std::list<size_t> record_lru_;
    mutable std::unordered_map<size_t, std::pair<std::vector<double>, std::list<size_t>::iterator>> record_cache_;

    void evaluate_type3(double jd, double jd2, double* result) const {
        std::vector<double> scratch;
        const double* ptr = record_ptr(jd, jd2, scratch);
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
        : epochs(std::move(epochs)), states(std::move(states)), window_size(window_size) {
        validate_type13_payload(epochs, states, window_size, "Type13Evaluator");
    }

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
    // Reference epoch of the catalog astrometry, TDB Julian date.
    double ref_epoch_jd;
    Vec3 p_hat, east_hat, north_hat;

    FixedStarEvaluator(double ra_deg, double dec_deg, double pmra_mas, double pmdec_mas, double parallax, double rv,
                       double ref_epoch = 2451545.0)
        : ra0_rad(deg_to_rad(ra_deg)), dec0_rad(deg_to_rad(dec_deg)),
          parallax_mas(parallax), rv_km_s(rv), ref_epoch_jd(ref_epoch) {
        
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
        double dt_yr = (jd_tt - ref_epoch_jd) / 365.25;

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
 * @brief THEOREM: Apparent geocentric fixed star.
 *
 * Stage 2 of the fixed-star pipeline (FIXED_STARS_BACKEND_STANDARD.md,
 * Section 2), mirroring moira.stars._earth_based_effects: annual parallax
 * (barycentric star minus Earth's barycentric position), light deflection by
 * the Sun and, when given, Jupiter and Saturn, then annual aberration from
 * Earth's barycentric velocity. The output is the geocentric ICRS vector in
 * km; velocity slots are zero.
 */
class ApparentStarEvaluator : public IEvaluator {
public:
    std::shared_ptr<IEvaluator> star_ssb;
    std::shared_ptr<IEvaluator> earth_ssb;
    std::shared_ptr<IEvaluator> sun_ssb;
    std::shared_ptr<IEvaluator> jupiter_ssb;
    std::shared_ptr<IEvaluator> saturn_ssb;

    ApparentStarEvaluator(std::shared_ptr<IEvaluator> star,
                          std::shared_ptr<IEvaluator> earth,
                          std::shared_ptr<IEvaluator> sun,
                          std::shared_ptr<IEvaluator> jupiter = nullptr,
                          std::shared_ptr<IEvaluator> saturn = nullptr)
        : star_ssb(std::move(star)), earth_ssb(std::move(earth)), sun_ssb(std::move(sun)),
          jupiter_ssb(std::move(jupiter)), saturn_ssb(std::move(saturn)) {
        if (!star_ssb || !earth_ssb || !sun_ssb) {
            throw std::invalid_argument("ApparentStarEvaluator requires star, Earth and Sun evaluators");
        }
    }

    void compute(double jd_tt, double* result) const override {
        double star[6], earth[6], body[6];
        star_ssb->evaluate(jd_tt, star);
        earth_ssb->evaluate(jd_tt, earth);
        const Vec3 earth_pos{earth[0], earth[1], earth[2]};
        const Vec3 earth_vel{earth[3], earth[4], earth[5]};
        Vec3 geo{star[0] - earth_pos[0], star[1] - earth_pos[1], star[2] - earth_pos[2]};

        std::vector<std::pair<Vec3, double>> deflectors;
        deflectors.reserve(3);
        sun_ssb->evaluate(jd_tt, body);
        deflectors.emplace_back(Vec3{body[0] - earth_pos[0], body[1] - earth_pos[1], body[2] - earth_pos[2]}, 2.95325008);
        if (jupiter_ssb) {
            jupiter_ssb->evaluate(jd_tt, body);
            deflectors.emplace_back(Vec3{body[0] - earth_pos[0], body[1] - earth_pos[1], body[2] - earth_pos[2]}, 0.00282);
        }
        if (saturn_ssb) {
            saturn_ssb->evaluate(jd_tt, body);
            deflectors.emplace_back(Vec3{body[0] - earth_pos[0], body[1] - earth_pos[1], body[2] - earth_pos[2]}, 0.000838);
        }
        geo = apparent_deflection(geo, deflectors);
        geo = apparent_aberration(geo, earth_vel);

        result[0] = geo[0];
        result[1] = geo[1];
        result[2] = geo[2];
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
 * @brief Sign-reversed evaluator used for reverse SPK route legs.
 */
class NegateEvaluator : public IEvaluator {
public:
    explicit NegateEvaluator(std::shared_ptr<IEvaluator> source)
        : source_(std::move(source)) {
        if (!source_) {
            throw std::invalid_argument("NegateEvaluator requires a source evaluator");
        }
    }

    void compute(double jd, double* result) const override {
        source_->evaluate(jd, result);
        for (int i = 0; i < 6; ++i) {
            result[i] = -result[i];
        }
    }

private:
    std::shared_ptr<IEvaluator> source_;
};

/**
 * @brief THEOREM: Topocentric Observer Evaluator.
 * Transforms geocentric ICRF positions to topocentric observer positions.
 */
class TopocentricEvaluator : public IEvaluator {
public:
    std::shared_ptr<IEvaluator> target;
    double lat, lon, alt;
    /// TT - UT1 in seconds.  The evaluator timeline is TT (like every sibling
    /// evaluator); Earth rotation needs the UT1 instant TT - delta_t.
    double delta_t;

    TopocentricEvaluator(std::shared_ptr<IEvaluator> t, double lat, double lon, double alt, double delta_t)
        : target(std::move(t)), lat(lat), lon(lon), alt(alt), delta_t(delta_t) {}

    void compute(double jd_tt, double* result) const override {
        // 1. Get geocentric position
        double r_geo[6];
        target->evaluate(jd_tt, r_geo);
        const double jd_ut = jd_tt - delta_t / 86400.0;

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
        double gmst = greenwich_mean_sidereal_time(jd_ut, jd_tt);
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
