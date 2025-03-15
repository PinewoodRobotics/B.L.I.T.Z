use lidar_rs::PointUnitree;
use nalgebra::{Matrix4, UnitVector3, Vector3};

pub fn to_transformation_matrix(
    position_in_robot: Vector3<f64>,
    direction_in_robot: Vector3<f64>,
) -> Matrix4<f64> {
    let direction = UnitVector3::new_normalize(direction_in_robot);

    let up = Vector3::new(0.0, 0.0, 1.0);
    let right = direction.cross(&up).normalize();
    let new_up = direction.cross(&right);

    Matrix4::new(
        right.x,
        new_up.x,
        direction.x,
        position_in_robot.x,
        right.y,
        new_up.y,
        direction.y,
        position_in_robot.y,
        right.z,
        new_up.z,
        direction.z,
        position_in_robot.z,
        0.0,
        0.0,
        0.0,
        1.0,
    )
}

pub fn to_robot_coordinates(pt: PointUnitree) -> PointUnitree {
    // robot coordinates: Forward: -z, right: +x, down: +y
    // lidar coordinates: Forward: +x, right: +y, up: +z
    PointUnitree {
        x: pt.y,
        y: -pt.z,
        z: -pt.x,
        intensity: pt.intensity,
        time: pt.time,
        ring: pt.ring,
    }
}
