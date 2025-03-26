use std::collections::HashMap;

use nalgebra::{Point3, Vector3};

pub struct TimedPoint3d {
    pub position: Vector3<f64>,
    pub direction: Vector3<f64>,
    pub timestamp: f64,
}

pub struct OptimizedPointCloud {
    pub points: Vec<Vector3<f32>>,
}

pub struct PoseGraph {
    data: HashMap<TimedPoint3d, OptimizedPointCloud>,
    time_cleaning_interval_ms: u128,
}

impl PoseGraph {
    pub fn new(time_cleaning_interval_ms: u128) -> Self {
        Self {
            data: HashMap::new(),
            time_cleaning_interval_ms,
        }
    }

    pub fn add_point_cloud(&mut self, position: TimedPoint3d, point_cloud: OptimizedPointCloud) {
        let current_time = std::time::Instant::now();
        self.data
            .retain(|key, _| current_time.elapsed().as_millis() < self.time_cleaning_interval_ms);

        //self.data.insert(position, point_cloud);
    }
}
