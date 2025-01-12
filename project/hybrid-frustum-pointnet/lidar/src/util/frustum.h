#ifndef FRUSTUM_H
#define FRUSTUM_H

#include <array>
#include <cassert>
#include <vector>

#include "vector3.h"

struct Plane {
  Vec3 normal;
  float distance;  // Signed distance from origin

  Plane(const Vec3& normal, float distance)
      : normal(normal.normalized()), distance(distance) {}

  float signedDistance(const Vec3& point) const {
    return normal.dot(point) - distance;
  }
};

class Frustum {
 public:
  Frustum(const Vec3& origin, const std::array<Vec3, 4>& corners)
      : origin(origin), corners(corners) {
    assert(corners.size() == 4 && "Corners must contain exactly 4 points!");

    for (size_t i = 0; i < corners.size(); ++i) {
      const Vec3& current = corners[i];
      const Vec3& next = corners[(i + 1) % corners.size()];

      // Calculate edges
      Vec3 edge1 = current - origin;
      Vec3 edge2 = next - origin;

      // Calculate normal for the plane
      Vec3 normal = edge1.cross(edge2).normalized();

      // Ensure the normal points inward
      if (normal.dot(corners[(i + 2) % corners.size()] - origin) > 0) {
        normal = -normal;  // Flip the normal
      }

      // Calculate signed distance from the origin
      float distance = normal.dot(origin);
      planes.emplace_back(normal, distance);
    }
  }

  bool isPointInside(const Vec3& point) const {
    for (const auto& plane : planes) {
      if (plane.signedDistance(point) > 0) {
        return false;  // Point is outside this plane
      }
    }

    return true;  // Point is inside all planes
  }

 private:
  std::vector<Plane> planes;
  Vec3 origin;
  std::array<Vec3, 4> corners;
};

#endif  // FRUSTUM_H
