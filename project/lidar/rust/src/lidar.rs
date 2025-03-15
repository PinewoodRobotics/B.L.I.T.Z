use futures_util::Stream;
use lidar_rs::PointUnitree;

pub mod points_getter_2d;
pub mod points_getter_3d;
pub mod reader;

pub trait PointsGetter: Stream<Item = Vec<PointUnitree>> + Drop {}
