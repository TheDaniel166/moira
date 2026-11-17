#include "eclipse_strict_snapshot.hpp"

#include <cfenv>
#include <cfloat>
#include <cmath>
#include <limits>
#include <stdexcept>

#if defined(_MSC_VER)
#include <float.h>
#endif

#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#define MOIRA_ECLIPSE_X86_64 1
#endif

namespace moira {
namespace native {
namespace {

constexpr const char* contract = "moira_eclipse_scalar_snapshot_binary64_rn_gradual_v1";

void require_strict_snapshot_environment() {
#if !defined(MOIRA_ECLIPSE_STRICT_SNAPSHOT_BUILD) || !defined(MOIRA_ECLIPSE_X86_64) || defined(__FAST_MATH__) || defined(_M_FP_FAST)
    throw std::invalid_argument("eclipse_snapshot_unsupported_build_or_architecture");
#elif defined(_MSC_VER) && !defined(_M_FP_STRICT)
    throw std::invalid_argument("eclipse_snapshot_unattested_msvc_fp_mode");
#else
    if (!std::numeric_limits<double>::is_iec559 || std::numeric_limits<double>::radix != 2 ||
        std::numeric_limits<double>::digits != 53 || FLT_EVAL_METHOD != 0) {
        throw std::invalid_argument("eclipse_snapshot_requires_binary64_operations");
    }
    if (std::fegetround() != FE_TONEAREST) {
        throw std::invalid_argument("eclipse_snapshot_requires_round_to_nearest");
    }
    const unsigned int csr = _mm_getcsr();
    constexpr unsigned int rc = 0x6000u;
    constexpr unsigned int flush_or_denormals_zero = 0x8040u;
    constexpr unsigned int exception_masks = 0x1f80u;
    if ((csr & rc) != 0 || (csr & flush_or_denormals_zero) != 0) {
        throw std::invalid_argument("eclipse_snapshot_requires_nearest_and_gradual_underflow");
    }
    if ((csr & exception_masks) != exception_masks) {
        throw std::invalid_argument("eclipse_snapshot_requires_masked_exceptions");
    }
#if defined(_MSC_VER)
    unsigned int control = 0;
    if (_controlfp_s(&control, 0, 0) != 0 || (control & _MCW_RC) != _RC_NEAR ||
        (control & _MCW_EM) != _MCW_EM) {
        throw std::invalid_argument("eclipse_snapshot_requires_masked_nearest_x87");
    }
#elif defined(__GNUC__) || defined(__clang__)
    unsigned short control = 0;
    __asm__ volatile("fnstcw %0" : "=m"(control));
    if ((control & 0x0c00u) != 0 || (control & 0x003fu) != 0x003fu) {
        throw std::invalid_argument("eclipse_snapshot_requires_masked_nearest_x87");
    }
#else
    throw std::invalid_argument("eclipse_snapshot_unattested_compiler");
#endif
#endif
}

void require_finite(double value, const char* reason) {
    if (!std::isfinite(value)) throw std::invalid_argument(reason);
}

}  // namespace

const char* eclipse_strict_snapshot_build_contract() {
#if defined(MOIRA_ECLIPSE_STRICT_SNAPSHOT_BUILD) && defined(MOIRA_ECLIPSE_X86_64) && !defined(__FAST_MATH__) && !defined(_M_FP_FAST) && (!defined(_MSC_VER) || defined(_M_FP_STRICT))
    return contract;
#else
    return "unsupported_or_unattested";
#endif
}

EclipseSnapshotResult eclipse_strict_snapshot_evaluate(
    const EclipseSnapshotRecord& record, double jd, double jd2,
    double init, double intlen, int64_t record_count, int64_t expected_record,
    double descriptor_start, double descriptor_end
) {
    // The caller must not asynchronously alter this thread's FP environment
    // during the operation. No Python callback or GIL release occurs here.
    require_strict_snapshot_environment();
    for (double value : {jd, jd2, init, intlen, descriptor_start, descriptor_end}) {
        require_finite(value, "eclipse_snapshot_requires_finite_input");
    }
    if (intlen <= 0 || descriptor_start > descriptor_end || record_count <= 0 ||
        record_count > 9007199254740992LL || expected_record < 0 || expected_record >= record_count) {
        throw std::invalid_argument("eclipse_snapshot_invalid_metadata");
    }
    const size_t n = record[0].size();
    if (n == 0 || n > 256 || record[1].size() != n || record[2].size() != n) {
        throw std::invalid_argument("eclipse_snapshot_invalid_record_layout");
    }
    for (const auto& component : record) {
        for (double coefficient : component) require_finite(coefficient, "eclipse_snapshot_nonfinite_coefficient");
    }

    const double whole1 = std::floor(jd);
    const double whole2 = std::floor(jd2);
    if (std::abs(whole1) > 9007199254740992.0 || std::abs(whole2) > 9007199254740992.0) {
        throw std::invalid_argument("eclipse_snapshot_split_day_out_of_range");
    }
    const double anchor = (whole1 + whole2 - 2451545.0) * 86400.0;
    const double fraction = (jd - whole1) + (jd2 - whole2);
    const double from_start = std::fma(fraction, 86400.0, anchor - descriptor_start);
    const double from_end = std::fma(fraction, 86400.0, anchor - descriptor_end);
    if (!std::isfinite(anchor) || !std::isfinite(from_start) || !std::isfinite(from_end) ||
        from_start < 0.0 || from_end > 0.0) {
        throw std::invalid_argument("eclipse_snapshot_descriptor_coverage_failure");
    }

    // Match the existing native split epoch and record-local operation order.
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
    const double combined_index = (index1 + index2) + index3;
    for (double value : {epoch_seconds, offset_seconds, virtual_init, roundoff_seconds,
                         index1, offset1, split_seconds, index2, offset2,
                         combined_offset, index3, combined_index}) {
        require_finite(value, "eclipse_snapshot_record_calculation_nonfinite");
    }
    if (std::abs(index1) > 9007199254740992.0 || std::abs(index2) > 9007199254740992.0 ||
        std::abs(index3) > 9007199254740992.0 || combined_index < 0.0 ||
        combined_index > static_cast<double>(record_count)) {
        throw std::invalid_argument("eclipse_snapshot_record_index_outside_payload");
    }
    int64_t index = static_cast<int64_t>(combined_index);
    double local_offset = combined_offset - index3 * intlen;
    if (index == record_count) {
        --index;
        local_offset += intlen;
    }
    if (index != expected_record) throw std::invalid_argument("eclipse_snapshot_record_mismatch");
    const double radius = 0.5 * intlen;
    if (radius == 0.0) throw std::invalid_argument("eclipse_snapshot_zero_radius");
    const double s = (local_offset - radius) / radius;
    require_finite(s, "eclipse_snapshot_normalized_time_nonfinite");

    const double twice_s = 2.0 * s;
    const double scale = 172800.0 / intlen;
    std::array<double, 3> position{}, velocity{};
    for (size_t component = 0; component < 3; ++component) {
        double w1 = 0.0, w2 = 0.0, dw1 = 0.0, dw2 = 0.0;
        for (size_t i = n - 1; i > 0; --i) {
            const double old_dw1 = dw1;
            dw1 = (2.0 * w1) + (twice_s * dw1 - dw2);
            dw2 = old_dw1;
            const double old_w1 = w1;
            w1 = record[component][i] + twice_s * w1 - w2;
            w2 = old_w1;
        }
        position[component] = record[component][0] + s * w1 - w2;
        velocity[component] = (w1 + s * dw1 - dw2) * scale;
        require_finite(position[component], "eclipse_snapshot_position_nonfinite");
        require_finite(velocity[component], "eclipse_snapshot_velocity_nonfinite");
    }
    require_strict_snapshot_environment();
    return {position, velocity, s, index};
}

}  // namespace native
}  // namespace moira
