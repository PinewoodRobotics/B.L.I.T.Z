#ifndef SPHERICAL_MAP_H
#define SPHERICAL_MAP_H

#include <algorithm>
#include <cmath>
#include <vector>

#include "frustum.h"
#include "timed_point.h"
#include "vector3.h"

class SphericalMap {
 public:
  SphericalMap(double existenceTimeMs, double pointCleanIntervalMs)
      : maxPointExistenceTimeMs(existenceTimeMs),
        pointCleanIntervalMs(pointCleanIntervalMs),
        lastCleanTimeMs(0) {}

  void addPoint(double x, double y, double z, double timestamp) {
    TimedPointXYZ point = {x, y, z, timestamp};
    points.push_back(point);

    if (timestamp - lastCleanTimeMs > pointCleanIntervalMs) {
      cleanOldPoints(timestamp);
      lastCleanTimeMs = timestamp;
    }
  }

  const std::vector<TimedPointXYZ> queryPointsInFrustum(
      const Frustum& frustum) const {
    std::vector<TimedPointXYZ> result;

    for (const auto& point : points) {
      if (frustum.isPointInside(Vec3(point.x, point.y, point.z))) {
        result.push_back(point);
      }
    }

    return result;
  }

 private:
  std::vector<TimedPointXYZ> points;
  double maxPointExistenceTimeMs, pointCleanIntervalMs, lastCleanTimeMs;

  void cleanOldPoints(double currentTime) {
    points.erase(
        std::remove_if(points.begin(), points.end(),
                       [this, currentTime](const TimedPointXYZ& point) {
                         return currentTime - point.timestamp >
                                maxPointExistenceTimeMs;
                       }),
        points.end());
  }

  bool isPointInsideFrustum(
      const TimedPointXYZ& point,
      const std::array<std::array<double, 4>, 6>& planes) const {
    for (const auto& plane : planes) {
      double distance = plane[0] * point.x + plane[1] * point.y +
                        plane[2] * point.z + plane[3];
      if (distance < 0) {
        return false;
      }
    }
    return true;
  }
};

#endif  // SPHERICAL_MAP_H