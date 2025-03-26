use std::env;
use std::path::PathBuf;
use walkdir::WalkDir;

extern crate cc;
extern crate prost_build;

fn main() {
    // Get the manifest directory (where Cargo.toml is located)
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let proto_dir = PathBuf::from(&manifest_dir)
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("proto");

    // Recursively find all .proto files in proto_dir and its subdirectories
    let proto_files: Vec<String> = WalkDir::new(&proto_dir)
        .follow_links(true) // Follow symbolic links
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().map_or(false, |ext| ext == "proto"))
        .map(|e| e.path().to_str().unwrap().to_string())
        .collect();

    // Add proto_dir and all its subdirectories to the include path
    let include_dirs: Vec<String> = WalkDir::new(&proto_dir)
        .follow_links(true)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_dir())
        .map(|e| e.path().to_str().unwrap().to_string())
        .collect();

    // Compile all found protos with all include directories
    prost_build::compile_protos(&proto_files, &include_dirs).unwrap();
}
