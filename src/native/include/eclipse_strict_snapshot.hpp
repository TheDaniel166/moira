#pragma once

#include <array>
#include <cstdint>
#include <tuple>
#include <vector>

namespace moira {
namespace native {

// The caller owns one immutable copied type-2 record in ascending degree order.
using EclipseSnapshotRecord = std::array<std::vector<double>, 3>;
using EclipseSnapshotResult = std::tuple<std::array<double, 3>, std::array<double, 3>, double, int64_t>;

// This is an opt-in strict scalar model; it does not attest the legacy mapped
// evaluator, source integrity, whole-route selection, time or light-time.
EclipseSnapshotResult eclipse_strict_snapshot_evaluate(
    const EclipseSnapshotRecord& record, double jd, double jd2,
    double init, double intlen, int64_t record_count, int64_t expected_record,
    double descriptor_start, double descriptor_end
);

const char* eclipse_strict_snapshot_build_contract();

}  // namespace native
}  // namespace moira
