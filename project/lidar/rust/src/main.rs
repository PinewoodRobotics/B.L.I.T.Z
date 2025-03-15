use autobahn::{Address, Autobahn};
use clap::Parser;
use futures_util::StreamExt;
use std::fs;
use std::path::PathBuf;

mod autobahn;
mod config;
mod device_info;
mod lidar;
mod math;
mod point_util;

use config::LidarConfig;
use lidar::points_getter_2d::PointsGetter2d;
use lidar::reader::LidarReader;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Path to the config file
    #[arg(short, long)]
    config: PathBuf,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let config_str = fs::read_to_string(args.config)?;
    let config: LidarConfig = serde_json::from_str(&config_str)?;

    let autobahn = Autobahn::new(Address::new("localhost", 8080), true, 5.0);
    autobahn.begin().await?;

    let reader = LidarReader::new_with_initialize(config)?;
    let mut stream = reader.into_stream();

    while let Some(points) = stream.next().await {}

    Ok(())
}
