#include "lola.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <unordered_map>

namespace moira {
namespace native {
namespace lola {

// ============================================================================
// LolaPointCloud Implementation
// ============================================================================

LolaPointCloud::LolaPointCloud(const std::vector<double>& x,
                               const std::vector<double>& y,
                               const std::vector<double>& z)
    : x_(x), y_(y), z_(z), size_(x.size())
{
    if (y.size() != size_ || z.size() != size_) {
        throw std::invalid_argument(
            "LolaPointCloud: coordinate vectors must have the same size");
    }
    // Debug print
    // printf("LolaPointCloud created with size: %zu\n", size_);
}

LolaPointCloud LolaPointCloud::filter_by_visibility(const Vec3& observer_dir) const {
    // Placeholder implementation - will be implemented in Phase 2
    std::vector<double> x_filtered, y_filtered, z_filtered;
    x_filtered.reserve(size_);
    y_filtered.reserve(size_);
    z_filtered.reserve(size_);

    for (size_t i = 0; i < size_; ++i) {
        double dot = x_[i] * observer_dir[0] + 
                     y_[i] * observer_dir[1] + 
                     z_[i] * observer_dir[2];
        if (dot > 0.0) {
            x_filtered.push_back(x_[i]);
            y_filtered.push_back(y_[i]);
            z_filtered.push_back(z_[i]);
        }
    }

    return LolaPointCloud(x_filtered, y_filtered, z_filtered);
}

LolaPointCloud LolaPointCloud::filter_by_position_angle(
    const Vec3& sky_east,
    const Vec3& sky_north,
    double target_pa_deg,
    double tolerance_deg) const
{
    std::vector<double> ox, oy, oz;
    ox.reserve(size_);
    oy.reserve(size_);
    oz.reserve(size_);

    constexpr double RAD_TO_DEG = 180.0 / 3.141592653589793238462643383279502884;

    for (size_t i = 0; i < size_; ++i) {
        double east = x_[i] * sky_east[0] + y_[i] * sky_east[1] + z_[i] * sky_east[2];
        double north = x_[i] * sky_north[0] + y_[i] * sky_north[1] + z_[i] * sky_north[2];
        // Exclude points at the origin (PA undefined)
        if (std::abs(east) < 1e-15 && std::abs(north) < 1e-15) continue;
        
        // PA measured from north through east
        double pa = std::atan2(east, north) * RAD_TO_DEG;
        if (pa < 0.0) pa += 360.0;
        
        double diff = std::abs(pa - target_pa_deg);
        if (diff > 180.0) diff = 360.0 - diff;
        
        if (diff <= tolerance_deg) {
            ox.push_back(x_[i]);
            oy.push_back(y_[i]);
            oz.push_back(z_[i]);
        }
    }

    return LolaPointCloud(ox, oy, oz);
}

LolaPointCloud LolaPointCloud::filter_by_radius(
    const Vec3& sky_east,
    const Vec3& sky_north,
    double min_radius_km) const
{
    std::vector<double> ox, oy, oz;
    ox.reserve(size_);
    oy.reserve(size_);
    oz.reserve(size_);

    for (size_t i = 0; i < size_; ++i) {
        double east = x_[i] * sky_east[0] + y_[i] * sky_east[1] + z_[i] * sky_east[2];
        double north = x_[i] * sky_north[0] + y_[i] * sky_north[1] + z_[i] * sky_north[2];
        double r_proj = std::sqrt(east*east + north*north);
        
        if (r_proj >= min_radius_km) {
            ox.push_back(x_[i]);
            oy.push_back(y_[i]);
            oz.push_back(z_[i]);
        }
    }

    return LolaPointCloud(ox, oy, oz);
}

LolaPointCloud LolaPointCloud::filter_combined(
    const Vec3& observer_dir,
    const Vec3& sky_east,
    const Vec3& sky_north,
    double target_pa_deg,
    double pa_tolerance_deg,
    double min_radius_km) const
{
    std::vector<double> ox, oy, oz;
    ox.reserve(size_);
    oy.reserve(size_);
    oz.reserve(size_);

    constexpr double RAD_TO_DEG = 180.0 / 3.141592653589793238462643383279502884;

    for (size_t i = 0; i < size_; ++i) {
        // 1. Visibility check (fastest)
        double dot = x_[i] * observer_dir[0] + y_[i] * observer_dir[1] + z_[i] * observer_dir[2];
        if (dot <= 0.0) continue;
        
        // 2. Projection
        double east = x_[i] * sky_east[0] + y_[i] * sky_east[1] + z_[i] * sky_east[2];
        double north = x_[i] * sky_north[0] + y_[i] * sky_north[1] + z_[i] * sky_north[2];
        
        // 3. Radius check
        double r_proj = std::sqrt(east*east + north*north);
        if (r_proj < min_radius_km) continue;

        // Exclude points at the origin (PA undefined) for PA check
        if (r_proj < 1e-15) continue;
        
        // 4. PA check
        double pa = std::atan2(east, north) * RAD_TO_DEG;
        if (pa < 0.0) pa += 360.0;
        
        double diff = std::abs(pa - target_pa_deg);
        if (diff > 180.0) diff = 360.0 - diff;
        
        if (diff <= pa_tolerance_deg) {
            ox.push_back(x_[i]);
            oy.push_back(y_[i]);
            oz.push_back(z_[i]);
        }
    }

    return LolaPointCloud(ox, oy, oz);
}

SphericalCoords LolaPointCloud::to_spherical() const {
    // Placeholder implementation - will be implemented in Phase 2
    SphericalCoords result;
    result.lon_deg.resize(size_);
    result.lat_deg.resize(size_);
    result.radius_km.resize(size_);
    
    cartesian_to_spherical_bulk(
        x_.data(), y_.data(), z_.data(),
        result.lon_deg.data(), result.lat_deg.data(), result.radius_km.data(),
        size_
    );
    
    return result;
}

SkyPlaneProjection LolaPointCloud::project_to_sky_plane(
    const Vec3& observer_dir,
    const Vec3& sky_east,
    const Vec3& sky_north) const
{
    SkyPlaneProjection result;
    result.east_km.resize(size_);
    result.north_km.resize(size_);
    result.radius_km.resize(size_);
    result.pa_deg.resize(size_);

    constexpr double RAD_TO_DEG = 180.0 / 3.141592653589793238462643383279502884;

    for (size_t i = 0; i < size_; ++i) {
        double east = x_[i] * sky_east[0] + y_[i] * sky_east[1] + z_[i] * sky_east[2];
        double north = x_[i] * sky_north[0] + y_[i] * sky_north[1] + z_[i] * sky_north[2];
        
        result.east_km[i] = east;
        result.north_km[i] = north;
        result.radius_km[i] = std::sqrt(east*east + north*north);
        
        double pa = std::atan2(east, north) * RAD_TO_DEG;
        if (pa < 0.0) pa += 360.0;
        result.pa_deg[i] = pa;
    }

    return result;
}

// ============================================================================
// Vector Operations Implementation
// ============================================================================

void normalize_vectors_bulk(
    const double* x_in, const double* y_in, const double* z_in,
    double* x_out, double* y_out, double* z_out,
    size_t count)
{
    // Placeholder implementation - will be implemented in Phase 1
    for (size_t i = 0; i < count; ++i) {
        double norm = std::sqrt(x_in[i] * x_in[i] + 
                               y_in[i] * y_in[i] + 
                               z_in[i] * z_in[i]);
        if (norm < 1e-15) {
            x_out[i] = 0.0;
            y_out[i] = 0.0;
            z_out[i] = 0.0;
        } else {
            x_out[i] = x_in[i] / norm;
            y_out[i] = y_in[i] / norm;
            z_out[i] = z_in[i] / norm;
        }
    }
}

void dot_product_bulk(
    const double* x, const double* y, const double* z,
    const Vec3& reference,
    double* results,
    size_t count)
{
    // Placeholder implementation - will be implemented in Phase 1
    for (size_t i = 0; i < count; ++i) {
        results[i] = x[i] * reference[0] + 
                     y[i] * reference[1] + 
                     z[i] * reference[2];
    }
}

void cross_product_bulk(
    const double* x, const double* y, const double* z,
    const Vec3& reference,
    double* x_out, double* y_out, double* z_out,
    size_t count)
{
    // Placeholder implementation - will be implemented in Phase 1
    for (size_t i = 0; i < count; ++i) {
        x_out[i] = y[i] * reference[2] - z[i] * reference[1];
        y_out[i] = z[i] * reference[0] - x[i] * reference[2];
        z_out[i] = x[i] * reference[1] - y[i] * reference[0];
    }
}

void project_onto_plane_bulk(
    const double* x_in, const double* y_in, const double* z_in,
    const Vec3& plane_normal,
    double* x_out, double* y_out, double* z_out,
    size_t count)
{
    // Placeholder implementation - will be implemented in Phase 1
    for (size_t i = 0; i < count; ++i) {
        double dot = x_in[i] * plane_normal[0] + 
                     y_in[i] * plane_normal[1] + 
                     z_in[i] * plane_normal[2];
        x_out[i] = x_in[i] - dot * plane_normal[0];
        y_out[i] = y_in[i] - dot * plane_normal[1];
        z_out[i] = z_in[i] - dot * plane_normal[2];
    }
}

// ============================================================================
// Coordinate Transformations Implementation
// ============================================================================

void cartesian_to_spherical_bulk(
    const double* x, const double* y, const double* z,
    double* lon_deg, double* lat_deg, double* radius_km,
    size_t count)
{
    constexpr double RAD_TO_DEG = 180.0 / 3.141592653589793238462643383279502884;
    
    for (size_t i = 0; i < count; ++i) {
        // Compute radius
        double r = std::sqrt(x[i] * x[i] + y[i] * y[i] + z[i] * z[i]);
        radius_km[i] = r;
        
        if (r < 1e-15) {
            // Zero radius case
            lon_deg[i] = 0.0;
            lat_deg[i] = 0.0;
        } else {
            // Compute longitude using atan2 for correct quadrant handling
            lon_deg[i] = std::atan2(y[i], x[i]) * RAD_TO_DEG;
            
            // Compute latitude with clamping to avoid domain errors
            double lat_sin = z[i] / r;
            lat_sin = std::max(-1.0, std::min(1.0, lat_sin));
            lat_deg[i] = std::asin(lat_sin) * RAD_TO_DEG;
        }
    }
}

void spherical_to_cartesian_bulk(
    const double* lon_deg, const double* lat_deg, const double* radius_km,
    double* x, double* y, double* z,
    size_t count)
{
    constexpr double DEG_TO_RAD = 3.141592653589793238462643383279502884 / 180.0;
    
    for (size_t i = 0; i < count; ++i) {
        double lon_rad = lon_deg[i] * DEG_TO_RAD;
        double lat_rad = lat_deg[i] * DEG_TO_RAD;
        double r = radius_km[i];
        
        double cos_lat = std::cos(lat_rad);
        x[i] = r * cos_lat * std::cos(lon_rad);
        y[i] = r * cos_lat * std::sin(lon_rad);
        z[i] = r * std::sin(lat_rad);
    }
}

void normalize_longitude_bulk(double* lon_deg, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        // Normalize to [-180, 180]
        double lon = lon_deg[i];
        lon = std::fmod(lon + 180.0, 360.0);
        if (lon < 0.0) {
            lon += 360.0;
        }
        lon_deg[i] = lon - 180.0;
    }
}

// ============================================================================
// Sorting and Binning Implementation
// ============================================================================

std::vector<int> bin_by_position_angle(
    const double* pa_deg, 
    double target_pa_deg, 
    double bin_width_deg, 
    size_t count)
{
    std::vector<int> bins(count);
    
    for (size_t i = 0; i < count; ++i) {
        double diff = pa_deg[i] - target_pa_deg;
        // Normalize diff to [-180, 180]
        while (diff > 180.0) diff -= 360.0;
        while (diff <= -180.0) diff += 360.0;
        
        bins[i] = static_cast<int>(std::round(diff / bin_width_deg));
    }
    
    return bins;
}

MaxPerBin select_max_radius_per_bin(
    const int* bin_indices, 
    const double* radius_km, 
    size_t count)
{
    // Use a map to track max radius per bin
    // For performance, we could use a fixed-size array if we knew the bin range,
    // but a map is safer for arbitrary bin indices.
    struct BinInfo {
        double max_r;
        size_t index;
    };
    std::unordered_map<int, BinInfo> max_map;
    
    for (size_t i = 0; i < count; ++i) {
        int bin = bin_indices[i];
        double r = radius_km[i];
        
        auto it = max_map.find(bin);
        if (it == max_map.end() || r > it->second.max_r) {
            max_map[bin] = {r, i};
        }
    }
    
    MaxPerBin result;
    result.bins.reserve(max_map.size());
    result.radii_km.reserve(max_map.size());
    result.point_indices.reserve(max_map.size());
    
    for (const auto& pair : max_map) {
        result.bins.push_back(pair.first);
        result.radii_km.push_back(pair.second.max_r);
        result.point_indices.push_back(pair.second.index);
    }
    
    return result;
}

std::vector<size_t> lexsort_by_bin_and_radius(
    const int* bin_indices, 
    const double* radius_km, 
    size_t count)
{
    std::vector<size_t> indices(count);
    for (size_t i = 0; i < count; ++i) indices[i] = i;
    
    // Equivalent to numpy.lexsort((radius_km, bin_indices))
    // Which means primary key is bin_indices (ascending), 
    // secondary key is radius_km (descending usually for limb, but lexsort is ascending)
    // Actually, usually we want to sort by bin index then descending radius.
    // Let's stick to Requirements 4.5: "identical results to numpy.lexsort"
    // numpy.lexsort((keys2, keys1)) sorts by keys1 then keys2.
    
    std::stable_sort(indices.begin(), indices.end(), [&](size_t a, size_t b) {
        if (bin_indices[a] != bin_indices[b]) {
            return bin_indices[a] < bin_indices[b];
        }
        return radius_km[a] < radius_km[b];
    });
    
    return indices;
}

// ============================================================================
// Convex Hull Implementation
// ============================================================================

std::vector<Point2D> convex_hull_2d(const std::vector<Point2D>& points) {
    // Placeholder implementation - will be implemented in Phase 3
    // For now, return empty hull
    if (points.size() <= 1) {
        return points;
    }
    
    // Remove duplicates and sort
    std::vector<Point2D> sorted_points = points;
    std::sort(sorted_points.begin(), sorted_points.end());
    sorted_points.erase(
        std::unique(sorted_points.begin(), sorted_points.end()),
        sorted_points.end()
    );
    
    if (sorted_points.size() <= 2) {
        return sorted_points;
    }
    
    // Build lower hull
    std::vector<Point2D> lower;
    for (const auto& p : sorted_points) {
        while (lower.size() >= 2 && 
               cross_2d(lower[lower.size()-2], lower[lower.size()-1], p) <= 0) {
            lower.pop_back();
        }
        lower.push_back(p);
    }
    
    // Build upper hull
    std::vector<Point2D> upper;
    for (auto it = sorted_points.rbegin(); it != sorted_points.rend(); ++it) {
        while (upper.size() >= 2 && 
               cross_2d(upper[upper.size()-2], upper[upper.size()-1], *it) <= 0) {
            upper.pop_back();
        }
        upper.push_back(*it);
    }
    
    // Remove last point of each half to avoid duplication
    lower.pop_back();
    upper.pop_back();
    
    // Concatenate
    lower.insert(lower.end(), upper.begin(), upper.end());
    return lower;
}

// ============================================================================
// Ray-Hull Intersection Implementation
// ============================================================================

double ray_hull_intersection(
    const std::vector<Point2D>& hull,
    double position_angle_deg,
    double fallback_radius_km)
{
    // Placeholder implementation - will be implemented in Phase 3
    if (hull.empty()) {
        return fallback_radius_km;
    }
    
    constexpr double DEG_TO_RAD = 3.141592653589793238462643383279502884 / 180.0;
    double pa_rad = position_angle_deg * DEG_TO_RAD;
    
    // Ray direction (PA measured from north through east)
    double ray_x = std::sin(pa_rad);
    double ray_y = std::cos(pa_rad);
    
    double best_t = -1.0;
    constexpr double EPSILON = 1e-12;
    
    // Test ray against each hull edge
    for (size_t i = 0; i < hull.size(); ++i) {
        const Point2D& start = hull[i];
        const Point2D& end = hull[(i + 1) % hull.size()];
        
        double edge_x = end.x - start.x;
        double edge_y = end.y - start.y;
        
        // Solve: t*ray = start + u*edge using Cramer's rule
        double det = ray_x * (-edge_y) - ray_y * (-edge_x);
        
        if (std::abs(det) < EPSILON) {
            continue;  // Parallel
        }
        
        double t = (start.x * (-edge_y) - start.y * (-edge_x)) / det;
        double u = (ray_x * start.y - ray_y * start.x) / det;
        
        if (t >= 0.0 && u >= 0.0 && u <= 1.0) {
            if (best_t < 0.0 || t > best_t) {
                best_t = t;
            }
        }
    }
    
    return (best_t >= 0.0) ? best_t : fallback_radius_km;
}

} // namespace lola
} // namespace native
} // namespace moira
