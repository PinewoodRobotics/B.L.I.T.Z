use std::collections::HashSet;

use kiss3d::nalgebra::Vector2;
use nalgebra::{Isometry3, Matrix4, Point3, Vector3};
use rstar::RTree;

pub trait Point3Ext {
    fn to_array(&self) -> [f64; 3];
}

impl Point3Ext for Point3<f64> {
    fn to_array(&self) -> [f64; 3] {
        [self.x, self.y, self.z]
    }
}

pub fn remove_ground(points: &[Point3<f64>], ground_z: f64) -> Vec<Point3<f64>> {
    points.iter().filter(|p| p.z > ground_z).cloned().collect()
}

pub fn voxel_downsample<T: Point3Ext>(points: Vec<T>, voxel_size: f64) -> Vec<Point3<f64>> {
    let mut occupied = HashSet::new();
    let mut result = Vec::new();
    for p in points {
        let p3 = Point3::new(p.to_array()[0], p.to_array()[1], p.to_array()[2]);
        // Compute voxel indices
        let ix = (p3.x / voxel_size).floor() as i64;
        let iy = (p3.y / voxel_size).floor() as i64;
        let iz = (p3.z / voxel_size).floor() as i64;
        if occupied.insert((ix, iy, iz)) {
            result.push(p3);
        }
    }
    result
}

pub fn build_rtree<T: Point3Ext>(points: &[T]) -> RTree<[f64; 3]> {
    RTree::bulk_load(points.iter().map(|p| p.to_array()).collect())
}

pub fn transform_cloud<T: Point3Ext>(points: &[T], transform: &Isometry3<f64>) -> Vec<Point3<f64>> {
    points
        .iter()
        .map(|p| {
            let p3 = Point3::new(p.to_array()[0], p.to_array()[1], p.to_array()[2]);
            transform * p3
        })
        .collect()
}

///
/// Having a point in the lidar's frame and a transform matrix (lidar in robot) transform point to the robot's frame
///
pub fn transform_point(point: &Vector3<f64>, transform: &Matrix4<f64>) -> Vector3<f64> {
    let p4 = transform * Vector3::new(point.x, point.y, point.z).push(1.0);
    Vector3::new(p4.x, p4.y, p4.z)
}

pub fn remove_static_objects<T: Point3Ext>(
    cloud1: &[T],
    cloud2: &[T],
    transform: &Isometry3<f64>,
    threshold: f64,
    max_cluster_size: usize,
) -> Vec<Point3<f64>> {
    let transformed_cloud2 = transform_cloud(cloud2, transform);

    // First, cluster the points and filter clusters
    let clusters = get_area_clusters(&transformed_cloud2, threshold.sqrt(), 2); // Minimum cluster size of 2 to remove isolated points
    let filtered_points: Vec<Point3<f64>> = clusters
        .into_iter()
        .filter(|cluster| cluster.len() <= max_cluster_size && cluster.len() >= 2) // Ensure minimum cluster size
        .flat_map(|cluster| cluster)
        .collect();

    // Then proceed with the normal static object removal
    let tree1 = build_rtree(cloud1);

    filtered_points
        .into_iter()
        .filter(|p| {
            let nearest = tree1.nearest_neighbor(&p.to_array());
            match nearest {
                Some(n) => {
                    let dist = (p.x - n[0]).powi(2) + (p.y - n[1]).powi(2) + (p.z - n[2]).powi(2);
                    dist > threshold
                }
                None => true,
            }
        })
        .collect()
}

pub fn get_area_clusters<T: Point3Ext>(
    cloud1: &[T],
    distance_threshold: f64,
    min_cluster_size: usize,
) -> Vec<Vec<Point3<f64>>> {
    if cloud1.is_empty() {
        return Vec::new();
    }

    let tree = build_rtree(cloud1);
    let mut visited = HashSet::new();
    let mut clusters = Vec::new();

    for (idx, point) in cloud1.iter().enumerate() {
        if visited.contains(&idx) {
            continue;
        }

        let mut cluster = Vec::new();
        let mut to_visit = vec![idx];
        visited.insert(idx);

        while let Some(current_idx) = to_visit.pop() {
            let current_point = Point3::new(
                cloud1[current_idx].to_array()[0],
                cloud1[current_idx].to_array()[1],
                cloud1[current_idx].to_array()[2],
            );
            cluster.push(current_point);

            // Find neighbors within distance_threshold
            let neighbors =
                tree.locate_within_distance(current_point.to_array(), distance_threshold);
            for neighbor in neighbors {
                let neighbor_idx = cloud1
                    .iter()
                    .position(|p| {
                        let arr = p.to_array();
                        (arr[0] - neighbor[0]).abs() < f64::EPSILON
                            && (arr[1] - neighbor[1]).abs() < f64::EPSILON
                            && (arr[2] - neighbor[2]).abs() < f64::EPSILON
                    })
                    .unwrap();

                if !visited.contains(&neighbor_idx) {
                    visited.insert(neighbor_idx);
                    to_visit.push(neighbor_idx);
                }
            }
        }

        if cluster.len() >= min_cluster_size {
            clusters.push(cluster);
        }
    }

    clusters
}

pub fn filter_all_limited(
    point: &Vector3<f64>,
    min_z: f64,
    max_z: f64,
    max_dist: f64,
    min_dist: f64,
) -> bool {
    let dist_sq = point.x.powi(2) + point.y.powi(2) + point.z.powi(2);

    (point.z < min_z || point.z > max_z)
        && dist_sq >= min_dist.powi(2)
        && dist_sq <= max_dist.powi(2)
}

pub fn to_2d(point: Vector3<f64>) -> Vector2<f64> {
    Vector2::new(point.x, point.y)
}
