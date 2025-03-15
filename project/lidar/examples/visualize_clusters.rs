use std::ffi::CString;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use kiss3d::light::Light;
use kiss3d::nalgebra::{Point3, Translation3};
use kiss3d::window::Window;
use lidar_rs::{
    createUnitreeLidarReaderCpp, delete_reader, getCloud, initialize,
    point_util::{get_area_clusters, voxel_downsample},
    runParse, MessageType, PointCloudUnitree, PointUnitree,
};

struct PointCloudData {
    points: Vec<PointUnitree>,
    updated: bool,
}

fn get_cluster_color(cluster_idx: usize) -> (f32, f32, f32) {
    // Generate different colors for different clusters
    match cluster_idx % 6 {
        0 => (1.0, 0.0, 0.0), // Red
        1 => (0.0, 1.0, 0.0), // Green
        2 => (0.0, 0.0, 1.0), // Blue
        3 => (1.0, 1.0, 0.0), // Yellow
        4 => (1.0, 0.0, 1.0), // Magenta
        5 => (0.0, 1.0, 1.0), // Cyan
        _ => unreachable!(),
    }
}

fn main() {
    let point_cloud_data = Arc::new(Mutex::new(PointCloudData {
        points: Vec::new(),
        updated: false,
    }));

    let point_cloud_data_lidar = point_cloud_data.clone();

    let lidar_thread = thread::spawn(move || unsafe {
        let reader = createUnitreeLidarReaderCpp();
        if reader.is_null() {
            eprintln!("Failed to create LiDAR reader");
            return;
        }

        let port = CString::new("/dev/ttyUSB0").unwrap();
        let result = initialize(
            reader,
            30,
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
            match message_type {
                MessageType::POINTCLOUD => {
                    let mut cloud = PointCloudUnitree::default();
                    getCloud(reader, &mut cloud);
                    let points = cloud.points();
                    if !points.is_empty() {
                        let mut data = point_cloud_data_lidar.lock().unwrap();
                        data.points = points;
                        data.updated = true;
                    }
                }
                _ => {}
            }
        }
    });

    let mut window = Window::new("LiDAR Clusters Visualization");
    window.set_light(Light::StickToCamera);
    window.set_background_color(0.0, 0.0, 0.0);
    let mut point_cloud_node = window.add_group();
    let mut prev_num_points = 0;

    while window.render() {
        let mut data = point_cloud_data.lock().unwrap();

        if data.updated {
            // Time the voxelization and clustering
            let start = std::time::Instant::now();
            let voxel_size = 0.2; // Adjust this value to change voxel grid size
            let voxelized_points = voxel_downsample(data.points.clone(), voxel_size);

            let distance_threshold = 0.6;
            let min_cluster_size = 10;
            let clusters =
                get_area_clusters(&voxelized_points, distance_threshold, min_cluster_size);
            let duration = start.elapsed();

            // Clear previous points if the number has changed
            if prev_num_points != data.points.len() {
                point_cloud_node.unlink();
                point_cloud_node = window.add_group();
                prev_num_points = data.points.len();
                println!(
                    "Found {} clusters from {} points (voxelized from {} points) in {:.2?}",
                    clusters.len(),
                    voxelized_points.len(),
                    data.points.len(),
                    duration
                );
            }

            // Draw unclustered points in white
            let mut clustered_points = std::collections::HashSet::new();
            for cluster in &clusters {
                for point in cluster {
                    // Round to reduce floating-point precision issues
                    let key = (
                        (point.x as f64 * 1000.0).round() as i64,
                        (point.y as f64 * 1000.0).round() as i64,
                        (point.z as f64 * 1000.0).round() as i64,
                    );
                    clustered_points.insert(key);
                }
            }

            // Draw clusters with different colors
            for (cluster_idx, cluster) in clusters.iter().enumerate() {
                let (r, g, b) = get_cluster_color(cluster_idx);

                for point in cluster {
                    let x = point.x * 0.1;
                    let y = point.y * 0.1;
                    let z = point.z * 0.1;

                    let mut sphere = point_cloud_node.add_sphere(0.015); // Slightly larger for clusters
                    sphere.append_translation(&Translation3::new(x as f32, y as f32, z as f32));
                    sphere.set_color(r, g, b);
                }
            }

            // Draw unclustered voxelized points in white
            for point in &voxelized_points {
                let key = (
                    (point.x as f64 * 1000.0).round() as i64,
                    (point.y as f64 * 1000.0).round() as i64,
                    (point.z as f64 * 1000.0).round() as i64,
                );
                if !clustered_points.contains(&key) {
                    let x = point.x * 0.1;
                    let y = point.y * 0.1;
                    let z = point.z * 0.1;

                    let mut sphere = point_cloud_node.add_sphere(0.01); // Smaller for unclustered points
                    sphere.append_translation(&Translation3::new(x as f32, y as f32, z as f32));
                    sphere.set_color(0.5, 0.5, 0.5); // Gray for unclustered points
                }
            }

            data.updated = false;
        }

        thread::sleep(Duration::from_millis(10));
    }
}
