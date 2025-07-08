use std::path::PathBuf;

fn main() {
    let out_dir = PathBuf::from(std::env::var("OUT_DIR").unwrap());
    let cargo_manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let include_dir = cargo_manifest_dir.join("include");
    let cxx_rs_include_dir = out_dir
        .join("cxxbridge")
        .join("include")
        .join("lidar-3d")
        .join("src");
    let cxx_include_dir = out_dir.join("cxxbridge").join("include").join("rust");

    cxx_build::bridge("src/bridge.rs")
        .file("src/cpp/unitree_lidar_wrapper.cpp")
        .include("src/cpp/")
        .include("include")
        .compile("unitree_lidar");

    // println!("cargo:rustc-link-arg=-Wl,-rpath,{}", cargo_manifest_dir.join("lib").display());
    println!(
        "cargo:rustc-link-search=native={}",
        cargo_manifest_dir.join("lib").display()
    );
    println!("cargo:rustc-link-lib=static=unitree_lidar_sdk");
}

/*
let out_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
let lib_path = PathBuf::from(&out_dir).join("lib");

// Add rpath with $ORIGIN to make library lookup relative to executable
println!("cargo:rustc-link-arg=-Wl,-rpath,$ORIGIN/lib");
println!("cargo:rustc-link-arg=-Wl,-rpath,{}", lib_path.display());

// Link libraries using exact paths
let wrapper_lib = lib_path.join("libunitree_lidar_sdk_wrapper.so");
let static_lib = lib_path.join("libunitree_lidar_sdk.a");

println!("cargo:rustc-link-arg={}", wrapper_lib.display());
println!("cargo:rustc-link-arg={}", static_lib.display());

// Ensure Rust links with the C++ standard library
println!("cargo:rustc-link-lib=dylib=stdc++");
*/
