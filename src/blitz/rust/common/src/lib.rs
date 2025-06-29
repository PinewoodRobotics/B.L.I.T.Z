pub mod autobahn;
pub mod config;
pub mod device_info;
pub mod math;

pub mod proto {
    pub mod autobahn {
        include!(concat!(env!("OUT_DIR"), "/proto.autobahn.rs"));
    }
    pub mod sensor {
        include!(concat!(env!("OUT_DIR"), "/proto.sensor.rs"));
    }
    pub mod status {
        include!(concat!(env!("OUT_DIR"), "/proto.status.rs"));
    }
    pub mod util {
        include!(concat!(env!("OUT_DIR"), "/proto.util.rs"));
    }
}

#[allow(dead_code, unused_imports, unused_extern_crates)]
#[allow(
    clippy::too_many_arguments,
    clippy::type_complexity,
    clippy::vec_box,
    clippy::wrong_self_convention
)]
pub mod thrift {
    pub mod config {
        include!(concat!(env!("OUT_DIR"), "/thrift/config.rs"));
    }
    pub mod common {
        include!(concat!(env!("OUT_DIR"), "/thrift/common.rs"));
    }
    pub mod autobahn {
        include!(concat!(env!("OUT_DIR"), "/thrift/autobahn.rs"));
    }
    pub mod apriltag {
        include!(concat!(env!("OUT_DIR"), "/thrift/apriltag.rs"));
    }
    pub mod camera {
        include!(concat!(env!("OUT_DIR"), "/thrift/camera.rs"));
    }
    pub mod image_recognition {
        include!(concat!(env!("OUT_DIR"), "/thrift/image_recognition.rs"));
    }
    pub mod lidar {
        include!(concat!(env!("OUT_DIR"), "/thrift/lidar.rs"));
    }
    pub mod logger {
        include!(concat!(env!("OUT_DIR"), "/thrift/logger.rs"));
    }
    pub mod pos_extrapolator {
        include!(concat!(env!("OUT_DIR"), "/thrift/pos_extrapolator.rs"));
    }
    pub mod kalman_filter {
        include!(concat!(env!("OUT_DIR"), "/thrift/kalman_filter.rs"));
    }
    pub mod watchdog {
        include!(concat!(env!("OUT_DIR"), "/thrift/watchdog.rs"));
    }
}
