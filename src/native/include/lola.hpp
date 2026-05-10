#ifndef MOIRA_NATIVE_LOLA_HPP
#define MOIRA_NATIVE_LOLA_HPP

#include <vector>
#include <cstddef>
#include "geometry.hpp"

/**
 * @brief LOLA (Lunar Orbiter Laser Altimeter) point-cloud processing module.
 * 
 * This module provides native C++ implementations for LOLA point-cloud operations,
 * replacing numpy-based Python implementations in moira/lunar_limb.py.
 * 
 * The module follows the dual-substrate architecture established in
 * MOIRA_NATIVE_BACKEND_ARCHITECTURE.md, where Python remains the canonical
 * reference and C++ provides the accelerated implementation.
 * 
 * Namespace: moira::native::lola
 * 
 * Key Components:
 * - LolaPointCloud: Efficient container for LOLA point cloud data
 * - Vector operations: Bulk normalization, dot product, cross product, projection
 * - Coordinate transformations: Cartesian ↔ spherical conversions
 * - Filtering operations: Visibility, position angle, radial distance filters
 * - Sorting and binning: Angular binning and maximum radius selection
 * - Convex hull: 2D convex hull computation (Andrew's monotone chain algorithm)
 * - Ray-hull intersection: Compute intersection of ray with convex hull
 * 
 * Design Goals:
 * - Zero NumPy dependency in production code
 * - Performance preservation or improvement through SIMD vectorization
 * - Numerical fidelity within documented tolerances
 * - API stability for public lunar limb functions
 * 
 * Validates: Requirements 15.1, 15.2, 15.4
 */

namespace moira {
namespace native {
namespace lola {

// Forward declarations
struct SphericalCoords;
struct SkyPlaneProjection;
struct FilterResult;
struct BinnedPoints;
struct MaxPerBin;
struct Point2D;

/**
 * @brief Efficient container for LOLA point cloud data.
 * 
 * Uses structure-of-arrays (SoA) layout for SIMD-friendly access patterns.
 * Stores Cartesian coordinates (x, y, z) in separate vectors.
 * 
 * Memory Layout: Separate x, y, z arrays enable vectorized operations.
 * Ownership: Point cloud owns its coordinate data.
 */
class LolaPointCloud {
private:
    std::vector<double> x_;  // Cartesian X coordinates (km)
    std::vector<double> y_;  // Cartesian Y coordinates (km)
    std::vector<double> z_;  // Cartesian Z coordinates (km)
    size_t size_;

public:
    /**
     * @brief Construct point cloud from coordinate vectors.
     * 
     * @param x X coordinates in kilometers
     * @param y Y coordinates in kilometers
     * @param z Z coordinates in kilometers
     * @throws std::invalid_argument if coordinate vectors have different sizes
     */
    LolaPointCloud(const std::vector<double>& x,
                   const std::vector<double>& y,
                   const std::vector<double>& z);

    /**
     * @brief Default constructor creates empty point cloud.
     */
    LolaPointCloud() : size_(0) {}

    // Accessors
    size_t size() const { return size_; }
    const double* x_data() const { return x_.data(); }
    const double* y_data() const { return y_.data(); }
    const double* z_data() const { return z_.data(); }

    const std::vector<double>& x_list() const { return x_; }
    const std::vector<double>& y_list() const { return y_; }
    const std::vector<double>& z_list() const { return z_; }

    /**
     * @brief Filter points by visibility (dot product with observer direction > 0).
     * 
     * @param observer_dir Unit vector pointing from Moon center to observer
     * @return New point cloud containing only visible points
     */
    LolaPointCloud filter_by_visibility(const Vec3& observer_dir) const;

    /**
     * @brief Filter points by position angle window.
     * 
     * @param sky_east Unit vector pointing east in sky plane
     * @param sky_north Unit vector pointing north in sky plane
     * @param target_pa_deg Target position angle in degrees
     * @param tolerance_deg Angular tolerance in degrees
     * @return New point cloud containing points within angular window
     */
    LolaPointCloud filter_by_position_angle(
        const Vec3& sky_east,
        const Vec3& sky_north,
        double target_pa_deg,
        double tolerance_deg) const;

    /**
     * @brief Filter points by minimum projected radius.
     * 
     * @param sky_east Unit vector pointing east in sky plane
     * @param sky_north Unit vector pointing north in sky plane
     * @param min_radius_km Minimum projected radius in kilometers
     * @return New point cloud containing points with radius >= min_radius_km
     */
    LolaPointCloud filter_by_radius(
        const Vec3& sky_east,
        const Vec3& sky_north,
        double min_radius_km) const;

    /**
     * @brief Combined filter (single pass for efficiency).
     * 
     * Applies visibility, position angle, and radius filters in a single pass
     * to minimize cache misses and redundant computations.
     * 
     * @param observer_dir Unit vector pointing from Moon center to observer
     * @param sky_east Unit vector pointing east in sky plane
     * @param sky_north Unit vector pointing north in sky plane
     * @param target_pa_deg Target position angle in degrees
     * @param pa_tolerance_deg Position angle tolerance in degrees
     * @param min_radius_km Minimum projected radius in kilometers
     * @return New point cloud containing points passing all filters
     */
    LolaPointCloud filter_combined(
        const Vec3& observer_dir,
        const Vec3& sky_east,
        const Vec3& sky_north,
        double target_pa_deg,
        double pa_tolerance_deg,
        double min_radius_km) const;

    /**
     * @brief Convert Cartesian coordinates to spherical coordinates.
     * 
     * @return Spherical coordinates (longitude, latitude, radius)
     */
    SphericalCoords to_spherical() const;

    /**
     * @brief Project points onto sky plane.
     * 
     * @param observer_dir Unit vector pointing from Moon center to observer
     * @param sky_east Unit vector pointing east in sky plane
     * @param sky_north Unit vector pointing north in sky plane
     * @return Sky plane projection with east, north, radius, and position angle
     */
    SkyPlaneProjection project_to_sky_plane(
        const Vec3& observer_dir,
        const Vec3& sky_east,
        const Vec3& sky_north) const;
};

/**
 * @brief Spherical coordinates (longitude, latitude, radius).
 */
struct SphericalCoords {
    std::vector<double> lon_deg;    // Longitude in degrees [-180, 180]
    std::vector<double> lat_deg;    // Latitude in degrees [-90, 90]
    std::vector<double> radius_km;  // Radius in kilometers
};

/**
 * @brief Sky-plane projection (east, north, radius, position angle).
 */
struct SkyPlaneProjection {
    std::vector<double> east_km;   // East coordinate in kilometers
    std::vector<double> north_km;  // North coordinate in kilometers
    std::vector<double> radius_km; // Projected radius in kilometers
    std::vector<double> pa_deg;    // Position angle in degrees [0, 360)
};

/**
 * @brief Binned point cloud data.
 */
struct BinnedPoints {
    std::vector<int> bin_indices;  // Bin index for each point
    std::vector<double> radius_km; // Projected radius for each point
    std::vector<double> pa_deg;    // Position angle for each point
    std::vector<size_t> original_indices; // Index into original point cloud
};

/**
 * @brief Maximum radius per angular bin.
 */
struct MaxPerBin {
    std::vector<int> bins;         // Bin indices
    std::vector<double> radii_km;  // Maximum radius in each bin
    std::vector<size_t> point_indices; // Index into original point cloud for best point
};

/**
 * @brief 2D point for convex hull computation.
 */
struct Point2D {
    double x;
    double y;

    Point2D(double x_ = 0.0, double y_ = 0.0) : x(x_), y(y_) {}

    bool operator<(const Point2D& other) const {
        return x < other.x || (x == other.x && y < other.y);
    }

    bool operator==(const Point2D& other) const {
        return x == other.x && y == other.y;
    }
};

// ============================================================================
// Vector Operations
// ============================================================================

/**
 * @brief Bulk vector normalization (SIMD-optimized).
 * 
 * Normalizes count 3D vectors to unit length.
 * 
 * @param x_in Input X coordinates
 * @param y_in Input Y coordinates
 * @param z_in Input Z coordinates
 * @param x_out Output X coordinates (normalized)
 * @param y_out Output Y coordinates (normalized)
 * @param z_out Output Z coordinates (normalized)
 * @param count Number of vectors
 * 
 * Note: Zero vectors are returned as (0, 0, 0) without error.
 */
void normalize_vectors_bulk(
    const double* x_in, const double* y_in, const double* z_in,
    double* x_out, double* y_out, double* z_out,
    size_t count);

/**
 * @brief Bulk dot product with single reference vector.
 * 
 * Computes dot product of count vectors with a single reference vector.
 * 
 * @param x Input X coordinates
 * @param y Input Y coordinates
 * @param z Input Z coordinates
 * @param reference Reference vector
 * @param results Output dot products
 * @param count Number of vectors
 */
void dot_product_bulk(
    const double* x, const double* y, const double* z,
    const Vec3& reference,
    double* results,
    size_t count);

/**
 * @brief Bulk cross product with single reference vector.
 * 
 * Computes cross product of count vectors with a single reference vector.
 * 
 * @param x Input X coordinates
 * @param y Input Y coordinates
 * @param z Input Z coordinates
 * @param reference Reference vector
 * @param x_out Output X coordinates
 * @param y_out Output Y coordinates
 * @param z_out Output Z coordinates
 * @param count Number of vectors
 */
void cross_product_bulk(
    const double* x, const double* y, const double* z,
    const Vec3& reference,
    double* x_out, double* y_out, double* z_out,
    size_t count);

/**
 * @brief Bulk vector projection onto plane perpendicular to normal.
 * 
 * Projects count vectors onto plane perpendicular to plane_normal.
 * 
 * @param x_in Input X coordinates
 * @param y_in Input Y coordinates
 * @param z_in Input Z coordinates
 * @param plane_normal Plane normal vector (should be unit vector)
 * @param x_out Output X coordinates
 * @param y_out Output Y coordinates
 * @param z_out Output Z coordinates
 * @param count Number of vectors
 */
void project_onto_plane_bulk(
    const double* x_in, const double* y_in, const double* z_in,
    const Vec3& plane_normal,
    double* x_out, double* y_out, double* z_out,
    size_t count);

// ============================================================================
// Coordinate Transformations
// ============================================================================

/**
 * @brief Convert Cartesian to spherical coordinates (bulk).
 * 
 * Converts count Cartesian coordinates (x, y, z) to spherical (lon, lat, radius).
 * 
 * Algorithm:
 * - radius = sqrt(x² + y² + z²)
 * - longitude = atan2(y, x) * 180/π
 * - latitude = asin(z / radius) * 180/π (clamped to [-1, 1])
 * 
 * @param x Input X coordinates
 * @param y Input Y coordinates
 * @param z Input Z coordinates
 * @param lon_deg Output longitude in degrees [-180, 180]
 * @param lat_deg Output latitude in degrees [-90, 90]
 * @param radius_km Output radius in kilometers
 * @param count Number of points
 */
void cartesian_to_spherical_bulk(
    const double* x, const double* y, const double* z,
    double* lon_deg, double* lat_deg, double* radius_km,
    size_t count);

/**
 * @brief Convert spherical to Cartesian coordinates (bulk).
 * 
 * Converts count spherical coordinates (lon, lat, radius) to Cartesian (x, y, z).
 * 
 * @param lon_deg Input longitude in degrees
 * @param lat_deg Input latitude in degrees
 * @param radius_km Input radius in kilometers
 * @param x Output X coordinates
 * @param y Output Y coordinates
 * @param z Output Z coordinates
 * @param count Number of points
 */
void spherical_to_cartesian_bulk(
    const double* lon_deg, const double* lat_deg, const double* radius_km,
    double* x, double* y, double* z,
    size_t count);

/**
 * @brief Normalize longitude to [-180, 180] degrees (bulk).
 * 
 * @param lon_deg Longitude values to normalize (modified in place)
 * @param count Number of values
 */
void normalize_longitude_bulk(double* lon_deg, size_t count);

// ============================================================================
// Sorting and Binning
// ============================================================================

/**
 * @brief Assign points to angular bins based on position angle.
 * 
 * @param pa_deg Position angles in degrees
 * @param target_pa_deg Center of the binning window
 * @param bin_width_deg Width of each bin
 * @param count Number of points
 * @return Vector of bin indices (relative to target)
 */
std::vector<int> bin_by_position_angle(
    const double* pa_deg, 
    double target_pa_deg, 
    double bin_width_deg, 
    size_t count);

/**
 * @brief Select point with maximum radius in each bin.
 * 
 * @param bin_indices Bin index for each point
 * @param radius_km Projected radius for each point
 * @param count Number of points
 * @return MaxPerBin structure containing best points
 */
MaxPerBin select_max_radius_per_bin(
    const int* bin_indices, 
    const double* radius_km, 
    size_t count);

/**
 * @brief Sort indices by (bin_index, -radius) using stable sort.
 * 
 * @param bin_indices Bin index for each point
 * @param radius_km Projected radius for each point
 * @param count Number of points
 * @return Vector of sorted indices (lexsort behavior)
 */
std::vector<size_t> lexsort_by_bin_and_radius(
    const int* bin_indices, 
    const double* radius_km, 
    size_t count);

// ============================================================================
// Convex Hull
// ============================================================================

/**
 * @brief Compute 2D convex hull using Andrew's monotone chain algorithm.
 * 
 * Time complexity: O(n log n) dominated by sorting.
 * 
 * Degenerate cases:
 * - Empty input: returns empty hull
 * - Single point: returns that point
 * - Two points: returns both points
 * - Collinear points: hull is the two extreme points
 * 
 * @param points Input 2D points
 * @return Convex hull vertices in counter-clockwise order
 */
std::vector<Point2D> convex_hull_2d(const std::vector<Point2D>& points);

/**
 * @brief Cross product for 2D points (used in hull computation).
 * 
 * Computes the z-component of the cross product (O-A) × (O-B).
 * Positive result means counter-clockwise turn from O-A to O-B.
 * 
 * @param O Origin point
 * @param A First point
 * @param B Second point
 * @return Cross product z-component
 */
inline double cross_2d(const Point2D& O, const Point2D& A, const Point2D& B) {
    return (A.x - O.x) * (B.y - O.y) - (A.y - O.y) * (B.x - O.x);
}

// ============================================================================
// Ray-Hull Intersection
// ============================================================================

/**
 * @brief Compute intersection of ray from origin with convex hull.
 * 
 * Returns maximum radius where ray intersects hull.
 * 
 * Algorithm:
 * - Test ray against each hull edge
 * - Solve: t*ray = start + u*edge using Cramer's rule
 * - Return maximum t where t >= 0 and 0 <= u <= 1
 * 
 * @param hull Convex hull vertices
 * @param position_angle_deg Position angle in degrees (0° = north, 90° = east)
 * @param fallback_radius_km Fallback radius if no intersection found
 * @return Intersection radius in kilometers
 */
double ray_hull_intersection(
    const std::vector<Point2D>& hull,
    double position_angle_deg,
    double fallback_radius_km);

} // namespace lola
} // namespace native
} // namespace moira

#endif // MOIRA_NATIVE_LOLA_HPP
