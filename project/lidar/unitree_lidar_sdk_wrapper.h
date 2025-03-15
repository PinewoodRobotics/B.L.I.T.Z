#pragma once

#include "unitree_lidar_sdk.h"

extern "C" {
unitree_lidar_sdk::UnitreeLidarReader* createUnitreeLidarReaderCpp();

int initialize(unitree_lidar_sdk::UnitreeLidarReader* reader,
               uint16_t cloud_scan_num, const char* port, uint32_t baudrate,
               float rotate_yaw_bias, float range_scale, float range_bias,
               float range_max, float range_min);

unitree_lidar_sdk::MessageType runParse(
    unitree_lidar_sdk::UnitreeLidarReader* reader);

void getCloud(unitree_lidar_sdk::UnitreeLidarReader* reader,
              unitree_lidar_sdk::PointCloudUnitree* cloud);

void getVersionOfFirmware(unitree_lidar_sdk::UnitreeLidarReader* reader,
                          char* buffer, size_t buffer_size);

void getVersionOfSDK(unitree_lidar_sdk::UnitreeLidarReader* reader,
                     char* buffer, size_t buffer_size);

void reset(unitree_lidar_sdk::UnitreeLidarReader* reader);

void setLidarWorkingMode(unitree_lidar_sdk::UnitreeLidarReader* reader,
                         unitree_lidar_sdk::LidarWorkingMode mode);

void delete_reader(unitree_lidar_sdk::UnitreeLidarReader* reader);
}
