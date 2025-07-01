#pragma once

#include "rust/cxx.h"
#include "unitree_lidar_sdk.h"
#include <memory>
#include <string>
#include <vector>

struct ImuRust;
struct PointUnitreeRust;

enum class MessageTypeRust : uint8_t;
enum class LidarWorkingModeRust : uint8_t;

class UnitreeLidarWrapper {
public:
  UnitreeLidarWrapper();
  ~UnitreeLidarWrapper();

  bool initialize(uint16_t cloud_scan_num, rust::Str port, uint32_t baudrate,
                  float rotate_yaw_bias, float range_scale, float range_bias,
                  float range_max, float range_min);

  MessageTypeRust run_parse();
  rust::Vec<PointUnitreeRust> get_cloud();
  ImuRust get_imu();
  void reset();
  void set_lidar_working_mode(LidarWorkingModeRust mode);
  rust::String get_version_of_firmware();
  rust::String get_version_of_sdk();

private:
  std::unique_ptr<unitree_lidar_sdk::UnitreeLidarReader> reader_;
};

std::unique_ptr<UnitreeLidarWrapper> make_unitree_lidar_reader();