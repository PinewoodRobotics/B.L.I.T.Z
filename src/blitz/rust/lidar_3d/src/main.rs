use clap::Parser;
use common_core::autobahn::{Address, Autobahn};
use common_core::config::from_uncertainty_config;
use common_core::device_info::{get_system_name, load_system_config};
use common_core::math::to_transformation_matrix_vec_matrix;
use common_core::proto::sensor::general_sensor_data::Data;
use common_core::proto::sensor::LidarData;
use common_core::proto::sensor::{lidar_data, ImuData, PointCloud3d};
use common_core::proto::sensor::{GeneralSensorData, SensorName};
use common_core::proto::util::{Position3d, Vector3};
use common_core::thrift::config::Config;
use common_core::thrift::lidar::LidarConfig;
use futures_util::StreamExt;
use prost::Message;

mod lidar;
mod point_util;
mod timed_point_map;

use lidar::reader::LidarReader;

use crate::lidar::reader::LidarResult;

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
    let current_pi = get_system_name()?;
    println!("Current pi: {}", current_pi);
    let config = from_uncertainty_config(args.config.as_deref())?;

    let autobahn = Autobahn::new_default(Address::new(
        system_config.autobahn.host,
        system_config.autobahn.port,
    ));

    autobahn.begin().await?;

    let lidar_configs = get_lidar_config(&config, &current_pi);

    let (lidar_name, config) = lidar_configs[0].clone(); // TODO: Handle multiple lidars
    let lidar_in_robot_transformation = to_transformation_matrix_vec_matrix(
        config.position_in_robot.into(),
        config.rotation_in_robot.into(),
    );

    let mut reader = LidarReader::new_with_initialize(
        config.port,
        config.baudrate as u32,
        config.min_distance_meters.into(),
        config.max_distance_meters.into(),
    )?;
    reader.start_lidar()?;

    let mut reader = reader.into_stream();
    while let Some(result) = reader.next().await {
        match result {
            LidarResult::PointCloud(points) => {
                let points = points
                    .iter()
                    .map(|point| Vector3 {
                        x: point.x,
                        y: point.y,
                        z: point.z,
                    })
                    .collect::<Vec<_>>();

                let general_sensor_data = GeneralSensorData {
                    sensor_name: SensorName::Lidar as i32,
                    sensor_id: lidar_name.clone(),
                    timestamp: std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_secs() as i64,
                    data: Some(Data::Lidar(LidarData {
                        data: Some(lidar_data::Data::PointCloud3d(PointCloud3d {
                            ranges: points,
                            lidar_id: lidar_name.clone(),
                        })),
                    })),
                };

                println!("Publishing lidar data");

                let _ = autobahn
                    .publish(
                        &format!("lidar/lidar3d/pointcloud/3d/robotframe"),
                        general_sensor_data.encode_to_vec(),
                    )
                    .await;
            }
            LidarResult::ImuReading(imu) => {
                let imu = ImuData {
                    position: Some(Position3d {
                        position: Some(Vector3 {
                            x: imu.quaternion[0],
                            y: imu.quaternion[1],
                            z: imu.quaternion[2],
                        }),
                        direction: Some(Vector3 {
                            x: imu.quaternion[0],
                            y: imu.quaternion[1],
                            z: imu.quaternion[2],
                        }),
                    }),
                    velocity: Some(Vector3 {
                        x: imu.angular_velocity[0],
                        y: imu.angular_velocity[1],
                        z: imu.angular_velocity[2],
                    }),
                    acceleration: Some(Vector3 {
                        x: imu.linear_acceleration[0],
                        y: imu.linear_acceleration[1],
                        z: imu.linear_acceleration[2],
                    }),
                };

                let general_sensor_data = GeneralSensorData {
                    sensor_name: SensorName::Imu as i32,
                    sensor_id: lidar_name.clone(),
                    timestamp: std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_millis() as i64,
                    data: Some(Data::Imu(imu)),
                };

                let _ = autobahn
                    .publish(
                        &format!("lidar/lidar3d/imu/robotframe"),
                        general_sensor_data.encode_to_vec(),
                    )
                    .await;
            }
        }
    }

    Ok(())
}
