#ifndef FRUSTUM_H
#define FRUSTUM_H

#include <array>
#include <vector>

#include "vector3.h"

struct Plane {
  Vec3 normal;
  Vec3 point;

  Plane(const Vec3& normal, const Vec3& point)
      : normal(normal.normalized()), point(point) {}

  float signedDistance(const Vec3& p) const { return normal.dot(p - point); }
};

class Frustum {
 public:
  Frustum(const Vec3& origin, const std::array<Vec3, 4>& corners)
      : origin(origin), corners(corners) {
    computePlanes();
  }

  bool isPointInside(const Vec3& point) const {
    for (const auto& plane : planes) {
      if (plane.signedDistance(point) < 0) {
        return false;  // Point is outside this plane
      }
    }
    return true;  // Point is inside all planes
  }

 private:
  std::vector<Plane> planes;
  Vec3 origin;
  std::array<Vec3, 4> corners;

  void computePlanes() {
    Vec3 nearNormal = (corners[1] - corners[0]).cross(corners[2] - corners[0]);
    planes.emplace_back(nearNormal, corners[0]);

    Vec3 farNormal = (corners[2] - corners[3]).cross(corners[1] - corners[3]);
    planes.emplace_back(-farNormal,
                        corners[3]);  // Negate to flip normal direction

    for (size_t i = 0; i < 4; ++i) {
      Vec3 edge1 = corners[i] - origin;
      Vec3 edge2 = corners[(i + 1) % 4] - origin;
      Vec3 sideNormal = edge1.cross(edge2);
      planes.emplace_back(sideNormal, origin);
    }
  }
};

#endif  // FRUSTUM_H