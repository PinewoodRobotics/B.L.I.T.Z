#include <cstring>  // For strcpy
#include <iostream>

#include "unitree_lidar_sdk.h"

using namespace unitree_lidar_sdk;

struct PointCloudUnitree_Fixed {
  double stamp;
  uint32_t id;
  uint32_t ringNum;
  PointUnitree points[120];  // FIXED SIZE ARRAY (matches Rust)
};

extern "C" void getCloud(UnitreeLidarReader* reader,
                         PointCloudUnitree_Fixed* cloud) {
  if (!reader || !cloud) return;

  // Get the cloud from Unitree SDK
  PointCloudUnitree cloudCpp = reader->getCloud();

  // Copy fields
  cloud->stamp = cloudCpp.stamp;
  cloud->id = cloudCpp.id;
  cloud->ringNum = cloudCpp.ringNum;

  // Copy points manually
  size_t numPoints = std::min(size_t(120), cloudCpp.points.size());
  for (size_t i = 0; i < numPoints; i++) {
    cloud->points[i] = cloudCpp.points[i];
  }
}

// Create a wrapper struct to store the LiDAR instance
extern "C" {

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
  return reader->initialize(cloud_scan_num, std::string(port), baudrate,
                            rotate_yaw_bias, range_scale, range_bias, range_max,
                            range_min);
}

// Run parsing
MessageType runParse(UnitreeLidarReader* reader) {
  if (!reader) return MessageType::NONE;
  return reader->runParse();
}

// Get point cloud
void getCloud(UnitreeLidarReader* reader, PointCloudUnitree* cloud) {
  if (!reader || !cloud) return;
  *cloud = reader->getCloud();
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
