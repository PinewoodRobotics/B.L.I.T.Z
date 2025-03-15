use std::ffi::CString;

fn main() {
    // Create a new LiDAR reader
    let reader = unsafe { lidar_rs::createUnitreeLidarReaderCpp() };
    if reader.is_null() {
        eprintln!("Failed to create LiDAR reader");
        return;
    }

    // Initialize the LiDAR
    let port = CString::new("/dev/ttyUSB0").unwrap();
    let result = unsafe {
        lidar_rs::initialize(
            reader,
            18,            // cloud_scan_num
            port.as_ptr(), // port
            2000000,       // baudrate
            0.0,           // rotate_yaw_bias
            0.001,         // range_scale
            0.0,           // range_bias
            50.0,          // range_max
            0.0,           // range_min
        )
    };

    if result != 0 {
        eprintln!("Failed to initialize LiDAR: {}", result);
        unsafe { lidar_rs::delete_reader(reader) };
        return;
    }

    println!("LiDAR initialized successfully");

    // Run the LiDAR for a few iterations
    for i in 0..10 {
        let message_type = unsafe { lidar_rs::runParse(reader) };

        // Use a match statement instead of direct comparison
        match message_type {
            lidar_rs::MessageType::POINTCLOUD => {
                // Create a new PointCloudUnitree to receive the data
                let mut cloud = lidar_rs::PointCloudUnitree::default();

                // Get the cloud data
                unsafe { lidar_rs::getCloud(reader, &mut cloud) };

                // Get a copy of the points
                let points = cloud.points();
                println!(
                    "Iteration {}: Received point cloud with {} points",
                    i,
                    points.len()
                );

                // Print the first few points
                for (j, point) in points.iter().take(5).enumerate() {
                    println!(
                        "Point {}: ({}, {}, {}), intensity: {}, time: {}, ring: {}",
                        j, point.x, point.y, point.z, point.intensity, point.time, point.ring
                    );
                }

                // The cloud will automatically free its points when it goes out of scope
            }
            _ => {} // Ignore other message types
        }
    }

    // Clean up
    unsafe { lidar_rs::delete_reader(reader) };
    println!("LiDAR reader deleted");
}
