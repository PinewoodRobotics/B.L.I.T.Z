use clap::Parser;
use common_core::{
    autobahn::{Address, Autobahn},
    config::LidarConfig,
    project_proto::PointCloud2d,
};
use std::{fs, path::PathBuf};

mod pose_graph_with_lidar_data;

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
    let _ = autobahn.begin().await;

    let _ = autobahn
        .subscribe(
            "lidar/lidar3d/pointcloud/2d/robotframe",
            |message: Vec<u8>| async move { () },
        )
        .await;

    Ok(())
}
