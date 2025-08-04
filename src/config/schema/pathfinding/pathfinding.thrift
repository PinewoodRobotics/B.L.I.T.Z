include "../common/common.thrift"

namespace py config.pathfinding

struct LidarConfig {
    1: required bool use_lidar,
    2: required double lidar_voxel_size_meters,
    3: required string lidar_pub_topic,
    4: required common.UnitConversion unit_conversion,
}

struct OthersConfig {
    1: required bool use_other_robot_positions,
    2: required common.UnitConversion unit_conversion,
}

struct PathfindingConfig {
    1: required common.MapData map_data,
    2: required LidarConfig lidar_config,
    3: required OthersConfig others_config,
    4: required bool publish_map,
    5: required string map_pub_topic,
}