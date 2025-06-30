use futures_util::Stream;
use lidar_3d::{
    createUnitreeLidarReaderCpp, delete_reader, getCloud, getImu, initialize, runParse,
    setLidarWorkingMode, Imu, LidarWorkingMode, MessageType, PointCloudUnitree,
};
use nalgebra::Vector3;
use std::ffi::{c_void, CString};
use std::pin::Pin;
use std::task::{Context, Poll};

pub struct LidarReader {
    reader: *mut c_void,
}

impl LidarReader {
    pub fn new_with_initialize(
        port: String,
        baudrate: u32,
        min_distance_meters: f64,
        max_distance_meters: f64,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let reader = unsafe { createUnitreeLidarReaderCpp() };
        if reader.is_null() {
            return Err("Failed to create LiDAR reader".into());
        }

        let port = CString::new(port.as_str())?;
        let result = unsafe {
            initialize(
                reader,
                18,
                port.as_ptr(),
                baudrate,
                min_distance_meters as f32,
                max_distance_meters as f32,
                0.0,
                max_distance_meters as f32,
                min_distance_meters as f32,
            )
        };

        if result != 0 {
            return Err("Failed to initialize LiDAR".into());
        }

        Ok(Self { reader })
    }

    pub fn start_lidar(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        unsafe {
            setLidarWorkingMode(self.reader, LidarWorkingMode::STANDBY);
            std::thread::sleep(std::time::Duration::from_secs(1));
            setLidarWorkingMode(self.reader, LidarWorkingMode::NORMAL);
        }

        Ok(())
    }

    pub fn into_stream(self) -> LidarStream {
        LidarStream { reader: self }
    }
}

pub enum LidarResult {
    PointCloud(Vec<Vector3<f32>>),
    ImuReading(Imu),
}

pub struct LidarStream {
    reader: LidarReader,
}

impl Stream for LidarStream {
    type Item = LidarResult;

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
                        Poll::Ready(Some(LidarResult::PointCloud(
                            points.iter().map(|p| Vector3::new(p.x, p.y, p.z)).collect(),
                        )))
                    }
                }
                MessageType::IMU => {
                    let mut imu = Imu::default();
                    getImu(self.reader.reader, &mut imu);
                    Poll::Ready(Some(LidarResult::ImuReading(imu)))
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
