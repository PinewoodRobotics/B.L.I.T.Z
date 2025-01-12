#include <bits/this_thread_sleep.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/visualization/pcl_visualizer.h>

#include <random>

#include "../src/util/frustum.h"
#include "../src/util/vector3.h"

std::vector<Vec3> generateRandomPoints(int rangePlusMinus, Vec3 origin,
                                       int numPoints) {
  std::vector<Vec3> outputPoints;

  std::random_device rd;
  std::mt19937 gen(rd());
  std::uniform_real_distribution<float> dis(-rangePlusMinus, rangePlusMinus);

  for (int i = 0; i < numPoints; i++) {
    float x = origin.x + dis(gen);
    float y = origin.y + dis(gen);
    float z = origin.z + dis(gen);

    outputPoints.push_back(Vec3(x, y, z));
  }

  return outputPoints;
}

int main() {
  // Define the origin and corners of the frustum
  Vec3 origin(0.0f, 0.0f, 0.0f);
  std::array<Vec3, 4> corners = {
      Vec3(-1.0f, 1.0f, -1.0f), Vec3(-1.0f, 1.0f, 1.0f),
      Vec3(-1.0f, -1.0f, 1.0f), Vec3(-1.0f, -1.0f, -1.0f)};

  // Create the frustum
  Frustum frustum(origin, corners);

  // Create a PCL visualizer
  pcl::visualization::PCLVisualizer::Ptr viewer(
      new pcl::visualization::PCLVisualizer("Frustum Viewer"));

  // Add the frustum edges to the visualizer
  for (size_t i = 0; i < corners.size(); ++i) {
    const Vec3& start = corners[i];
    const Vec3& end = corners[(i + 1) % corners.size()];

    viewer->addLine<pcl::PointXYZ>(pcl::PointXYZ(start.x, start.y, start.z),
                                   pcl::PointXYZ(end.x, end.y, end.z),
                                   "edge" + std::to_string(i));
  }

  // Add lines from origin to each corner
  for (size_t i = 0; i < corners.size(); ++i) {
    const Vec3& corner = corners[i];
    viewer->addLine<pcl::PointXYZ>(pcl::PointXYZ(origin.x, origin.y, origin.z),
                                   pcl::PointXYZ(corner.x, corner.y, corner.z),
                                   "origin_to_corner" + std::to_string(i));
  }

  viewer->addSphere<pcl::PointXYZ>(
      pcl::PointXYZ(corners[0].x, corners[0].y, corners[0].z),
      0.1,  // radius
      1, 1,
      0.0,  // blue
      "test_point");

  // Test some points
  std::vector<Vec3> testPoints = generateRandomPoints(4, Vec3(0, 0, 0), 100);

  for (size_t i = 0; i < testPoints.size(); ++i) {
    const Vec3& point = testPoints[i];
    bool inside = frustum.isPointInside(point);

    std::cout << inside << std::endl;

    // Add the test point to the visualizer with different colors based on its
    // status
    viewer->addSphere<pcl::PointXYZ>(pcl::PointXYZ(point.x, point.y, point.z),
                                     0.1,                 // radius
                                     inside ? 0.0 : 1.0,  // red
                                     inside ? 1.0 : 0.0,  // green
                                     0.0,                 // blue
                                     "test_point" + std::to_string(i));
  }

  // Visualizer loop
  viewer->setBackgroundColor(0.1, 0.1, 0.1);
  viewer->addCoordinateSystem(1.0);
  viewer->initCameraParameters();

  while (!viewer->wasStopped()) {
    viewer->spinOnce(100);
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }

  return 0;
}
