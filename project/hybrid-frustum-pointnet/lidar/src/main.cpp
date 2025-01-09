#include <httplib.h>
#include <json/json.h>
#include <toml++/toml.h>

#include <iostream>
#include <thread>

#include "unitree_lidar_sdk.h"
#include "util/lidar_config.h"
#include "util/spherical_map.h"
#include "util/vector3.h"

httplib::Server::Handler makePOSTHandler(SphericalMap &sphericalMap) {
  return [&sphericalMap](const httplib::Request &req, httplib::Response &res) {
    try {
      Json::Value jsonData;
      Json::CharReaderBuilder reader;
      std::string errors;

      double originX = jsonData["origin"]["x"].asDouble();
      double originY = jsonData["origin"]["y"].asDouble();
      double originZ = jsonData["origin"]["z"].asDouble();

      std::array<Vec3, 4> directions;
      for (int i = 0; i < 4; i++) {
        double directionX = jsonData["directions"][i]["x"].asDouble();
        double directionY = jsonData["directions"][i]["y"].asDouble();
        double directionZ = jsonData["directions"][i]["z"].asDouble();
        directions[i] = Vec3(directionX, directionY, directionZ);
      }

      Frustum frustum(Vec3(originX, originY, originZ), directions);

      auto startTime = std::chrono::high_resolution_clock::now();  // debug

      auto points = sphericalMap.queryPointsInFrustum(frustum);

      Json::Value responseJson;
      for (const auto &point : points) {
        Json::Value pointJson;
        pointJson["x"] = point.x;
        pointJson["y"] = point.y;
        pointJson["z"] = point.z;
        pointJson["timestamp"] = point.timestamp;
        responseJson["points"].append(pointJson);
      }

      auto endTime = std::chrono::high_resolution_clock::now();  // debug
      auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
          endTime - startTime);  // debug

      std::cout << "Query time: " << duration.count() << "ms"
                << std::endl;  // debug

      Json::StreamWriterBuilder writer;
      res.set_content(Json::writeString(writer, responseJson),
                      "application/json");
    } catch (const std::exception &e) {
      res.status = 500;
      res.set_content(std::string("Server error: ") + e.what(), "text/plain");
    }
  };
}

int main() {
  std::cout << "starting main" << std::endl;
  LidarConfig config;
  try {
    config = LidarConfig("../config/config.toml");
  } catch (const std::exception &e) {
    std::cerr << "Standard exception caught: " << e.what() << std::endl;
    return 1;
  } catch (...) {
    std::cerr << "Unknown exception caught!" << std::endl;
    return 1;
  }

  std::cout << "config: " << config.port_names.size() << std::endl;

  std::vector<unitree_lidar_sdk::UnitreeLidarReader *> lidar_readers;
  SphericalMap sphericalMap(config.max_point_existence_time_ms, 50);
  for (auto port_name : config.port_names) {
    unitree_lidar_sdk::UnitreeLidarReader *lreader =
        unitree_lidar_sdk::createUnitreeLidarReader();
    if (lreader->initialize(config.cloud_scan_num, port_name)) {
      printf("Unilidar initialization failed! Exit here!\n");
      exit(-1);
    }

    std::cout << "lidar reader initialized" << std::endl;

    lidar_readers.push_back(lreader);
  }

  httplib::Server svr;
  svr.Post("/post-json", makePOSTHandler(sphericalMap));

  std::thread server_thread(
      [&svr, &config]() { svr.listen("0.0.0.0", config.server_port); });

  sleep(1);

  for (auto lreader : lidar_readers) {
    lreader->setLidarWorkingMode(unitree_lidar_sdk::STANDBY);
    std::cout << "lidar reader set to standby" << std::endl;
  }

  unitree_lidar_sdk::MessageType result;
  while (true) {
    for (auto lreader : lidar_readers) {
      result = lreader->runParse();

      switch (result) {
        case unitree_lidar_sdk::NONE:
          break;

        case unitree_lidar_sdk::IMU:
          // TODO: idk maybe we can also use this imu somehow. dono tho...
          break;

        case unitree_lidar_sdk::POINTCLOUD:
          std::cout << "lidar reader got pointcloud" << std::endl;
          for (auto point : lreader->getCloud().points) {
            sphericalMap.addPoint(point.x, point.y, point.z, point.time);
          }
          break;

        default:
          break;
      }
    }

    usleep(500);
  }

  return 0;
}
