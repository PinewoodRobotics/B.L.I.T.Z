use std::env;
use std::fs;
use std::path::PathBuf;
use walkdir::WalkDir;

extern crate prost_build;

fn main() {
    let workspace_dir = env::var("CARGO_WORKSPACE_DIR")
        .or_else(|_| find_workspace_root())
        .expect("Failed to find workspace root");

    let proto_dir = PathBuf::from(&workspace_dir).join("backend").join("proto");

    println!("proto_dir: {}", proto_dir.display());

    let proto_files: Vec<String> = WalkDir::new(&proto_dir)
        .follow_links(true)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().map_or(false, |ext| ext == "proto"))
        .map(|e| e.path().to_str().unwrap().to_string())
        .collect();

    let include_dirs: Vec<String> = WalkDir::new(&proto_dir)
        .follow_links(true)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_dir())
        .map(|e| e.path().to_str().unwrap().to_string())
        .collect();

    prost_build::compile_protos(&proto_files, &include_dirs).unwrap();

    // Generate Thrift bindings
    generate_thrift_bindings();
}

fn find_workspace_root() -> Result<String, Box<dyn std::error::Error>> {
    let manifest_dir = env::var("CARGO_MANIFEST_DIR")?;
    let mut current = PathBuf::from(manifest_dir);

    loop {
        let cargo_toml = current.join("Cargo.toml");
        if cargo_toml.exists() {
            let content = fs::read_to_string(&cargo_toml)?;
            if content.contains("[workspace]") {
                return Ok(current.to_str().unwrap().to_string());
            }
        }

        if !current.pop() {
            break;
        }
    }

    Err("Could not find workspace root".into())
}

fn generate_thrift_bindings() {
    let workspace_dir = env::var("CARGO_WORKSPACE_DIR")
        .or_else(|_| find_workspace_root())
        .expect("Failed to find workspace root");

    let schema_dir = PathBuf::from(&workspace_dir)
        .join("ThriftTsConfig")
        .join("schema");

    println!("schema_dir: {}", schema_dir.display());

    let out_dir = env::var("OUT_DIR").unwrap();
    let thrift_out_dir = PathBuf::from(&out_dir).join("thrift");

    // Create output directory
    std::fs::create_dir_all(&thrift_out_dir).unwrap();

    // Find the main config.thrift file
    let config_thrift = schema_dir.join("config.thrift");

    println!("cargo:rerun-if-changed={}", schema_dir.display());
    println!("cargo:rerun-if-changed={}", config_thrift.display());

    // Generate Rust code using thrift compiler
    let mut cmd = std::process::Command::new("thrift");
    cmd.arg("--gen")
        .arg("rs")
        .arg("-r")
        .arg("-I")
        .arg(&schema_dir)
        .arg("-out")
        .arg(&thrift_out_dir)
        .arg(&config_thrift);

    let output = cmd
        .output()
        .expect("Failed to execute thrift compiler. Make sure 'thrift' is installed and in PATH.");

    if !output.status.success() {
        panic!(
            "Thrift compilation failed for {}: {}",
            config_thrift.display(),
            String::from_utf8_lossy(&output.stderr)
        );
    }

    // Post-process generated files to fix import paths
    fix_generated_imports(&thrift_out_dir);

    println!(
        "cargo:rustc-env=THRIFT_OUT_DIR={}",
        thrift_out_dir.display()
    );
}

fn fix_generated_imports(thrift_out_dir: &PathBuf) {
    // Walk through generated .rs files and fix imports
    for entry in WalkDir::new(thrift_out_dir)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        if entry.path().extension().map_or(false, |ext| ext == "rs") {
            let file_path = entry.path();
            let content = fs::read_to_string(file_path).unwrap();

            // Fix inner attributes to outer attributes
            let mut fixed_content = content
                .replace("#![allow(", "#[allow(")
                .replace("#![cfg_attr(", "#[cfg_attr(");

            // Fix imports by replacing crate:: with crate::thrift::
            fixed_content = fixed_content.replace("use crate::", "use crate::thrift::");

            fs::write(file_path, fixed_content).unwrap();
        }
    }
}
