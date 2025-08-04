use clap::{Parser, Subcommand};
use common_core::{
    autobahn::{Address, Autobahn},
    config::from_uncertainty_config,
    device_info::load_system_config,
    thrift::{config::Config, lidar::LidarConfig},
};

use crate::grid::Grid;

pub mod astar;
pub mod grid;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(short, long)]
    config: Option<String>,
}

fn get_lidar_config(config: &Config, current_pi: &str) -> Vec<(String, LidarConfig)> {
    let mut output_lidar_configs = Vec::new();
    for (key, lidar_config) in config.lidar_configs.iter() {
        if lidar_config.pi_to_run_on == current_pi {
            output_lidar_configs.push((key.clone(), lidar_config.clone()));
        }
    }

    output_lidar_configs
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let system_config = load_system_config()?;
    let config = from_uncertainty_config(args.config.as_deref())?;

    let autobahn = Autobahn::new_default(Address::new(
        system_config.autobahn.host,
        system_config.autobahn.port,
    ));
    autobahn.begin().await?;

    let pathfind_config = config.pathfinding;

    let grid = Grid::from_map_data(pathfind_config.map_data);

    return Ok(());
}
