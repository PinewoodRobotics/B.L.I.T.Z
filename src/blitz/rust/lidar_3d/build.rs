extern crate cc;
use std::env;
use std::path::PathBuf;

fn main() {
    // Only link the static library on Linux systems
    if cfg!(target_os = "linux") {
        let out_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
        let lib_path = PathBuf::from(&out_dir).join("lib");

        println!("cargo:rustc-link-search=native={}", lib_path.display());

        // Add rpath so the executable can find the dynamic library
        println!("cargo:rustc-link-arg=-Wl,-rpath,{}", lib_path.display());

        // Link the C++ wrapper library
        println!("cargo:rustc-link-lib=dylib=unitree_lidar_sdk_wrapper");

        // Link the original Unitree SDK library (static library)
        println!("cargo:rustc-link-lib=static=unitree_lidar_sdk");

        // Ensure Rust links with the C++ standard library
        println!("cargo:rustc-link-lib=dylib=stdc++");
    }
}
