use nalgebra::{Matrix1, Matrix2, Quaternion, RowVector2, UnitQuaternion, Vector2, Vector3};
use std::time::{self, Duration, Instant};
use unitree_lidar_l1_rust::bridge::ffi::ImuRust;

use crate::util::model::UpdateModel;

use std::sync::LazyLock;

static GRAVITY: LazyLock<Vector3<f32>> = LazyLock::new(|| Vector3::new(0.0, 0.0, 9.81));

pub struct VelEstimator {
    prev_stamp: Option<time::Duration>,
    velocity: Vector3<f32>,
    max_dt: f32,
}

impl VelEstimator {
    pub fn new(start_stamp: time::Duration) -> Self {
        let dt = 0.01;

        VelEstimator {
            prev_stamp: Some(start_stamp),
            velocity: Vector3::zeros(),
            max_dt: 0.1, // 100ms max - reset if larger gaps
        }
    }

    pub fn reset_velocity(&mut self) {
        self.velocity = Vector3::zeros();
        println!("Manually reset velocity to zero");
    }
}

impl UpdateModel<ImuRust, Vector3<f32>> for VelEstimator {
    fn update(&mut self, imu: &ImuRust) -> Vector3<f32> {
        if self.prev_stamp.is_none() {
            self.prev_stamp = Some(time::Duration::from_secs_f64(imu.stamp));
            return Vector3::zeros();
        }

        let time_imu = time::Duration::from_secs_f64(imu.stamp);
        let dt = time_imu - self.prev_stamp.unwrap();
        let dt_f32 = dt.as_secs_f32();

        if dt_f32 > self.max_dt {
            self.velocity = Vector3::zeros();
            self.prev_stamp = Some(time_imu);
            return Vector3::zeros();
        }

        self.prev_stamp = Some(time_imu);

        let q = UnitQuaternion::from_quaternion(Quaternion::new(
            imu.quaternion[3],
            imu.quaternion[0],
            imu.quaternion[1],
            imu.quaternion[2],
        ));
        let a_body = Vector3::new(
            imu.linear_acceleration[0],
            imu.linear_acceleration[1],
            imu.linear_acceleration[2],
        );
        let a_world = q.transform_vector(&a_body);

        let a_net = a_world - *GRAVITY;

        let velocity_delta = a_net * dt_f32;
        self.velocity += velocity_delta;

        let vel_magnitude = self.velocity.magnitude();
        if vel_magnitude > 100.0 {
            println!(
                "Velocity magnitude too large: {:.3} m/s - resetting",
                vel_magnitude
            );
            self.velocity = Vector3::zeros();
        }

        self.velocity
    }

    fn get(&self) -> Vector3<f32> {
        self.velocity
    }

    fn reset(&mut self, reset_time: Instant) -> Vector3<f32> {
        self.prev_stamp = Some(reset_time.duration_since(reset_time));
        self.velocity = Vector3::zeros();
        self.velocity
    }
}

pub struct ImuPositionVelocityEstimator {
    last_position: Vector3<f32>,
    last_rotation: Vector3<f32>,
    velocity_estimator: VelEstimator,
    last_time_stamp: Option<Duration>,
}

impl ImuPositionVelocityEstimator {
    pub fn new() -> Self {
        ImuPositionVelocityEstimator {
            last_position: Vector3::zeros(),
            last_rotation: Vector3::zeros(),
            velocity_estimator: VelEstimator::new(time::Duration::new(0, 0)),
            last_time_stamp: None,
        }
    }
}

impl UpdateModel<ImuRust, Vector3<f32>> for ImuPositionVelocityEstimator {
    /// x(t) = x(t-1) + v(t) * Δt

    fn update(&mut self, imu: &ImuRust) -> Vector3<f32> {
        // println!("imu: {:?}", imu.stamp);
        if self.last_time_stamp.is_none() {
            self.last_time_stamp = Some(Duration::from_secs_f64(imu.stamp));
            return Vector3::zeros();
        }

        let newest_velocity = self.velocity_estimator.update(imu);
        let imu_time_stamp = Duration::from_secs_f64(imu.stamp);
        let delta_time = (imu_time_stamp - self.last_time_stamp.unwrap()).as_secs_f32();
        let delta_position = newest_velocity * delta_time;

        self.last_position += delta_position;
        self.last_rotation += Vector3::from_row_slice(&imu.angular_velocity) * delta_time;

        self.last_position
    }

    fn get(&self) -> Vector3<f32> {
        self.last_position
    }

    fn reset(&mut self, reset_time: Instant) -> Vector3<f32> {
        self.last_position = Vector3::zeros();
        self.velocity_estimator.reset(reset_time);
        self.last_position
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

        // Frame 3: at t = 2.0 s, same accel
        let imu3 = ImuRust {
            stamp: 2.0,
            id: 0,
            quaternion: [0.0, 0.0, 0.0, -1.0],
            linear_acceleration: [1.0, 0.0, -9.81],
            angular_velocity: [0.0, 0.0, 0.0],
        };
        // → time = 2.0 s, velocity = [2.0, 0.0, 0.0] m/s

        // Frame 4: at t = 3.0 s, same accel
        let imu4 = ImuRust {
            stamp: 3.0,
            id: 0,
            quaternion: [0.0, 0.0, 0.0, -1.0],
            linear_acceleration: [1.0, 0.0, -9.81],
            angular_velocity: [0.0, 0.0, 0.0],
        };
        // → time = 3.0 s, velocity = [3.0, 0.0, 0.0] m/s

        vec![imu1, imu2, imu3, imu4]
    }

    #[test]
    fn test_imu_position_velocity_estimator() {
        let mut imu_vel_estimator = VelEstimator::new(time::Duration::new(0, 0));
        let imu_data = get_imu_data();
        for imu in imu_data {
            let velocity = imu_vel_estimator.update(&imu);
            println!("Velocity: {:?}", velocity);
        }

        assert_eq!(imu_vel_estimator.get(), Vector3::new(3.0, 0.0, 0.0));
    }

    #[test]
    fn test_imu_position_velocity_estimator_with_gravity() {
        let mut imu_vel_estimator = ImuPositionVelocityEstimator::new();
        let imu_data = get_imu_data();
        for imu in imu_data {
            let position = imu_vel_estimator.update(&imu);
            println!("Position: {:?}", position);
        }

        assert_eq!(imu_vel_estimator.get(), Vector3::new(6.0, 0.0, 0.0));
    }
}
