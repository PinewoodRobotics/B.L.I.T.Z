#ifndef LIDAR_CONFIG_H
#define LIDAR_CONFIG_H
#include <iostream>
#include <string>
#include <toml++/impl/parser.inl>

namespace toml::v3::ex {
class parse_error;
}

class LidarConfig {
 public:
  LidarConfig() {}

  explicit LidarConfig(const std::string &filename) {
    try {
      std::cout << "Parsing TOML file: " << filename << std::endl;
      auto config_table = toml::parse_file(filename);
      const auto &lidar = config_table["lidar"];

      if (auto ports_array = lidar["port_names"].as_array()) {
        for (const auto &item : *ports_array) {
          if (auto port = item.value<std::string>()) {
            this->port_names.push_back(*port);
          } else {
            throw std::runtime_error("Invalid type in 'port_names' array.");
          }
        }
      } else {
        throw std::runtime_error("'port_names' is missing or not an array.");
      }

      this->cloud_scan_num = lidar["cloud_scan_num"].as_integer()->get();
      this->max_point_existence_time_ms =
          lidar["max_point_existence_time_ms"].as_floating_point()->get();
      this->server_port = lidar["server_port"].as_integer()->get();

      // Parse autobahn configuration
      this->autobahn_host = lidar["autobahn_host"].as_string()->get();
      this->autobahn_port = lidar["autobahn_port"].as_string()->get();

      this->min_height = lidar["min_height"].as_floating_point()->get();
      this->max_height = lidar["max_height"].as_floating_point()->get();

      std::cout << "TOML parsing succeeded." << std::endl;
    } catch (const toml::v3::ex::parse_error &err) {
      std::cerr << "Parsing failed: " << err << "\n";
      throw;
    }
  }

  std::vector<std::string> port_names;
  int cloud_scan_num = 0;
  double max_point_existence_time_ms = 0;
  int server_port = 0;
  std::string autobahn_host = "";
  std::string autobahn_port = "";
  float min_height = 0;
  float max_height = 0;
};

#endif  // LIDAR_CONFIG_H
