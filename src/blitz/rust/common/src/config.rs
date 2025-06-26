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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemConfig {
    pub autobahn: AutobahnConfig,
    pub logging: LoggingConfig,
    pub watchdog: WatchdogConfig,
    pub config_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutobahnConfig {
    pub host: String,
    pub port: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    pub global_log_pub_topic: String,
    pub global_logging_publishing_enabled: bool,
    pub global_logging_level: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WatchdogConfig {
    pub host: String,
    pub port: u16,
    pub stats_pub_period_s: f32,
    pub send_stats: bool,
}
