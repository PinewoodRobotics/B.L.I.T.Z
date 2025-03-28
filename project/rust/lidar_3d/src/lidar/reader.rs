use common_core::config::LidarConfig;
use futures_util::Stream;
use lidar_3d::{
    createUnitreeLidarReaderCpp, delete_reader, getCloud, initialize, runParse, MessageType,
    PointCloudUnitree,
};
use nalgebra::Vector3;
use std::ffi::{c_void, CString};
use std::pin::Pin;
use std::task::{Context, Poll};

pub struct LidarReader {
    reader: *mut c_void,
}

impl LidarReader {
    pub fn new_with_initialize(config: LidarConfig) -> Result<Self, Box<dyn std::error::Error>> {
        let reader = unsafe { createUnitreeLidarReaderCpp() };
        if reader.is_null() {
            return Err("Failed to create LiDAR reader".into());
        }

        let port = CString::new(config.port.as_str())?;
        let result = unsafe {
            initialize(
                reader,
                18,
                port.as_ptr(),
                config.baudrate,
                0.0,
                0.001,
                0.0,
                config.max_distance_meters as f32,
                config.min_distance_meters as f32,
            )
        };

        if result != 0 {
            return Err("Failed to initialize LiDAR".into());
        }

        Ok(Self { reader })
    }

    pub fn into_stream(self) -> LidarStream {
        LidarStream { reader: self }
    }
}

pub struct LidarStream {
    reader: LidarReader,
}

impl Stream for LidarStream {
    type Item = Vec<Vector3<f64>>;

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        unsafe {
            match runParse(self.reader.reader) {
                MessageType::POINTCLOUD => {
                    let mut cloud = PointCloudUnitree::default();
                    getCloud(self.reader.reader, &mut cloud);
                    let points = cloud.points();
                    if points.is_empty() {
                        cx.waker().wake_by_ref();
                        Poll::Pending
                    } else {
                        Poll::Ready(Some(
                            points
                                .iter()
                                .map(|p| Vector3::new(p.x as f64, p.y as f64, p.z as f64))
                                .collect(),
                        ))
                    }
                }
                _ => {
                    // If no data, wake up after a short delay
                    cx.waker().wake_by_ref();
                    Poll::Pending
                }
            }
        }
    }
}

impl Drop for LidarReader {
    fn drop(&mut self) {
        unsafe {
            delete_reader(self.reader);
        }
    }
}
