#ifndef MOIRA_NATIVE_SEARCH_POOL_HPP
#define MOIRA_NATIVE_SEARCH_POOL_HPP

#include "events.hpp"
#include <map>
#include <string>

namespace moira {
namespace native {

enum class EventType {
    STATION,
    INGRESS,
    OCCULTATION
};

struct SearchResult {
    EventType type;
    double jd;
    std::string description;
    double value; // e.g., separation or sign index
};

/**
 * @brief THEOREM: Unified Event Search Pool.
 * Consolidates multiple discovery kernels into a single temporal scan.
 */
class SearchPool {
public:
    struct Task {
        EventType type;
        std::shared_ptr<IEvaluator> target1;
        std::shared_ptr<IEvaluator> target2; // Optional (for separation)
        std::shared_ptr<IEvaluator> observer;
        double r1_km = 0.0;
        double r2_km = 0.0;
    };

    std::vector<Task> tasks;

    void add_station_task(std::shared_ptr<IEvaluator> t, std::shared_ptr<IEvaluator> obs) {
        tasks.push_back({EventType::STATION, t, nullptr, obs});
    }

    void add_ingress_task(std::shared_ptr<IEvaluator> t, std::shared_ptr<IEvaluator> obs) {
        tasks.push_back({EventType::INGRESS, t, nullptr, obs});
    }

    void add_occultation_task(std::shared_ptr<IEvaluator> t1, double r1, std::shared_ptr<IEvaluator> t2, double r2, std::shared_ptr<IEvaluator> obs) {
        tasks.push_back({EventType::OCCULTATION, t1, t2, obs, r1, r2});
    }

    std::vector<SearchResult> run(double a, double b, double dt = 0.5) {
        std::vector<SearchResult> results;

        // In Phase 4, we currently execute sequentially for rigor.
        // Future slices can parallelize this loop.
        for (const auto& task : tasks) {
            if (task.type == EventType::STATION) {
                auto times = find_stations(*task.target1, *task.observer, a, b, dt);
                for (double t : times) results.push_back({EventType::STATION, t, "STATION", 0.0});
            } else if (task.type == EventType::INGRESS) {
                auto times = find_ingresses(*task.target1, *task.observer, a, b, dt);
                for (double t : times) results.push_back({EventType::INGRESS, t, "INGRESS", 0.0});
            } else if (task.type == EventType::OCCULTATION) {
                auto events = find_occultations(*task.target1, task.r1_km, *task.target2, task.r2_km, *task.observer, a, b, dt);
                for (const auto& ev : events) {
                    results.push_back({EventType::OCCULTATION, ev.t_mid, "OCCULTATION", ev.separation_min});
                }
            }
        }

        // Sort by time
        std::sort(results.begin(), results.end(), [](const SearchResult& a, const SearchResult& b) {
            return a.jd < b.jd;
        });

        return results;
    }
};

} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_SEARCH_POOL_HPP
