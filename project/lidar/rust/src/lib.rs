use std::os::raw::{c_char, c_float, c_int, c_void};
use std::vec::Vec;

use point_util::Point3Ext;

pub mod point_util;

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct PointUnitree {
    pub x: f32,
    pub y: f32,
    pub z: f32,
    pub intensity: f32,
    pub time: f32,
    pub ring: u32,
}

impl Default for PointUnitree {
    fn default() -> Self {
        PointUnitree {
            x: 0.0,
            y: 0.0,
            z: 0.0,
            intensity: 0.0,
            time: 0.0,
            ring: 0,
        }
    }
}

impl Point3Ext for PointUnitree {
    fn to_array(&self) -> [f64; 3] {
        [self.x as f64, self.y as f64, self.z as f64]
    }
}

#[repr(C)]
#[derive(Debug)]
pub struct PointCloudUnitree {
    pub stamp: f64,
    pub id: u32,
    pub ring_num: u32,
    pub points_ptr: *mut PointUnitree,
    pub points_len: usize,
    pub points_capacity: usize,
}

impl Default for PointCloudUnitree {
    fn default() -> Self {
        PointCloudUnitree {
            stamp: 0.0,
            id: 0,
            ring_num: 0,
            points_ptr: std::ptr::null_mut(),
            points_len: 0,
            points_capacity: 0,
        }
    }
}

impl PointCloudUnitree {
    // Helper method to get a copy of the points as a Vec
    pub fn points(&self) -> Vec<PointUnitree> {
        if self.points_ptr.is_null() || self.points_len == 0 {
            return Vec::new();
        }

        // Create a copy of the points
        let mut result = Vec::with_capacity(self.points_len);
        unsafe {
            for i in 0..self.points_len {
                result.push(*self.points_ptr.add(i));
            }
        }
        result
    }

    // Clean up the points when done
    pub fn free_points(&mut self) {
        if !self.points_ptr.is_null() {
            unsafe {
                freePointCloudMemory(self.points_ptr);
            }
            self.points_ptr = std::ptr::null_mut();
            self.points_len = 0;
            self.points_capacity = 0;
        }
    }
}

impl Drop for PointCloudUnitree {
    fn drop(&mut self) {
        self.free_points();
    }
}

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub enum LidarWorkingMode {
    NORMAL = 1,
    STANDBY = 2,
}

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub enum MessageType {
    NONE = 0,
    IMU = 1,
    POINTCLOUD = 2,
    RANGE = 3,
    AUXILIARY = 4,
    VERSION = 5,
    TIMESYNC = 6,
}

extern "C" {
    pub fn createUnitreeLidarReaderCpp() -> *mut c_void;
    pub fn initialize(
        reader: *mut c_void,
        cloud_scan_num: u16,
        port: *const c_char,
        baudrate: u32,
        rotate_yaw_bias: c_float,
        range_scale: c_float,
        range_bias: c_float,
        range_max: c_float,
        range_min: c_float,
    ) -> c_int;
    pub fn runParse(reader: *mut c_void) -> MessageType;
    pub fn getCloud(reader: *mut c_void, cloud: *mut PointCloudUnitree);
    pub fn freePointCloudMemory(points_ptr: *mut PointUnitree);
    pub fn getVersionOfFirmware(reader: *mut c_void, buffer: *mut c_char, buffer_size: usize);
    pub fn getVersionOfSDK(reader: *mut c_void, buffer: *mut c_char, buffer_size: usize);
    pub fn reset(reader: *mut c_void);
    pub fn setLidarWorkingMode(reader: *mut c_void, mode: LidarWorkingMode);
    pub fn delete_reader(reader: *mut c_void);
}
