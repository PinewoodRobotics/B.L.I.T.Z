use clap::{Parser, Subcommand};
use common_core::{
    autobahn::{Address, Autobahn},
    config::from_uncertainty_config,
    device_info::load_system_config,
    proto::pathfind::grid::Grid,
    thrift::{config::Config, lidar::LidarConfig},
};
use tokio::time;

use crate::grid::Grid2d;

pub mod astar;
pub mod grid;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(short, long)]
    config: Option<String>,
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

    let grid = Grid2d::from_map_data(pathfind_config.map_data);

    let sigint = tokio::signal::ctrl_c();
    tokio::pin!(sigint);

    loop {
        tokio::select! {
            _ = &mut sigint => {
                break;
            }
            _ = time::sleep(time::Duration::from_millis(100)) => {

                let grid_data = grid.serialize();
                let mut buf = Vec::new();
                Grid::Grid2d(grid_data).encode(&mut buf);
                autobahn
                    .publish(pathfind_config.map_pub_topic.as_str(), buf)
                    .await?;
            }
        }
    }

    return Ok(());
}
