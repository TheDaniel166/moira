#ifndef MOIRA_NATIVE_SPK_BATCH_HPP
#define MOIRA_NATIVE_SPK_BATCH_HPP

#include <iomanip>
#include <map>
#include <sstream>
#include "daf.hpp"
#include "light_time.hpp"

namespace moira {
namespace native {

using SpkPair = std::pair<int32_t, int32_t>;
using SpkRoute = std::vector<SpkPair>;

/**
 * Evaluate explicit ICRF routes in one kernel. Each request shares reception
 * leg states and owns its descriptor evaluators and bounded record windows.
 */
class SpkBatchEvaluator {
public:
    SpkBatchEvaluator(NativeSpkKernelHandle& handle, size_t sample_count)
        : handle_(handle), sample_count_(sample_count) {}

    void states(
        const std::vector<SpkRoute>& routes, const std::vector<double>& epochs, double* out
    ) {
        const auto paths = compile_routes(routes, false);
        std::vector<std::array<double, 6>> legs(legs_.size());
        for (size_t epoch = 0; epoch < epochs.size(); ++epoch) {
            const double jd = epochs[epoch];
            for (size_t leg = 0; leg < legs.size(); ++leg) {
                auto& segment = select(leg, jd, 0.0);
                double* state = legs[leg].data();
                segment.evaluator->position_and_velocity(jd, 0.0, state, state + 3, &segment.records);
                if (segment.entry.data_type == 3) {
                    // Type 3 stores rates in km/s. Type 2 differentiates in km/day.
                    for (size_t component = 3; component < 6; ++component) {
                        state[component] *= 86400.0;
                    }
                }
            }
            for (size_t route = 0; route < paths.size(); ++route) {
                double* row = out + (route * epochs.size() + epoch) * 6;
                std::fill_n(row, 6, 0.0);
                for (size_t leg : paths[route]) {
                    for (size_t component = 0; component < 6; ++component) {
                        row[component] += legs[leg][component];
                    }
                }
            }
        }
    }

    void received_light(
        const SpkRoute& observer_route, const std::vector<SpkRoute>& target_routes,
        const std::vector<double>& epochs, double* out
    ) {
        const auto observer_path = compile_route(observer_route, true);
        const auto paths = compile_routes(target_routes, true);
        std::vector<Vec3> legs(legs_.size());
        const auto reception_position = [&](const Path& path) {
            return sum_positions(path, [&](size_t leg) { return legs[leg]; });
        };
        for (size_t epoch = 0; epoch < epochs.size(); ++epoch) {
            const double jd = epochs[epoch];
            for (size_t leg = 0; leg < legs.size(); ++leg) {
                legs[leg] = position(leg, jd, 0.0);
            }
            const Vec3 observer = reception_position(observer_path);
            for (size_t route = 0; route < paths.size(); ++route) {
                const auto& path = paths[route];
                const auto [xyz, delay] = solve_reception_light_time(
                    observer, reception_position(path), [&](double offset) {
                        return sum_positions(path, [&](size_t leg) { return position(leg, jd, offset); });
                    }
                );
                double* row = out + (route * epochs.size() + epoch) * 4;
                std::copy_n(xyz.data.data(), 3, row);
                row[3] = delay;
            }
        }
    }

private:
    using Path = std::vector<size_t>;

    template <typename Sample>
    static Vec3 sum_positions(const Path& path, Sample sample) {
        const Vec3 first = sample(path.front());
        if (path.size() == 1) {
            return first;
        }
        const Vec3 second = sample(path[1]);
        Vec3 sum = first + second;
        if (path.size() == 2) {
            return sum;
        }
        Vec3 correction;
        // Neumaier summation retains small contributions across multiple legs.
        for (size_t axis = 0; axis < 3; ++axis) {
            correction[axis] = addition_residual(first[axis], second[axis], sum[axis]);
        }
        for (size_t leg = 2; leg < path.size(); ++leg) {
            const Vec3 next = sample(path[leg]);
            for (size_t axis = 0; axis < 3; ++axis) {
                const double combined = sum[axis] + next[axis];
                correction[axis] += addition_residual(sum[axis], next[axis], combined);
                sum[axis] = combined;
            }
        }
        return sum + correction;
    }

    static double addition_residual(double a, double b, double sum) {
        return std::abs(a) >= std::abs(b) ? (a - sum) + b : (b - sum) + a;
    }

    struct Segment {
        Segment(const DafSummaryEntry& entry, size_t sample_count)
            : entry(entry), records(sample_count) {}

        const DafSummaryEntry& entry;
        std::shared_ptr<SpkSegmentEvaluator> evaluator;
        SpkSegmentEvaluator::BatchRecords records;
    };

    struct Leg {
        SpkPair pair;
        std::vector<Segment> segments;
    };

    NativeSpkKernelHandle& handle_;
    size_t sample_count_;
    std::map<SpkPair, size_t> leg_index_;
    std::vector<Leg> legs_;

    std::vector<Path> compile_routes(const std::vector<SpkRoute>& routes, bool require_ssb) {
        std::vector<Path> paths;
        paths.reserve(routes.size());
        for (const auto& route : routes) {
            paths.push_back(compile_route(route, require_ssb));
        }
        return paths;
    }

    Path compile_route(const SpkRoute& route, bool require_ssb) {
        if (route.empty()) {
            throw std::invalid_argument("SPK batch routes must contain at least one center-target pair");
        }
        if (require_ssb && route.front().first != 0) {
            throw std::invalid_argument("Light-time routes must start at the solar system barycenter (0)");
        }
        Path path;
        path.reserve(route.size());
        int32_t previous = route.front().first;
        for (const auto& pair : route) {
            if (pair.first != previous) {
                throw std::invalid_argument("SPK batch routes must be contiguous");
            }
            const auto [index, inserted] = leg_index_.try_emplace(pair, legs_.size());
            if (inserted) {
                auto& leg = legs_.emplace_back(Leg{pair, {}});
                const auto& catalog = handle_.catalog.summaries;
                for (auto it = catalog.rbegin(); it != catalog.rend(); ++it) {
                    if (it->center == pair.first && it->target == pair.second) {
                        leg.segments.emplace_back(*it, sample_count_);
                    }
                }
            }
            path.push_back(index->second);
            previous = pair.second;
        }
        return path;
    }

    Segment& select(size_t leg_index, double jd, double offset) {
        auto& leg = legs_[leg_index];
        // Scan newest to oldest at every sample, including light-time iterations.
        for (auto& segment : leg.segments) {
            if (!spk_descriptor_covers_tdb(segment.entry, jd, offset)) {
                continue;
            }
            if (!segment.evaluator) {
                const auto& entry = segment.entry;
                if (entry.frame != 1 || (entry.data_type != 2 && entry.data_type != 3)) {
                    throw std::invalid_argument("SPK batches require J2000 Type 2 or 3 segments");
                }
                segment.evaluator = handle_.get_segment_evaluator(
                    entry.start_i, entry.end_i, entry.data_type
                );
            }
            return segment;
        }
        std::ostringstream message;
        message << "No SPK segment covers center=" << leg.pair.first << ", target=" << leg.pair.second
                << " at JD(TDB) " << std::setprecision(17) << jd << " with offset " << offset << " days";
        throw std::invalid_argument(message.str());
    }

    Vec3 position(size_t leg, double jd, double offset) {
        auto& segment = select(leg, jd, offset);
        Vec3 xyz;
        segment.evaluator->position(jd, offset, xyz.data.data(), &segment.records);
        return xyz;
    }
};

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_SPK_BATCH_HPP
