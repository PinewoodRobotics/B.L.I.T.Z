use nalgebra::Vector3;

pub struct PointsGetter2d {
    position_in_robot: Vector3<f64>,
    direction_in_robot: Vector3<f64>,
}

impl PointsGetter2d {
    pub fn new(position_in_robot: Vector3<f64>, direction_in_robot: Vector3<f64>) -> Self {
        Self {
            position_in_robot,
            direction_in_robot,
        }
    }
}
