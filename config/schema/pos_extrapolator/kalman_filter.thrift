include "../common/common.thrift"

namespace py config.kalman_filter

struct KalmanFilterSensorConfig {
    1: required common.Matrix6x6 measurement_noise_matrix,
    2: required common.Matrix6x6 measurement_conversion_matrix,
}

enum KalmanFilterSensorType {
    APRIL_TAG,
    ODOMETRY,
    IMU,
}

struct KalmanFilterConfig {
    1: required common.Vector6D state_vector,
    2: required common.Matrix6x6 state_transition_matrix,
    3: required common.Matrix6x6 uncertainty_matrix,
    4: required common.Matrix6x6 process_noise_matrix,
    5: required double time_step_initial,
    6: required map<KalmanFilterSensorType, map<string, KalmanFilterSensorConfig>> sensors,
    7: required list<i32> dim_x_z,
}