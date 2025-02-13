use std::collections::HashMap;

#[derive(serde::Deserialize)]
pub struct Config {
    pub server: ServerConfig,
    pub others: HashMap<String, OtherConfig>,
    pub debug: Option<bool>,
}

#[derive(serde::Deserialize)]
pub struct ServerConfig {
    pub port: u16,
}

#[derive(serde::Deserialize, Clone)]
pub struct OtherConfig {
    pub port: u16,
    pub ip_addr_v4: String,
}
