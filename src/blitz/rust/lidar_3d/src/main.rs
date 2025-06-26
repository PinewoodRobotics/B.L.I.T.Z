use clap::Parser;
use common_core::autobahn::{Address, Autobahn};
use common_core::config::LidarConfig;
use common_core::math::to_transformation_matrix;
use common_core::proto::sensor::general_sensor_data::Data;
use common_core::proto::sensor::lidar_data;
use common_core::proto::sensor::{GeneralSensorData, SensorName};
use common_core::proto::sensor::{LidarData, PointCloud2d};
use common_core::proto::util::Vector2;
use futures_util::StreamExt;
use point_util::{filter_all_limited, to_2d, transform_point};
use prost::Message;
use std::fs;
use std::path::PathBuf;
use timed_point_map::TimedPointMap;

mod lidar;
mod point_util;
mod timed_point_map;

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

    let mut timed_point_map = TimedPointMap::new(1000);

    let lidar_in_robot_transformation =
        to_transformation_matrix(config.position_in_robot, config.direction_vector_in_robot);

    let mut reader = LidarReader::new_with_initialize(config.clone())?.into_stream();

    while let Some(points) = reader.next().await {
        timed_point_map.add_all(points.clone());

        let points = points
            .iter()
            .filter(|point| {
                filter_all_limited(
                    point,
                    -20.0,
                    20.0,
                    config.max_distance_meters,
                    config.min_distance_meters,
                )
            })
            .map(|point| transform_point(point, &lidar_in_robot_transformation))
            .map(|f| to_2d(f))
            .map(|f| Vector2 {
                x: f.get(0).unwrap().clone() as f32,
                y: f.get(1).unwrap().clone() as f32,
            })
            .collect::<Vec<_>>();

        let general_sensor_data = GeneralSensorData {
            sensor_name: SensorName::Lidar as i32,
            sensor_id: config.lidar_name.clone(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs() as i64,
            data: Some(Data::Lidar(LidarData {
                data: Some(lidar_data::Data::PointCloud2d(PointCloud2d {
                    ranges: points,
                    lidar_id: config.lidar_name.clone(),
                })),
            })),
        };

        let _ = autobahn
            .publish(
                &format!("lidar/lidar3d/pointcloud/2d/robotframe"),
                general_sensor_data.encode_to_vec(),
            )
            .await;
    }

    Ok(())
}
