use std::fs;
use std::io;

use crate::config::SystemConfig;

pub fn get_system_name() -> io::Result<String> {
    fs::read_to_string("system_data/name.txt").map(|s| s.trim().to_string())
}

pub fn load_system_config() -> Result<SystemConfig, Box<dyn std::error::Error>> {
    let config_str = fs::read_to_string("system_data/basic_system_config.json")?;
    let config: SystemConfig = serde_json::from_str(&config_str)?;

    Ok(config)
}
