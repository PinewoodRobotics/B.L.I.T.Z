#include <pcl/point_types.h>
#include <pcl/visualization/pcl_visualizer.h>

#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <queue>
#include <thread>

#include "unitree_lidar_sdk.h"

// Thread-safe queue for point clouds
std::queue<pcl::PointCloud<pcl::PointXYZI>::Ptr> cloudQueue;
std::mutex queueMutex;
std::condition_variable queueCondVar;

void readLidar(unitree_lidar_sdk::UnitreeLidarReader *lreader) {
  while (true) {
    unitree_lidar_sdk::MessageType result = lreader->runParse();
    if (result == unitree_lidar_sdk::POINTCLOUD) {
      auto pointCloud = lreader->getCloud();

      if (pointCloud.points.empty()) {
        std::cerr << "No points in the point cloud!" << std::endl;
        continue;
      }

      // Convert to PCL point cloud
      pcl::PointCloud<pcl::PointXYZI>::Ptr cloud(
          new pcl::PointCloud<pcl::PointXYZI>());
      cloud->width = pointCloud.points.size();
      cloud->height = 1;
      cloud->is_dense = true;

      for (const auto &point : pointCloud.points) {
        cloud->points.push_back(
            pcl::PointXYZI{point.y, point.z, point.x, 100.0f});
      }

      // Add the cloud to the queue
      {
        std::lock_guard<std::mutex> lock(queueMutex);
        cloudQueue.push(cloud);
      }
      queueCondVar.notify_one();
    }
  }
}

void visualize(pcl::visualization::PCLVisualizer &viewer) {
  while (!viewer.wasStopped()) {
    pcl::PointCloud<pcl::PointXYZI>::Ptr cloud;

    // Get the latest cloud from the queue
    {
      std::unique_lock<std::mutex> lock(queueMutex);
      queueCondVar.wait(lock, [] { return !cloudQueue.empty(); });
      cloud = cloudQueue.front();
      cloudQueue.pop();
    }

    // Update the visualizer
    viewer.removeAllPointClouds();
    viewer.addPointCloud<pcl::PointXYZI>(cloud, "sample cloud");
    viewer.setPointCloudRenderingProperties(
        pcl::visualization::PCL_VISUALIZER_POINT_SIZE, 1, "sample cloud");

    viewer.spinOnce(100);
  }
}

int main() {
  unitree_lidar_sdk::UnitreeLidarReader *lreader =
      unitree_lidar_sdk::createUnitreeLidarReader();
  if (lreader->initialize(32, "/dev/ttyUSB0") == -1) {
    std::cerr << "Unitree lidar initialization failed! Exiting." << std::endl;
    delete lreader;
    return -1;
  }

  std::cout << "Lidar reader initialized." << std::endl;

  pcl::visualization::PCLVisualizer viewer("3D Viewer");

  viewer.setBackgroundColor(0, 0, 0);
  viewer.addCoordinateSystem(1.0);
  viewer.initCameraParameters();

  lreader->setLidarWorkingMode(unitree_lidar_sdk::NORMAL);

  std::thread lidarThread(readLidar, lreader);
  visualize(viewer);

  lidarThread.join();

  delete lreader;
  return 0;
}
