extern crate cc;

fn main() {
    // Tell Cargo to look in the `lib` directory
    println!("cargo:rustc-link-search=native=./lib");

    // Link the C++ wrapper library
    println!("cargo:rustc-link-lib=dylib=unitree_lidar_sdk_wrapper");

    // Link the original Unitree SDK library
    println!("cargo:rustc-link-lib=dylib=unitree_lidar_sdk");

    // Ensure Rust links with the C++ standard library
    println!("cargo:rustc-link-lib=dylib=stdc++");
}
