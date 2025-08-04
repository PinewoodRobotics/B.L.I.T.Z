namespace py config

include "./autobahn/autobahn.thrift"
include "./apriltag/apriltag.thrift"
include "./camera/camera.thrift"
include "./image_recognition/image_recognition.thrift"
include "./lidar/lidar.thrift"
include "./logger/logger.thrift"
include "./pos_extrapolator/pos_extrapolator.thrift"
include "./watchdog/watchdog.thrift"
include "./pathfinding/pathfinding.thrift"

struct Config {
    1: required autobahn.AutobahnConfig autobahn,
    2: required watchdog.WatchdogConfig watchdog,
    3: required pos_extrapolator.PosExtrapolator pos_extrapolator,
    4: required image_recognition.ImageDetectionConfig image_recognition,
    5: required list<camera.CameraParameters> cameras,
    6: required map<string, lidar.LidarConfig> lidar_configs,
    7: required apriltag.AprilDetectionConfig april_detection,
    8: required pathfinding.PathfindingConfig pathfinding,
    9: required logger.LoggerConfig logger,
}