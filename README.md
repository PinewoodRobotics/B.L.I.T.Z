# B.L.I.T.Z (Battle-Linked Intelligent Tactical Pi Swarm)

BLITZ is a robotics project designed to create a swarm of intelligent tactical Pi-based robots that can work together collaboratively.

## Overview

The BLITZ system combines multiple components for sensing, positioning, AI detection, and coordinated movement. It uses a hybrid approach with both Python and Rust for different system components.

## Features

- LiDAR-based obstacle detection and mapping (2D and 3D)
- Computer vision for object recognition
- AprilTag-based positioning system
- Position extrapolation
- Watchdog monitoring

## Technologies

### Languages
- Python
- Rust
- TypeScript/JavaScript

### Major Dependencies
- Python: PyTorch, OpenCV, Flask, NumPy, UltraLytics
- Rust: Tokio, Nalgebra, Kiss3D
- Communication: Protobuf, Thrift

## Getting Started

### Prerequisites
- Python 3.x
- Rust and Cargo
- npm/Node.js

### Installation

Set up the Python environment and install dependencies:

```bash
make initiate-project
```

### Code Generation

Generate required protocol buffer and Thrift files:

```bash
make generate
```

## Usage

Start the various system components:

```bash
# AI detection server
make ai-server

# AprilTag positioning server
make april-server

# 2D LiDAR reader
make lidar-reader-2d

# LiDAR point processor
make lidar-point-processor

# Position extrapolation system
make position-extrapolator

# System monitoring watchdog
make watchdog
```

## Development

- Run linting: `make check-all`
- Run tests: `make test`
- Deploy to a target: `make send-to-target ARGS=<target-id>`

## Project Structure

- `project/`: Main source code
  - `lidar/`: LiDAR data processing components
  - `recognition/`: Computer vision and positioning
  - `pos_extrapolator/`: Position prediction system
  - `watchdog/`: System monitoring
  - `rust/`: Rust components for performance-critical operations
- `proto/`: Protocol buffer definitions
- `config/`: System configuration
- `generated/`: Generated code (Protobuf, Thrift)
- `scripts/`: Utility scripts

## License

ISC License

## Repository

GitHub: [https://github.com/PinewoodRobotics/B.L.I.T.Z](https://github.com/PinewoodRobotics/B.L.I.T.Z)
