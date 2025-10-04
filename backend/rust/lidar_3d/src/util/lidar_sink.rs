use std::sync::Arc;

use futures_util::StreamExt;
use nalgebra::Vector3;
use tokio::{sync::Mutex, task::LocalSet};
use unitree_lidar_l1_rust::{
    bridge::ffi::ImuRust,
    lidar::reader::{LidarResult, LidarStream},
};

pub struct LidarSink {
    lidars: Vec<Arc<Mutex<LidarStream>>>,
    accumulated_points: Mutex<Option<Vec<Vector3<f32>>>>,
    latest_imu: Mutex<Option<ImuRust>>,
    online: bool,
}

impl LidarSink {
    pub fn new(lidars: Vec<LidarStream>) -> Self {
        LidarSink {
            lidars: lidars
                .into_iter()
                .map(|lidar| Arc::new(Mutex::new(lidar)))
                .collect(),
            accumulated_points: Mutex::new(None),
            latest_imu: Mutex::new(None),
            online: false,
        }
    }

    pub async fn spin(self: Arc<Self>, local: LocalSet) {
        for lidar in self.lidars.iter() {
            let lidar = Arc::clone(lidar);
            let self_clone = Arc::clone(&self);

            local.spawn_local(async move {
                if let Some(result) = lidar.lock().await.next().await {
                    match result {
                        LidarResult::PointCloud(points) => {
                            let mut acc_points = self_clone.accumulated_points.lock().await;
                            if acc_points.is_none() {
                                *acc_points = Some(points);
                            } else {
                                acc_points.as_mut().unwrap().extend(points);
                            }

                            drop(acc_points);
                        }
                        LidarResult::ImuReading(imu) => {
                            let mut latest_imu = self_clone.latest_imu.lock().await;
                            *latest_imu = Some(imu);
                            drop(latest_imu);
                        }
                    }
                }
            });
        }

        local.await;
    }

    pub async fn get_latest_imu(&self) -> Option<ImuRust> {
        let mut latest_imu = self.latest_imu.lock().await;
        latest_imu.take()
    }

    pub async fn get_accumulated_points(&self) -> Option<Vec<Vector3<f32>>> {
        let mut accumulated_points = self.accumulated_points.lock().await;
        accumulated_points.take()
    }
}
