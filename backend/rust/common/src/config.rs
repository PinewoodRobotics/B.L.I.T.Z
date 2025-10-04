use std::{fs::File, io::BufReader, process::Command};

use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};
use nalgebra::Vector3;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use thrift::{
    protocol::{TBinaryInputProtocol, TSerializable},
    transport::TBufferChannel,
};

use crate::thrift::config::Config;

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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigGetterOutput {
    pub json: String,
    pub binary_base64: String,
}

pub fn load_config() -> Result<Config, Box<dyn std::error::Error>> {
    let config_json = get_config_raw()?;
    let config_output: ConfigGetterOutput = serde_json::from_str(&config_json)?;
    from_base64(&config_output.binary_base64)
}

pub fn get_config_raw() -> Result<String, Box<dyn std::error::Error>> {
    let output = Command::new("npm")
        .args(&["run", "config", "--silent"])
        .output()?;

    let output_stdout = String::from_utf8_lossy(&output.stdout);

    if !output.status.success() {
        return Err(format!("npm run config failed with status: {}", output.status).into());
    }

    Ok(output_stdout.trim().to_string())
}

pub fn from_file(file_path: &str) -> Result<Config, Box<dyn std::error::Error>> {
    let config_json = std::fs::read_to_string(file_path)?;
    from_base64(&config_json)
}

pub fn from_uncertainty_config(
    file_path: Option<&str>,
) -> Result<Config, Box<dyn std::error::Error>> {
    match file_path {
        Some(path) => from_file(path),
        None => load_config(),
    }
}

pub fn from_base64(base64_str: &str) -> Result<Config, Box<dyn std::error::Error>> {
    let buffer = BASE64.decode(base64_str)?;

    let mut transport = TBufferChannel::with_capacity(buffer.len(), buffer.len());
    transport.set_readable_bytes(&buffer);

    let mut protocol = TBinaryInputProtocol::new(transport, true);

    let config = Config::read_from_in_protocol(&mut protocol)?;
    Ok(config)
}

#[cfg(test)]
mod tests {
    use crate::thrift::camera::CameraType;

    use super::*;

    const CONFIG_PATH: &str = "fixtures/sample_config.txt";

    fn test_config(config: Config) {
        assert_eq!(config.cameras.len(), 1);
        assert_eq!(config.cameras[0].name, "one");
        assert_eq!(config.cameras[0].camera_path, "/dev/video0");
        assert_eq!(config.cameras[0].flags, 0);
        assert_eq!(config.cameras[0].width, 800);
        assert_eq!(config.cameras[0].height, 600);
        assert_eq!(config.cameras[0].camera_type, CameraType::OV2311);
    }

    #[test]
    fn test_load_config() {
        let config = load_config().unwrap();
    }

    #[test]
    fn test_from_file() {
        let config = from_file(CONFIG_PATH).unwrap();
        test_config(config);
    }

    #[test]
    fn test_from_uncertainty_config() {
        let config = from_uncertainty_config(Some(CONFIG_PATH));

        assert!(config.is_ok());
        test_config(config.unwrap());
    }
}
