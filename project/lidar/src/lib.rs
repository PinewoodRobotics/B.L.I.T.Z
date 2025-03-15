use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint, c_void};

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

#[repr(C)]
#[derive(Debug)]
pub struct PointCloudUnitree {
    pub stamp: f64,
    pub id: u32,
    pub ringNum: u32,
    pub points: [PointUnitree; 120], // MATCHES C++ FIXED SIZE ARRAY
}

impl Default for PointCloudUnitree {
    fn default() -> Self {
        PointCloudUnitree {
            stamp: 0.0,
            id: 0,
            ringNum: 0,
            points: [PointUnitree::default(); 120],
        }
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
    pub fn getVersionOfFirmware(reader: *mut c_void, buffer: *mut c_char, buffer_size: usize);
    pub fn getVersionOfSDK(reader: *mut c_void, buffer: *mut c_char, buffer_size: usize);
    pub fn reset(reader: *mut c_void);
    pub fn setLidarWorkingMode(reader: *mut c_void, mode: LidarWorkingMode);
    pub fn delete_reader(reader: *mut c_void);
}
