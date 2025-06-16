# Blitz Watchdog

A comprehensive process monitoring and system management service for the Blitz project. The watchdog monitors system processes, collects system statistics, and provides a REST API for process control.

## Overview

The watchdog service is responsible for:
- Monitoring and automatically restarting critical processes
- Collecting and publishing system statistics (CPU, memory, disk, network)
- Providing REST API endpoints for process management
- Managing configuration updates

## Components

### Core Modules

- **`main.py`** - Flask REST API server and main entry point
- **`monitor.py`** - Process monitoring and lifecycle management
- **`process_starter.py`** - Process launching utilities
- **`helper.py`** - System statistics collection and process types

## Supported Process Types

The watchdog can monitor the following process types:
- `position-extrapolator` - Position extrapolation service
- `lidar-reader-2d` - 2D LIDAR data reader
- `lidar-point-processor` - LIDAR point processing
- `lidar-processing` - General LIDAR processing
- `april-server` - Camera processing service

## API Endpoints

### Configuration Management

**POST** `/set/config`
```json
{
  "config": "json_config_string"
}
```
Updates the system configuration and saves it to `config/config.json`.

### Process Control

**POST** `/start/process`
```json
{
  "process_types": ["position-extrapolator", "lidar-reader-2d"]
}
```
Starts monitoring for the specified process types.

**POST** `/stop/process`
```json
{
  "process_types": ["position-extrapolator"]
}
```
Stops monitoring and terminates the specified processes.

## Features

### Process Monitoring
- Automatic process restart on failure
- Graceful process termination with child process cleanup
- Process health checking and status reporting

### System Statistics
Collects and publishes system metrics including:
- CPU usage (per-core and total)
- Memory usage percentage
- Disk usage percentage
- Network I/O statistics
- Top 10 running processes by resource usage

### Configuration
- Dynamic configuration updates via REST API
- Configurable statistics collection intervals
- Autobahn WebSocket publishing for real-time stats

## Usage

Start the watchdog service:
```bash
python -m blitz.watchdog.main
```

The service will:
1. Start the Flask API server on port 1000
2. Connect to Autobahn WebSocket server on localhost:8080
3. Begin system statistics collection and publishing

## Dependencies

- Flask - REST API server
- psutil - System and process utilities
- asyncio - Asynchronous operations
- Autobahn - WebSocket communication
- Protocol Buffers - Message serialization
