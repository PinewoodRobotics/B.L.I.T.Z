pub mod autobahn;
pub mod config;
pub mod device_info;
pub mod math;

pub mod project_proto {
    include!(concat!(env!("OUT_DIR"), "/proto.autobahn.rs"));
    include!(concat!(env!("OUT_DIR"), "/proto.lidar.rs"));
    include!(concat!(env!("OUT_DIR"), "/proto.status.rs"));
    include!(concat!(env!("OUT_DIR"), "/proto.util.rs"));
}
