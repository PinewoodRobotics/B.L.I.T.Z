use std::ffi::{CStr, CString};
use std::fs;
use std::path::Path;
use std::time::Duration;

use lidar_rs::{
    createUnitreeLidarReaderCpp, delete_reader, getCloud, initialize, runParse, MessageType,
    PointCloudUnitree,
};

fn main() {
    unsafe {
        let reader = createUnitreeLidarReaderCpp();
        if reader.is_null() {
            println!("Failed to create LiDAR reader.");
            return;
        }

        let port = CString::new("/dev/ttyUSB0").unwrap();
        let init_result = initialize(
            reader,
            18,
            port.as_ptr(),
            2000000,
            0.0,
            0.001,
            0.0,
            50.0,
            0.0,
        );

        if init_result == 0 {
            println!("LiDAR initialized successfully.");
        } else {
            println!("Failed to initialize LiDAR.");
        }

        loop {
            let message_type = runParse(reader);
            match message_type {
                MessageType::POINTCLOUD => {
                    let mut cloud = PointCloudUnitree::default();
                    // Use read_unaligned to safely access packed field
                    getCloud(reader, &mut cloud as *mut _);
                    let x = cloud.points[0].x;
                    let y = cloud.points[0].y;
                    let z = cloud.points[0].z;
                    println!("PointCloud: {:?}, {:?}, {:?}", cloud.stamp, y, z);
                }
                _ => {}
            }
        }

        delete_reader(reader);
    }
}
