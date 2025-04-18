include "../common/common.thrift"

namespace py thrift.camera

struct CameraParameters {
    1: required string pi_to_run_on,
    2: required string name,
    3: required common.Matrix3x3 camera_matrix,
    4: required common.Vector5D dist_coeff,
    5: required string camera_path,
    6: required i32 max_fps,
    7: required i32 width,
    8: required i32 height,
    9: required i32 flags,
    10: required i32 exposure_time,
}