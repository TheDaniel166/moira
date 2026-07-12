#include "nutation.hpp"

#include <atomic>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>

#include "constants.hpp"

namespace moira {
namespace native {
namespace {

struct NutationSeries {
    std::vector<NutationSeriesTerm> longitude_terms;
    std::vector<NutationSeriesTerm> obliquity_terms;
    std::size_t longitude_j0_count = 0;
    std::size_t obliquity_j0_count = 0;
};

std::shared_ptr<const NutationSeries> g_series;

constexpr double TAU = 2.0 * 3.141592653589793238462643383279502884;
constexpr double UAS_TO_RAD = ARCSEC2RAD * 1.0e-6;

double wrap_tau(double value) noexcept {
    const double wrapped = std::fmod(value, TAU);
    return wrapped < 0.0 ? wrapped + TAU : wrapped;
}

std::array<double, 14> fundamental_arguments(double t) noexcept {
    const double l = (485868.249036
        + t * (1717915923.2178
        + t * (31.8792
        + t * (0.051635
        + t * (-0.00024470))))) * ARCSEC2RAD;
    const double lp = (1287104.793048
        + t * (129596581.0481
        + t * (-0.5532
        + t * (0.000136
        + t * (-0.00001149))))) * ARCSEC2RAD;
    const double f = (335779.526232
        + t * (1739527262.8478
        + t * (-12.7512
        + t * (-0.001037
        + t * (0.00000417))))) * ARCSEC2RAD;
    const double d = (1072260.703692
        + t * (1602961601.2090
        + t * (-6.3706
        + t * (0.006593
        + t * (-0.00003169))))) * ARCSEC2RAD;
    const double omega = (450160.398036
        + t * (-6962890.5431
        + t * (7.4722
        + t * (0.007702
        + t * (-0.00005939))))) * ARCSEC2RAD;

    return {
        l,
        lp,
        f,
        d,
        omega,
        wrap_tau(4.402608842 + 2608.7903141574 * t),
        wrap_tau(3.176146697 + 1021.3285546211 * t),
        wrap_tau(1.753470314 + 628.3075849991 * t),
        wrap_tau(6.203480913 + 334.0612426700 * t),
        wrap_tau(0.599546497 + 52.9690962641 * t),
        wrap_tau(0.874016757 + 21.3299104960 * t),
        wrap_tau(5.481293872 + 7.4781598567 * t),
        wrap_tau(5.311886287 + 3.8133035638 * t),
        wrap_tau(0.02438175 + 0.00000538691 * t),
    };
}

double argument(
    const NutationSeriesTerm& term,
    const std::array<double, 14>& arguments
) noexcept {
    double value = 0.0;
    for (std::size_t index = 0; index < term.argument_count; ++index) {
        value += static_cast<double>(term.arguments[index]) * arguments[index];
    }
    return value;
}

void validate_terms(
    const std::vector<NutationSeriesTerm>& terms,
    std::size_t j0_count,
    const char* table_name
) {
    if (terms.empty()) {
        throw std::invalid_argument(std::string(table_name) + " nutation table is empty");
    }
    if (j0_count > terms.size()) {
        throw std::invalid_argument(std::string(table_name) + " j=0 count exceeds table size");
    }
    for (const NutationSeriesTerm& term : terms) {
        if (term.argument_count == 0 || term.argument_count > term.arguments.size()) {
            throw std::invalid_argument(std::string(table_name) + " term has invalid argument count");
        }
    }
}

} // namespace

void register_nutation_2000r06_series(
    std::vector<NutationSeriesTerm> longitude_terms,
    std::vector<NutationSeriesTerm> obliquity_terms,
    std::size_t longitude_j0_count,
    std::size_t obliquity_j0_count
) {
    validate_terms(longitude_terms, longitude_j0_count, "longitude");
    validate_terms(obliquity_terms, obliquity_j0_count, "obliquity");

    auto series = std::make_shared<NutationSeries>();
    series->longitude_terms = std::move(longitude_terms);
    series->obliquity_terms = std::move(obliquity_terms);
    series->longitude_j0_count = longitude_j0_count;
    series->obliquity_j0_count = obliquity_j0_count;
    std::atomic_store_explicit(
        &g_series,
        std::shared_ptr<const NutationSeries>(std::move(series)),
        std::memory_order_release
    );
}

bool nutation_2000r06_series_ready() noexcept {
    return static_cast<bool>(std::atomic_load_explicit(&g_series, std::memory_order_acquire));
}

NutationResult nutation_2000r06(double jd_tt) {
    const auto series = std::atomic_load_explicit(&g_series, std::memory_order_acquire);
    if (!series) {
        throw std::runtime_error(
            "Native IERS 2000_R06 nutation tables are not registered"
        );
    }

    const double t = (jd_tt - J2000) / 36525.0;
    const std::array<double, 14> fa = fundamental_arguments(t);

    double longitude_uas = 0.0;
    for (std::size_t index = 0; index < series->longitude_terms.size(); ++index) {
        const NutationSeriesTerm& term = series->longitude_terms[index];
        const double phase = argument(term, fa);
        const double value = term.c1 * std::sin(phase) + term.c2 * std::cos(phase);
        longitude_uas += index < series->longitude_j0_count ? value : t * value;
    }

    double obliquity_uas = 0.0;
    for (std::size_t index = 0; index < series->obliquity_terms.size(); ++index) {
        const NutationSeriesTerm& term = series->obliquity_terms[index];
        const double phase = argument(term, fa);
        const double value = term.c2 * std::cos(phase) + term.c1 * std::sin(phase);
        obliquity_uas += index < series->obliquity_j0_count ? value : t * value;
    }

    return {
        longitude_uas * UAS_TO_RAD,
        obliquity_uas * UAS_TO_RAD,
    };
}

NutationResult NutationEpochCache::evaluate(double jd_tt) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        const auto found = values_.find(jd_tt);
        if (found != values_.end()) return found->second;
    }
    const NutationResult result = nutation_2000r06(jd_tt);
    std::lock_guard<std::mutex> lock(mutex_);
    return values_.emplace(jd_tt, result).first->second;
}

std::size_t NutationEpochCache::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return values_.size();
}

} // namespace native
} // namespace moira
