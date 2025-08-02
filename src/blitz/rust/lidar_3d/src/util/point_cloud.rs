use std::{
    collections::HashMap,
    time::{Duration, Instant},
};

use common_core::math::to_transformation_matrix_vec_matrix;
use nalgebra::{Matrix, Matrix3, Vector3};
use unitree_lidar_l1_rust::bridge::ffi::{ImuRust, PointUnitreeRust};

use crate::util::{imu::ImuPositionVelocityEstimator, model::UpdateModel, transform_points};

struct PointCloudUndistort {
    all_lidar_points: Vec<Vector3<f32>>,
    imu_position_velocity_estimator: ImuPositionVelocityEstimator,
    last_measurement_position: Vector3<f32>,
    measurement_collection_duration: Duration,
    last_reset_time: Instant,
}

impl PointCloudUndistort {
    pub fn new(measurement_collection_duration: Duration) -> Self {
        Self {
            all_lidar_points: Vec::new(),
            imu_position_velocity_estimator: ImuPositionVelocityEstimator::new(Duration::new(
                10, 0,
            )),
            last_measurement_position: Vector3::zeros(),
            measurement_collection_duration,
            last_reset_time: Instant::now(),
        }
    }
}

impl UpdateModel<ImuRust, ()> for PointCloudUndistort {
    fn update(&mut self, imu: &ImuRust) {
        self.last_measurement_position = self.imu_position_velocity_estimator.get();
        self.imu_position_velocity_estimator.update(imu);
    }

    fn get(&self) {}

    fn reset(&mut self, reset_time: Instant) {
        self.imu_position_velocity_estimator.reset(reset_time);
    }
}

impl UpdateModel<Vec<Vector3<f32>>, Vec<Vector3<f32>>> for PointCloudUndistort {
    fn update(&mut self, points: &Vec<Vector3<f32>>) -> Vec<Vector3<f32>> {
        let current_time = Instant::now();
        let time_since_last_reset = current_time.duration_since(self.last_reset_time);
        if time_since_last_reset > self.measurement_collection_duration {
            return self.reset(current_time);
        }

        let current_position = self.imu_position_velocity_estimator.get();
        let delta_position = current_position - self.last_measurement_position;

        let transformed_points = transform_points(
            points,
            &to_transformation_matrix_vec_matrix(-delta_position, Matrix3::identity()),
        );
        self.all_lidar_points.extend(transformed_points);
        return self.all_lidar_points.clone();
    }

    fn get(&self) -> Vec<Vector3<f32>> {
        self.all_lidar_points.clone()
    }

    fn reset(&mut self, reset_time: Instant) -> Vec<Vector3<f32>> {
        let tmp = self.all_lidar_points.clone();
        self.all_lidar_points = Vec::new();
        tmp
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn get_imu_data() -> Vec<ImuRust> {
        // Frame 1: at t = 0.0 s, starting at rest
        let imu1 = ImuRust {
            stamp: 0.0,
            id: 0,
            quaternion: [0.0, 0.0, 0.0, -1.0],
            linear_acceleration: [0.0, 0.0, -9.81],
            angular_velocity: [0.0, 0.0, 0.0],
        };
        // → time = 0.0 s, velocity = [0.0, 0.0, 0.0] m/s

        // Frame 2: at t = 1.0 s, accel = +1 m/s² on X
        let imu2 = ImuRust {
            stamp: 1.0,
            id: 0,
            quaternion: [0.0, 0.0, 0.0, -1.0],
            linear_acceleration: [1.0, 0.0, -9.81],
            angular_velocity: [0.0, 0.0, 0.0],
        };
        // → time = 1.0 s, velocity = [1.0, 0.0, 0.0] m/s

        vec![imu1, imu2]
    }

    fn get_point_cloud_data() -> Vec<Vec<Vector3<f32>>> {
        vec![
            vec![
                Vector3::new(1.0, 2.0, 3.0),
                Vector3::new(2.0, 3.0, 4.0),
                Vector3::new(3.0, 4.0, 5.0),
            ],
            vec![
                Vector3::new(1.5, 2.5, 3.5),
                Vector3::new(2.5, 3.5, 4.5),
                Vector3::new(3.5, 4.5, 5.5),
            ],
        ]
    }

    #[test]
    fn test_point_cloud_undistort() {
        let mut point_cloud_undistort = PointCloudUndistort::new(Duration::from_secs(1));
        let imu_data = get_imu_data();
        let point_cloud_data = get_point_cloud_data();
        for (imu, points) in imu_data.iter().zip(point_cloud_data.iter()) {
            point_cloud_undistort.update(imu);
            point_cloud_undistort.update(points);
        }

        let out: Vec<Vector3<f32>> = point_cloud_undistort.reset(Instant::now());
        assert_eq!(
            out,
            vec![
                Vector3::new(1.0, 2.0, 3.0),
                Vector3::new(2.0, 3.0, 4.0),
                Vector3::new(3.0, 4.0, 5.0),
                Vector3::new(0.5, 2.5, 3.5),
                Vector3::new(1.5, 3.5, 4.5),
                Vector3::new(2.5, 4.5, 5.5),
            ]
        );
    }
}
