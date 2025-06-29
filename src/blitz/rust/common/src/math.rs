use nalgebra::{Matrix3, Matrix4, UnitVector3, Vector3};

use crate::thrift::common::Vector3D;

pub fn to_transformation_matrix(
    position_in_robot: Vector3<f64>,
    direction_in_robot: Vector3<f64>,
) -> Matrix4<f64> {
    let direction = UnitVector3::new_normalize(direction_in_robot).into_inner();
    let up = Vector3::new(0.0, 0.0, 1.0);
    let left = up.cross(&direction).normalize();

    let rotation_matrix = Matrix3::from_columns(&[direction, left, up]);

    let mut transform = Matrix4::identity();
    transform
        .fixed_view_mut::<3, 3>(0, 0)
        .copy_from(&rotation_matrix);
    transform
        .fixed_view_mut::<3, 1>(0, 3)
        .copy_from(&position_in_robot);

    transform
}

pub fn from_thrift_vector(vector: Vector3D) -> Vector3<f64> {
    Vector3::new(vector.k1.into(), vector.k2.into(), vector.k3.into())
}
