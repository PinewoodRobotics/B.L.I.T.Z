include "../common/common.thrift"

namespace py thrift.lidar

struct LidarConfig {
    1: required string pi_to_run_on,
    2: required string port,
    3: required i32 baudrate,
    4: required bool is_2d,
    5: required double min_distance_meters,
    6: required double max_distance_meters,
    7: required common.Vector3D position_in_robot,
    8: required common.Matrix3x3 rotation_in_robot,
}