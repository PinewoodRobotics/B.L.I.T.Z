use std::time::{Duration, Instant};

pub trait UpdateModel<T, O> {
    fn update(&mut self, imu: &T) -> O;
    fn get(&self) -> O;
    fn reset(&mut self, reset_time: Instant) -> O;
}
