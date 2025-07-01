#include "unitree_lidar_wrapper.h"
#include "lidar-3d/src/bridge.rs.h"

#include <string>

UnitreeLidarWrapper::UnitreeLidarWrapper()
{
    reader_ = std::unique_ptr<unitree_lidar_sdk::UnitreeLidarReader>(
        unitree_lidar_sdk::createUnitreeLidarReader());
}

UnitreeLidarWrapper::~UnitreeLidarWrapper() = default;

bool UnitreeLidarWrapper::initialize(uint16_t cloud_scan_num, rust::Str port,
                                     uint32_t baudrate, float rotate_yaw_bias,
                                     float range_scale, float range_bias,
                                     float range_max, float range_min)
{
    return reader_->initialize(cloud_scan_num, port.data(), baudrate, rotate_yaw_bias, range_scale, range_bias, range_max, range_min) == -1 ? false : true;
}

MessageTypeRust UnitreeLidarWrapper::run_parse()
{
    if (!reader_)
    {
        return MessageTypeRust::None;
    }

    auto message_type = reader_->runParse();
    return static_cast<MessageTypeRust>(message_type);
}

rust::Vec<PointUnitreeRust> UnitreeLidarWrapper::get_cloud()
{
    rust::Vec<PointUnitreeRust> points;

    if (!reader_)
    {
        return points;
    }

    auto sdk_points = reader_->getCloud();
    for (const auto &sdk_point : sdk_points.points)
    {
        PointUnitreeRust point;
        point.x = sdk_point.x;
        point.y = sdk_point.y;
        point.z = sdk_point.z;
        point.intensity = sdk_point.intensity;
        point.time = sdk_point.time;
        point.ring = sdk_point.ring;
        points.push_back(point);
    }

    return points;
}

ImuRust UnitreeLidarWrapper::get_imu()
{
    ImuRust imu{};

    if (!reader_)
    {
        return imu;
    }

    auto sdk_imu = reader_->getIMU();
    imu.id = sdk_imu.id;
    imu.stamp = sdk_imu.stamp;
    std::copy(sdk_imu.quaternion, sdk_imu.quaternion + 4, imu.quaternion.begin());
    std::copy(sdk_imu.angular_velocity, sdk_imu.angular_velocity + 3, imu.angular_velocity.begin());
    std::copy(sdk_imu.linear_acceleration, sdk_imu.linear_acceleration + 3, imu.linear_acceleration.begin());

    return imu;
}

void UnitreeLidarWrapper::reset()
{
    if (reader_)
    {
        reader_.reset();
    }
}

void UnitreeLidarWrapper::set_lidar_working_mode(LidarWorkingModeRust mode)
{
    if (reader_)
    {
        reader_->setLidarWorkingMode(static_cast<unitree_lidar_sdk::LidarWorkingMode>(mode));
    }
}

rust::String UnitreeLidarWrapper::get_version_of_firmware()
{
    if (!reader_)
    {
        return rust::String("unknown");
    }

    return rust::String(reader_->getVersionOfFirmware());
}

rust::String UnitreeLidarWrapper::get_version_of_sdk()
{
    if (!reader_)
    {
        return rust::String("unknown");
    }

    // Stub implementation
    return rust::String(reader_->getVersionOfSDK());
}

std::unique_ptr<UnitreeLidarWrapper> make_unitree_lidar_reader()
{
    return std::make_unique<UnitreeLidarWrapper>();
}
