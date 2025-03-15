#include <cstring>  // For strcpy
#include <iostream>

#include "unitree_lidar_sdk.h"

using namespace unitree_lidar_sdk;

// This struct matches the Rust PointCloudUnitree with dynamic points
struct PointCloudUnitree_Dynamic {
  double stamp;
  uint32_t id;
  uint32_t ringNum;
  PointUnitree* points_ptr;
  size_t points_len;
  size_t points_capacity;
};

// Create a wrapper struct to store the LiDAR instance
extern "C" {

void getCloud(UnitreeLidarReader* reader, PointCloudUnitree_Dynamic* cloud) {
  if (!reader || !cloud) return;

  // Get the cloud from Unitree SDK
  PointCloudUnitree cloudCpp = reader->getCloud();

  // Copy basic fields
  cloud->stamp = cloudCpp.stamp;
  cloud->id = cloudCpp.id;
  cloud->ringNum = cloudCpp.ringNum;

  // Allocate memory for points if needed
  size_t numPoints = cloudCpp.points.size();

  // Don't free memory here - let Rust handle it
  // The Rust side will check if points_ptr is null before allocating

  if (numPoints > 0) {
    // Allocate memory for the points - use new[] instead of malloc for proper
    // alignment
    cloud->points_ptr = new PointUnitree[numPoints];
    if (cloud->points_ptr) {
      // Copy points
      for (size_t i = 0; i < numPoints; i++) {
        cloud->points_ptr[i] = cloudCpp.points[i];
      }
      cloud->points_len = numPoints;
      cloud->points_capacity = numPoints;
    } else {
      // Allocation failed
      cloud->points_len = 0;
      cloud->points_capacity = 0;
    }
  } else {
    // No points
    cloud->points_ptr = nullptr;
    cloud->points_len = 0;
    cloud->points_capacity = 0;
  }
}

void freePointCloudMemory(PointUnitree* points_ptr) {
  if (points_ptr) {
    delete[] points_ptr;
  }
}

// Create a new LiDAR instance
UnitreeLidarReader* createUnitreeLidarReaderCpp() {
  return createUnitreeLidarReader();
}

// Initialize the LiDAR
int initialize(UnitreeLidarReader* reader, uint16_t cloud_scan_num,
               const char* port, uint32_t baudrate, float rotate_yaw_bias,
               float range_scale, float range_bias, float range_max,
               float range_min) {
  if (!reader) return -1;
  try {
    return reader->initialize(cloud_scan_num, std::string(port), baudrate,
                              rotate_yaw_bias, range_scale, range_bias,
                              range_max, range_min);
  } catch (const std::exception& e) {
    std::cerr << "Error initializing LiDAR: " << e.what() << std::endl;
    return -1;
  }
}

// Run parsing
MessageType runParse(UnitreeLidarReader* reader) {
  if (!reader) return MessageType::NONE;
  return reader->runParse();
}

// Get firmware version
void getVersionOfFirmware(UnitreeLidarReader* reader, char* buffer,
                          size_t buffer_size) {
  if (!reader || !buffer) return;
  std::string version = reader->getVersionOfFirmware();
  strncpy(buffer, version.c_str(), buffer_size - 1);
  buffer[buffer_size - 1] = '\0';
}

// Get SDK version
void getVersionOfSDK(UnitreeLidarReader* reader, char* buffer,
                     size_t buffer_size) {
  if (!reader || !buffer) return;
  std::string version = reader->getVersionOfSDK();
  strncpy(buffer, version.c_str(), buffer_size - 1);
  buffer[buffer_size - 1] = '\0';
}

// Reset the LiDAR
void reset(UnitreeLidarReader* reader) {
  if (!reader) return;
  reader->reset();
}

// Set LiDAR working mode
void setLidarWorkingMode(UnitreeLidarReader* reader, LidarWorkingMode mode) {
  if (!reader) return;
  reader->setLidarWorkingMode(mode);
}

// Delete the LiDAR instance
void delete_reader(UnitreeLidarReader* reader) {
  if (reader) {
    delete reader;
  }
}

}  // extern "C"
