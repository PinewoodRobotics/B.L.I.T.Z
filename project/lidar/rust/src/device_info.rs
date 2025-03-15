use std::fs;
use std::io;

pub fn get_system_name() -> io::Result<String> {
    fs::read_to_string("name.txt").map(|s| s.trim().to_string())
}
