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
