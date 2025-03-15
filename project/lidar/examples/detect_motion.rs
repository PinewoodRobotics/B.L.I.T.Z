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
use nalgebra::{Isometry3, Translation3, Vector3};

use lidar_rs::point_util::{remove_static_objects, voxel_downsample, Point3Ext};

struct PointCloudData {
    points: Vec<PointUnitree>,
    prev_points: Vec<PointUnitree>,
    updated: bool,
}

fn main() {
    let point_cloud_data = Arc::new(Mutex::new(PointCloudData {
        points: Vec::new(),
        prev_points: Vec::new(),
        updated: false,
    }));

    let point_cloud_data_lidar = point_cloud_data.clone();

    // Spawn LiDAR reading thread
    let lidar_thread = thread::spawn(move || unsafe {
        let reader = createUnitreeLidarReaderCpp();
        if reader.is_null() {
            eprintln!("Failed to create LiDAR reader");
            return;
        }

        let port = CString::new("/dev/ttyUSB0").unwrap();
        let result = initialize(
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
                    let mut data = point_cloud_data_lidar.lock().unwrap();
                    data.prev_points = std::mem::replace(&mut data.points, points);
                    data.updated = true;
                }
            }
        }
    });

    let mut window = Window::new("Moving Object Detection");
    window.set_light(Light::StickToCamera);
    window.set_background_color(0.0, 0.0, 0.0);

    // Add coordinate system axes at the center
    let mut center_node = window.add_group();

    // X axis (red)
    let mut x_axis = center_node.add_cylinder(0.01, 0.5);
    x_axis.set_color(1.0, 0.0, 0.0);
    x_axis.append_rotation(&kiss3d::nalgebra::UnitQuaternion::from_axis_angle(
        &kiss3d::nalgebra::Vector3::y_axis(),
        std::f32::consts::FRAC_PI_2,
    ));

    // Y axis (green)
    let mut y_axis = center_node.add_cylinder(0.01, 0.5);
    y_axis.set_color(0.0, 1.0, 0.0);

    // Z axis (blue)
    let mut z_axis = center_node.add_cylinder(0.01, 0.5);
    z_axis.set_color(0.0, 0.0, 1.0);
    z_axis.append_rotation(&kiss3d::nalgebra::UnitQuaternion::from_axis_angle(
        &kiss3d::nalgebra::Vector3::x_axis(),
        std::f32::consts::FRAC_PI_2,
    ));

    // Add center sphere
    let mut center_sphere = center_node.add_sphere(0.03);
    center_sphere.set_color(1.0, 1.0, 1.0);

    let mut point_cloud_node = window.add_group();
    let mut regular_point_cloud_node = window.add_group();
    let mut prev_num_points = 0;

    // Use frame-to-frame motion instead of accumulating
    let forward_speed = 0.0; // meters per frame
    let max_distance = 10.0; // meters

    while window.render() {
        let mut data = point_cloud_data.lock().unwrap();

        if data.updated && !data.prev_points.is_empty() {
            // Filter points by distance first
            let filtered_prev: Vec<PointUnitree> = data
                .prev_points
                .iter()
                .filter(|p| (p.x * p.x + p.y * p.y + p.z * p.z).sqrt() <= max_distance)
                .cloned()
                .collect();
            let filtered_current: Vec<PointUnitree> = data
                .points
                .iter()
                .filter(|p| (p.x * p.x + p.y * p.y + p.z * p.z).sqrt() <= max_distance)
                .cloned()
                .collect();

            // Voxelize both point clouds
            let voxel_size = 0.3;
            let voxelized_prev = voxel_downsample(filtered_prev, voxel_size);
            let voxelized_current = voxel_downsample(filtered_current, voxel_size);

            // Create transform for frame-to-frame motion
            let transform = Isometry3::from_parts(
                Translation3::new(0.0, 0.0, forward_speed),
                nalgebra::UnitQuaternion::identity(),
            );

            // Detect moving objects using voxelized points
            let start = std::time::Instant::now();
            let moving_points = remove_static_objects(
                &voxelized_prev,
                &voxelized_current,
                &transform,
                0.4,
                10, // Maximum cluster size (adjust this value based on your needs)
            );
            let duration = start.elapsed();

            // Clear and recreate point cloud node
            point_cloud_node.unlink();
            point_cloud_node = window.add_group();

            prev_num_points = moving_points.len();
            println!(
                "Found {} moving points (processing time: {:.2?})",
                moving_points.len(),
                duration
            );

            // Visualize points in 3D
            for point in &moving_points {
                // Keep original coordinates, but scale for better visibility
                let x = point.x * 0.1;
                let y = point.y * 0.1;
                let z = point.z * 0.1;

                // Add sphere at actual 3D position
                let mut sphere = point_cloud_node.add_sphere(0.02);
                sphere.set_color(1.0, 0.0, 0.0);
                sphere.append_translation(&kiss3d::nalgebra::Translation3::new(
                    x as f32, y as f32, z as f32,
                ));

                // Add velocity vector as arrow
                let mut arrow = point_cloud_node.add_cylinder(0.01, 0.1);
                arrow.set_color(1.0, 1.0, 0.0);

                // Calculate rotation to point in the direction of motion
                let direction = Vector3::<f32>::new(0.0, 0.0, forward_speed as f32);
                if direction.magnitude() > 0.0 {
                    let up = Vector3::<f32>::y();
                    let rotation = nalgebra::UnitQuaternion::<f32>::rotation_between(
                        &up,
                        &direction.normalize(),
                    )
                    .unwrap_or(nalgebra::UnitQuaternion::<f32>::identity());
                }

                arrow.append_translation(&kiss3d::nalgebra::Translation3::new(
                    x as f32, y as f32, z as f32,
                ));
            }

            data.updated = false;
        }

        thread::sleep(Duration::from_millis(10));
    }
}
