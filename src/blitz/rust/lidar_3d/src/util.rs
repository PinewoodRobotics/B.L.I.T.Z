use std::{collections::HashMap, time};

use nalgebra::{Matrix4, Quaternion, UnitQuaternion, Vector2, Vector3};
use unitree_lidar_l1_rust::bridge::ffi::{ImuRust, PointUnitreeRust};

pub mod imu;
pub mod model;
pub mod point_cloud;

///
/// Having a point in the lidar's frame and a transform matrix (lidar in robot) transform point to the robot's frame
///
pub fn transform_point(point: &Vector3<f32>, transform: &Matrix4<f32>) -> Vector3<f32> {
    let p4 = transform * Vector3::new(point.x, point.y, point.z).push(1.0);
    Vector3::new(p4.x, p4.y, p4.z)
}

pub fn transform_points(points: &Vec<Vector3<f32>>, transform: &Matrix4<f32>) -> Vec<Vector3<f32>> {
    points
        .iter()
        .map(|point| transform_point(point, transform))
        .collect()
}

pub fn filter_all_limited(
    point: &Vector3<f64>,
    min_z: f64,
    max_z: f64,
    max_dist: f64,
    min_dist: f64,
) -> bool {
    let dist_sq = point.x.powi(2) + point.y.powi(2) + point.z.powi(2);

    (point.z < min_z || point.z > max_z)
        && dist_sq >= min_dist.powi(2)
        && dist_sq <= max_dist.powi(2)
}

pub fn to_2d(point: Vector3<f64>) -> Vector2<f64> {
    Vector2::new(point.x, point.y)
}
