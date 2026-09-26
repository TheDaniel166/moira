#ifndef MOIRA_NATIVE_PCK_HPP
#define MOIRA_NATIVE_PCK_HPP

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "daf.hpp"
#include "geometry.hpp"

namespace moira {
namespace native {

struct PckSummaryEntry {
    std::string name;
    double start_second;
    double end_second;
    int32_t frame_class_id;
    int32_t inertial_frame_id;
    int32_t data_type;
    int32_t start_i;
    int32_t end_i;
};

inline PckSummaryEntry project_pck_summary(const DafSummaryEntry& entry) {
    if (entry.double_components.size() != 2 || entry.integer_components.size() != 5) {
        throw std::runtime_error("PCK summary requires ND=2 and NI=5");
    }
    PckSummaryEntry result{
        entry.name,
        entry.double_components[0],
        entry.double_components[1],
        entry.integer_components[0],
        entry.integer_components[1],
        entry.integer_components[2],
        entry.integer_components[3],
        entry.integer_components[4],
    };
    if (
        !std::isfinite(result.start_second)
        || !std::isfinite(result.end_second)
        || result.start_second > result.end_second
        || result.start_i <= 0
        || result.end_i < result.start_i
    ) {
        throw std::runtime_error("PCK descriptor metadata is invalid");
    }
    return result;
}

inline std::vector<PckSummaryEntry> project_pck_catalog(const DafCatalog& catalog) {
    if (catalog.locidw != "DAF/PCK" || catalog.nd != 2 || catalog.ni != 5) {
        throw std::runtime_error("PCK catalog requires a DAF/PCK ND=2 NI=5 kernel");
    }
    std::vector<PckSummaryEntry> summaries;
    summaries.reserve(catalog.summaries.size());
    for (const auto& entry : catalog.summaries) {
        summaries.push_back(project_pck_summary(entry));
    }
    return summaries;
}

class NativePckKernelHandle {
public:
    explicit NativePckKernelHandle(std::string kernel_path)
        : path(std::move(kernel_path)), file(path, std::ios::binary), catalog() {
        if (!file.is_open()) {
            throw std::runtime_error("unable to open DAF file");
        }
        catalog = read_daf_catalog(file);
        summaries_ = project_pck_catalog(catalog);
        if (summaries_.empty()) {
            throw std::runtime_error("PCK kernel contains no segments");
        }
        for (const auto& summary : summaries_) {
            if (summary.data_type != 2) {
                throw std::runtime_error("only PCK type 2 segments are supported");
            }
            if (summary.inertial_frame_id != 1) {
                throw std::runtime_error("PCK segment inertial frame must be J2000 (frame 1)");
            }
        }
    }

    std::pair<double, double> coverage_jd(int32_t frame_class_id) const {
        double start_second = std::numeric_limits<double>::infinity();
        double end_second = -std::numeric_limits<double>::infinity();
        bool found = false;
        for (const auto& summary : summaries_) {
            if (summary.frame_class_id != frame_class_id) {
                continue;
            }
            found = true;
            start_second = std::min(start_second, summary.start_second);
            end_second = std::max(end_second, summary.end_second);
        }
        if (!found) {
            throw std::invalid_argument("PCK frame class ID is not present in the kernel");
        }
        return {
            start_second / 86400.0 + 2451545.0,
            end_second / 86400.0 + 2451545.0,
        };
    }

    std::array<double, 3> euler_angles(double jd_tdb, int32_t frame_class_id) {
        if (!std::isfinite(jd_tdb)) {
            throw std::invalid_argument("PCK evaluation epoch must be finite JD TDB");
        }
        const PckSummaryEntry& summary = select_segment(jd_tdb, frame_class_id);
        auto evaluator = get_segment_evaluator(summary);
        double angles[3] = {0.0, 0.0, 0.0};
        evaluator->position(jd_tdb, angles);
        if (!std::isfinite(angles[0]) || !std::isfinite(angles[1]) || !std::isfinite(angles[2])) {
            throw std::runtime_error("PCK type 2 evaluation produced non-finite Euler angles");
        }
        return {angles[0], angles[1], angles[2]};
    }

    Mat3 rotation_matrix(double jd_tdb, int32_t frame_class_id) {
        const auto angles = euler_angles(jd_tdb, frame_class_id);
        // Binary PCK type 2 stores the three Euler angles used directly by
        // the 3-1-3 inertial-to-body-fixed rotation, in coefficient order
        // (angle1, angle2, angle3).
        return Mat3::mul(
            Mat3::rot_z(angles[2]),
            Mat3::mul(
                Mat3::rot_x(angles[1]),
                Mat3::rot_z(angles[0])
            )
        );
    }

    void close() {
        std::lock_guard<std::mutex> guard(mutex_);
        if (closed_) {
            return;
        }
        evaluators_.clear();
        if (file.is_open()) {
            file.close();
        }
        closed_ = true;
    }

    size_t segment_cache_size() const {
        std::lock_guard<std::mutex> guard(mutex_);
        return evaluators_.size();
    }

    std::string path;
    std::ifstream file;
    DafCatalog catalog;

    const std::vector<PckSummaryEntry>& summaries() const {
        return summaries_;
    }

private:
    const PckSummaryEntry& select_segment(double jd_tdb, int32_t frame_class_id) const {
        const double second = (jd_tdb - 2451545.0) * 86400.0;
        for (auto it = summaries_.rbegin(); it != summaries_.rend(); ++it) {
            if (
                it->frame_class_id == frame_class_id
                && second >= it->start_second
                && second <= it->end_second
            ) {
                return *it;
            }
        }
        throw std::out_of_range("PCK epoch is outside descriptor coverage");
    }

    std::shared_ptr<SpkSegmentEvaluator> get_segment_evaluator(
        const PckSummaryEntry& summary
    ) {
        const int64_t key =
            (static_cast<int64_t>(summary.start_i) << 32)
            ^ static_cast<uint32_t>(summary.end_i);
        std::lock_guard<std::mutex> guard(mutex_);
        if (closed_) {
            throw std::runtime_error("native PCK kernel handle is closed");
        }
        const auto found = evaluators_.find(key);
        if (found != evaluators_.end()) {
            return found->second;
        }
        const auto payload = read_spk_chebyshev_segment_payload(
            file,
            summary.start_i,
            summary.end_i,
            catalog.little_endian,
            summary.data_type,
            false
        );
        auto evaluator = std::make_shared<SpkSegmentEvaluator>(
            summary.start_second / 86400.0 + 2451545.0,
            summary.end_second / 86400.0 + 2451545.0,
            2,
            true,
            payload.init,
            payload.intlen,
            payload.record_count,
            payload.component_count,
            payload.coefficient_count,
            payload.coefficients
        );
        evaluators_.emplace(key, evaluator);
        return evaluator;
    }

    std::vector<PckSummaryEntry> summaries_;
    mutable std::mutex mutex_;
    bool closed_ = false;
    std::unordered_map<int64_t, std::shared_ptr<SpkSegmentEvaluator>> evaluators_;
};

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_PCK_HPP
