namespace py config

include "./apriltag/apriltag.thrift"
include "./camera/camera.thrift"
include "./lidar/lidar.thrift"
include "./pos_extrapolator/pos_extrapolator.thrift"
include "./pathfinding/pathfinding.thrift"

struct Config {
    1: required pos_extrapolator.PosExtrapolator pos_extrapolator,
    2: required list<camera.CameraParameters> cameras,
    3: required map<string, lidar.LidarConfig> lidar_configs,
    4: required apriltag.AprilDetectionConfig april_detection,
    5: required pathfinding.PathfindingConfig pathfinding,
    6: required bool record_replay,
    7: required string replay_folder_path,
}