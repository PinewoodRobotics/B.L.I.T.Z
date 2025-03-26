use futures_util::Stream;
use kiss3d::nalgebra::Vector3;

pub mod reader;

pub trait PointsGetter: Stream<Item = Vec<Vector3<f64>>> {}
