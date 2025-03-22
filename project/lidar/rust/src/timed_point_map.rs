use std::time::Instant;

use nalgebra::Vector3;

pub struct Plane {
    normal: Vector3<f64>,
    distance: f64,
}

impl Plane {
    pub fn new(normal: Vector3<f64>, distance: f64) -> Self {
        Self {
            normal: normal.normalize(),
            distance,
        }
    }

    pub fn signed_distance(&self, point: &Vector3<f64>) -> f64 {
        self.normal.dot(point) - self.distance
    }
}

pub struct Frustum {
    planes: Vec<Plane>,
    origin: Vector3<f64>,
    corners: [Vector3<f64>; 4],
}

impl Frustum {
    pub fn new(origin: Vector3<f64>, corners: [Vector3<f64>; 4]) -> Self {
        let mut planes = Vec::new();

        for i in 0..4 {
            let current = corners[i];
            let next = corners[(i + 1) % 4];

            // Calculate edges
            let edge1 = current - origin;
            let edge2 = next - origin;

            // Calculate normal for the plane
            let mut normal = edge1.cross(&edge2).normalize();

            // Ensure normal points inward
            if normal.dot(&(corners[(i + 2) % 4] - origin)) > 0.0 {
                normal = -normal;
            }

            // Calculate signed distance from origin
            let distance = normal.dot(&origin);
            planes.push(Plane::new(normal, distance));
        }

        Self {
            planes,
            origin,
            corners,
        }
    }

    pub fn contains(&self, point: &Vector3<f64>) -> bool {
        self.planes
            .iter()
            .all(|plane| plane.signed_distance(point) <= 0.0)
    }
}

pub struct TimedPointCloud3d {
    pub points: Vec<Vector3<f64>>,
    pub timestamp: u128,
}

pub struct TimedPointMap {
    pointclouds: Vec<TimedPointCloud3d>,
    last_clean_time: u128,
    clean_interval_millis: u128,
}

impl TimedPointMap {
    pub fn new(clean_interval_millis: u128) -> Self {
        TimedPointMap {
            pointclouds: Vec::new(),
            last_clean_time: Instant::now().elapsed().as_millis(),
            clean_interval_millis,
        }
    }

    pub fn add_all(&mut self, points: Vec<Vector3<f64>>) {
        self.clean_old_points();
        self.pointclouds.push(TimedPointCloud3d {
            points,
            timestamp: Instant::now().elapsed().as_millis(),
        });
    }

    pub fn clean_old_points(&mut self) {
        let now = Instant::now().elapsed().as_millis();
        self.pointclouds
            .retain(|point| now - point.timestamp < self.clean_interval_millis);
    }

    pub fn query_points_frustum(&self, frustum: &Frustum) -> Vec<Vector3<f64>> {
        self.pointclouds
            .iter()
            .flat_map(|pc| pc.points.iter())
            .filter(|point| frustum.contains(point))
            .cloned()
            .collect()
    }
}
