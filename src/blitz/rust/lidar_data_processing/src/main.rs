use clap::Parser;
use common_core::autobahn::{Address, Autobahn};
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

    Ok(())
}
