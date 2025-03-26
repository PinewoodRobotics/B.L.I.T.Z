use std::collections::HashSet;

use kiss3d::nalgebra::Vector2;
use nalgebra::{Isometry3, Matrix4, Point3, Vector3};
use rstar::RTree;

///
/// Having a point in the lidar's frame and a transform matrix (lidar in robot) transform point to the robot's frame
///
pub fn transform_point(point: &Vector3<f64>, transform: &Matrix4<f64>) -> Vector3<f64> {
    let p4 = transform * Vector3::new(point.x, point.y, point.z).push(1.0);
    Vector3::new(p4.x, p4.y, p4.z)
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
