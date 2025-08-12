use std::time::Duration;

use autobahn_client::autobahn::{Address, Autobahn};
use clap::Parser;
use common_core::config::from_uncertainty_config;
use common_core::device_info::{get_system_name, load_system_config};
use common_core::math::{
    to_transformation_matrix_vec_matrix, to_transformation_matrix_vec_matrix_f64,
};
use common_core::proto::sensor::general_sensor_data::Data;
use common_core::proto::sensor::LidarData;
use common_core::proto::sensor::{lidar_data, ImuData, PointCloud3d};
use common_core::proto::sensor::{GeneralSensorData, SensorName};
use common_core::proto::util::{Position3d, Vector2, Vector3};
use common_core::thrift::config::Config;
use common_core::thrift::lidar::LidarConfig;
use futures_util::StreamExt;
use prost::Message;
use unitree_lidar_l1_rust::lidar::reader::{LidarReader, LidarResult};

use crate::util::imu::{ImuPositionVelocityEstimator, VelEstimator};
use crate::util::model::UpdateModel;
use crate::util::transform_point;

mod timed_point_map;
mod util;

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
    let lidar_in_robot_transformation = to_transformation_matrix_vec_matrix_f64(
        config.position_in_robot.into(),
        config.rotation_in_robot.into(),
    );

    let mut reader = LidarReader::new_with_initialize(
        config.cloud_scan_num as u32,
        config.port,
        config.baudrate as u32,
        config.min_distance_meters.into(),
        config.max_distance_meters.into(),
        0.0,
        0.001,
        0.0,
    )?;
    reader.start_lidar()?;

    let mut imu_pos_estimator = ImuPositionVelocityEstimator::new();
    let mut imu_vel_estimator = VelEstimator::new(Duration::new(0, 0));

    let mut reader = reader.into_stream();
    while let Some(result) = reader.next().await {
        match result {
            LidarResult::PointCloud(points) => {
                let points = points
                    .iter()
                    .map(|point| transform_point(point, &lidar_in_robot_transformation))
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

                let _ = autobahn
                    .publish(
                        &format!("lidar/lidar3d/pointcloud/3d/robotframe"),
                        general_sensor_data.encode_to_vec(),
                    )
                    .await;
            }
            LidarResult::ImuReading(imu) => {
                let imu_new_pos = imu_pos_estimator.update(&imu);
                let imu_new_vel = imu_vel_estimator.update(&imu);

                let position_data = Position3d {
                    position: Some(Vector3 {
                        x: imu_new_pos.x,
                        y: imu_new_pos.y,
                        z: imu_new_pos.z,
                    }),
                    direction: Some(Vector3 {
                        x: imu_new_pos.x,
                        y: imu_new_pos.y,
                        z: imu_new_pos.z,
                    }),
                };

                let _ = autobahn
                    .publish(
                        &format!("lidar/lidar3d/imu/position"),
                        position_data.encode_to_vec(),
                    )
                    .await;

                // println!("!!! IMU Velocity: {:?}", imu_new_vel);

                let _ = autobahn
                    .publish(
                        &format!("imu/imu"),
                        GeneralSensorData {
                            sensor_name: SensorName::Imu as i32,
                            sensor_id: "0".to_string(),
                            timestamp: std::time::SystemTime::now()
                                .duration_since(std::time::UNIX_EPOCH)
                                .unwrap()
                                .as_secs() as i64,
                            data: Some(Data::Imu(ImuData {
                                position: None,
                                velocity: Some(Vector3 {
                                    x: imu_new_vel.x,
                                    y: imu_new_vel.y,
                                    z: imu_new_vel.z,
                                }),
                                acceleration: Some(Vector3 {
                                    x: imu_new_pos.x,
                                    y: imu_new_pos.y,
                                    z: imu_new_pos.z,
                                }),
                            })),
                        }
                        .encode_to_vec(),
                    )
                    .await;
            }
        }
    }

    Ok(())
}
