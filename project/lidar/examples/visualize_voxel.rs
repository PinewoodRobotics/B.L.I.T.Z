use std::ffi::CString;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use kiss3d::light::Light;
use kiss3d::nalgebra::Point3;
use kiss3d::window::Window;
use lidar_rs::{
    createUnitreeLidarReaderCpp, delete_reader, getCloud, initialize, runParse, MessageType,
    PointCloudUnitree, PointUnitree,
};

// Import our point_util functions
use lidar_rs::point_util::{voxel_downsample, Point3Ext};

// Structure to hold the latest point cloud data
struct PointCloudData {
    points: Vec<PointUnitree>,
    updated: bool,
}

fn main() {
    // Create a shared data structure for the point cloud
    let point_cloud_data = Arc::new(Mutex::new(PointCloudData {
        points: Vec::new(),
        updated: false,
    }));

    // Clone the Arc for the LiDAR thread
    let point_cloud_data_lidar = point_cloud_data.clone();

    // Spawn a thread to read LiDAR data
    let lidar_thread = thread::spawn(move || {
        unsafe {
            // Create a new LiDAR reader
            let reader = createUnitreeLidarReaderCpp();
            if reader.is_null() {
                eprintln!("Failed to create LiDAR reader");
                return;
            }

            println!("LiDAR reader created successfully");

            // Initialize the LiDAR
            let port = CString::new("/dev/ttyUSB0").unwrap();
            let result = initialize(
                reader,
                100,
                port.as_ptr(),
                2000000,
                0.0,
                0.001,
                0.0,
                50.0,
                0.0,
            );

            if result != 0 {
                eprintln!("Failed to initialize LiDAR: {}", result);
                delete_reader(reader);
                return;
            }

            println!("LiDAR initialized successfully");

            loop {
                let message_type = runParse(reader);

                if let MessageType::POINTCLOUD = message_type {
                    let mut cloud = PointCloudUnitree::default();
                    getCloud(reader, &mut cloud);
                    let points = cloud.points();

                    if !points.is_empty() {
                        println!("Received point cloud with {} points", points.len());
                        let mut data = point_cloud_data_lidar.lock().unwrap();
                        data.points = points;
                        data.updated = true;
                    }
                }
            }
        }
    });

    // Create a window for 3D visualization
    let mut window = Window::new("Voxelized Point Cloud Visualization");
    window.set_light(Light::StickToCamera);
    window.set_background_color(0.0, 0.0, 0.0);

    let mut point_cloud_node = window.add_group();
    let mut prev_num_points = 0;

    // Main rendering loop
    while window.render() {
        let mut data = point_cloud_data.lock().unwrap();

        if data.updated {
            let len = data.points.len();
            // Time the voxel downsampling
            let start = std::time::Instant::now();
            let voxel_size = 0.01; // Adjust this value to change the voxel grid size
            let downsampled_points = voxel_downsample(data.points.clone(), voxel_size);
            let duration = start.elapsed();

            // Clear previous points if the number has changed
            if prev_num_points != downsampled_points.len() {
                point_cloud_node.unlink();
                point_cloud_node = window.add_group();
                prev_num_points = downsampled_points.len();
                println!(
                    "Downsampled from {} to {} points in {:.2?}",
                    len,
                    downsampled_points.len(),
                    duration
                );
            }

            // Add downsampled points to the scene
            for point in &downsampled_points {
                // Scale the points to fit in the window
                let x = point.x * 0.1;
                let y = point.y * 0.1;
                let z = point.z * 0.1;

                // Create a slightly larger sphere for better visibility of voxelized points
                let mut sphere = point_cloud_node.add_sphere(0.02);
                sphere.set_color(0.0, 1.0, 0.0); // Make voxelized points green
                sphere.append_translation(&kiss3d::nalgebra::Translation3::new(
                    x as f32, y as f32, z as f32,
                ));
            }

            data.updated = false;
        }

        thread::sleep(Duration::from_millis(10));
    }
}
