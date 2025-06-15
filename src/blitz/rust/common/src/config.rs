use nalgebra::Vector3;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LidarConfig {
    pub pi_to_run_on: String,
    pub port: String,
    pub baudrate: u32,
    pub lidar_name: String,
    pub is_2d: bool,
    pub min_distance_meters: f64,
    pub max_distance_meters: f64,
    pub position_in_robot: Vector3<f64>,
    pub direction_vector_in_robot: Vector3<f64>,
}
