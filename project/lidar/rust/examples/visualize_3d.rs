use std::ffi::CString;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use kiss3d::light::Light;
use kiss3d::nalgebra::{Point3, Translation3};
use kiss3d::window::Window;
use lidar_rs::{
    createUnitreeLidarReaderCpp, delete_reader, getCloud, initialize, runParse, MessageType,
    PointCloudUnitree, PointUnitree,
};

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

            // Initialize the LiDAR
            let port = CString::new("/dev/ttyUSB0").unwrap();
            let result = initialize(
                reader,
                18,            // cloud_scan_num
                port.as_ptr(), // port
                2000000,       // baudrate
                0.0,           // rotate_yaw_bias
                0.001,         // range_scale
                0.0,           // range_bias
                50.0,          // range_max
                0.0,           // range_min
            );

            if result != 0 {
                eprintln!("Failed to initialize LiDAR: {}", result);
                delete_reader(reader);
                return;
            }

            println!("LiDAR initialized successfully");

            // Run the LiDAR continuously
            loop {
                let message_type = runParse(reader);

                match message_type {
                    MessageType::POINTCLOUD => {
                        // Create a new PointCloudUnitree to receive the data
                        let mut cloud = PointCloudUnitree::default();

                        // Get the cloud data
                        getCloud(reader, &mut cloud);

                        // Get a copy of the points
                        let points = cloud.points();

                        if !points.is_empty() {
                            println!("Received point cloud with {} points", points.len());

                            // Update the shared data structure
                            let mut data = point_cloud_data_lidar.lock().unwrap();
                            data.points = points;
                            data.updated = true;
                        }
                    }
                    _ => {} // Ignore other message types
                }
            }

            // This code is unreachable due to the infinite loop above,
            // but we'll keep it for completeness
            delete_reader(reader);
            println!("LiDAR reader deleted");
        }
    });

    // Create a window for 3D visualization
    let mut window = Window::new("LiDAR Point Cloud Visualization");

    // Add a light to the scene
    window.set_light(Light::StickToCamera);

    // Set background color to black
    window.set_background_color(0.0, 0.0, 0.0);

    // Create a point cloud scene node
    let mut point_cloud_node = window.add_group();

    // Previous number of points, to detect changes
    let mut prev_num_points = 0;

    // Main rendering loop
    while window.render() {
        // Get the latest point cloud data
        let mut data = point_cloud_data.lock().unwrap();

        // Check if the data has been updated
        if data.updated {
            // Clear previous points if the number has changed
            if prev_num_points != data.points.len() {
                point_cloud_node.unlink();
                point_cloud_node = window.add_group();
                prev_num_points = data.points.len();
            }

            // Add points to the scene
            for point in &data.points {
                // Scale the points to fit in the window
                // You may need to adjust these scaling factors based on your LiDAR data
                let x = point.x * 0.1;
                let y = point.y * 0.1;
                let z = point.z * 0.1;

                // Create a small sphere for each point
                let mut sphere = point_cloud_node.add_sphere(0.01);

                // Position the sphere
                sphere.append_translation(&Translation3::new(x, y, z));

                // Color the sphere based on intensity (normalized to 0-1)
                let intensity = point.intensity / 255.0;
                sphere.set_color(intensity, intensity, intensity);
            }

            // Reset the updated flag
            data.updated = false;
        }

        // Small delay to prevent CPU hogging
        thread::sleep(Duration::from_millis(10));
    }

    // The program will exit when the window is closed
    // We don't need to join the lidar_thread as it will be terminated when the main thread exits
}
