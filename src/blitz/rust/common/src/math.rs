use nalgebra::{Matrix3, Matrix4, UnitVector3, Vector3};

pub mod proto_to_nalgebra;
pub mod thrift_to_nalgebra;

pub fn to_transformation_matrix(
    position_in_robot: Vector3<f32>,
    direction_in_robot: Vector3<f32>,
) -> Matrix4<f32> {
    let direction = UnitVector3::new_normalize(direction_in_robot).into_inner();
    let up = Vector3::new(0.0, 0.0, 1.0);
    let left = up.cross(&direction).normalize();

    let rotation_matrix = Matrix3::from_columns(&[direction, left, up]);
    to_transformation_matrix_vec_matrix(position_in_robot, rotation_matrix)
}

pub fn to_transformation_matrix_vec_matrix(
    position_in_robot: Vector3<f32>,
    matrix_rotation: Matrix3<f32>,
) -> Matrix4<f32> {
    let mut transform = Matrix4::identity();
    transform
        .fixed_view_mut::<3, 3>(0, 0)
        .copy_from(&matrix_rotation);
    transform
        .fixed_view_mut::<3, 1>(0, 3)
        .copy_from(&position_in_robot);

    transform
}

pub fn to_transformation_matrix_vec_matrix_f64(
    position_in_robot: Vector3<f64>,
    matrix_rotation: Matrix3<f64>,
) -> Matrix4<f32> {
    let mut transform = Matrix4::identity();
    transform
        .fixed_view_mut::<3, 3>(0, 0)
        .copy_from(&matrix_rotation);
    transform
        .fixed_view_mut::<3, 1>(0, 3)
        .copy_from(&position_in_robot);

    transform.map(|x| x as f32)
}
