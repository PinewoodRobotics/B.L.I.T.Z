#include <httplib.h>
#include <json/json.h>
#include <toml++/toml.h>

#include <iostream>
#include <thread>

#include "unitree_lidar_sdk.h"
#include "util/lidar_config.h"
#include "util/spherical_map.h"
#include "util/vector3.h"
#include "autobahn/autobahn.h"
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>

long long getCurrentTimeMs()
{
  auto now = std::chrono::system_clock::now();
  auto duration = now.time_since_epoch();
  return std::chrono::duration_cast<std::chrono::milliseconds>(duration)
      .count();
}

httplib::Server::Handler makePOSTHandler(SphericalMap &sphericalMap)
{
  return [&sphericalMap](const httplib::Request &req, httplib::Response &res)
  {
    try
    {
      Json::Value jsonData;
      Json::CharReaderBuilder reader;
      std::string errors;

      // Parse JSON from request body
      std::istringstream iss(req.body);
      if (!Json::parseFromStream(reader, iss, &jsonData, &errors))
      {
        res.status = 400;
        res.set_content("Invalid JSON: " + errors, "text/plain");
        return;
      }

      double originX = jsonData["origin"].get("x", 0.0).asFloat();
      double originY = jsonData["origin"].get("y", 0.0).asFloat();
      double originZ = jsonData["origin"].get("z", 0.0).asFloat();

      std::array<Vec3, 4> directions;
      for (int i = 0; i < 4; i++)
      {
        const auto &dir = jsonData["directions"][i];
        if (!dir.isObject())
        {
          res.status = 400;
          res.set_content(
              "Invalid 'direction' object at index " + std::to_string(i),
              "text/plain");
          return;
        }
        double directionX = dir.get("x", 0.0).asDouble();
        double directionY = dir.get("y", 0.0).asDouble();
        double directionZ = dir.get("z", 0.0).asDouble();
        directions[i] = Vec3(directionX, directionY, directionZ);
      }

      Frustum frustum(Vec3(originX, originY, originZ), directions);
      auto startTime = std::chrono::high_resolution_clock::now();
      auto points = sphericalMap.queryPointsInFrustum(frustum);

      Json::Value responseJson;
      for (const auto &point : points)
      {
        Json::Value pointJson;
        pointJson["x"] = point.x;
        pointJson["y"] = point.y;
        pointJson["z"] = point.z;
        pointJson["timestamp"] = point.timestamp;
        responseJson["points"].append(pointJson);
      }

      auto endTime = std::chrono::high_resolution_clock::now();
      auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
          endTime - startTime);

      std::cout << "Query time: " << duration.count() << "ms" << std::endl;

      Json::StreamWriterBuilder writer;
      res.set_content(Json::writeString(writer, responseJson),
                      "application/json");
    }
    catch (const std::exception &e)
    {
      res.status = 500;
      res.set_content(std::string("Server error: ") + e.what(), "text/plain");
    }
  };
}

int main()
{
  std::cout << "starting main" << std::endl;
  LidarConfig config;
  try
  {
    config = LidarConfig("../config/config.toml");
  }
  catch (const std::exception &e)
  {
    std::cerr << "Standard exception caught: " << e.what() << std::endl;
    return 1;
  }
  catch (...)
  {
    std::cerr << "Unknown exception caught!" << std::endl;
    return 1;
  }

  std::cout << "config: " << config.port_names.size() << std::endl;

  Address addr("127.0.0.1", 8080);
  Autobahn client(addr);
  auto connectionFuture = client.begin();
  connectionFuture.get();

  auto callback = [](const std::vector<uint8_t> &payload) {};
  auto subscribeFuture = client.subscribe("position-extrapolator/position", callback);
  subscribeFuture.get();

  std::vector<unitree_lidar_sdk::UnitreeLidarReader *> lidar_readers;
  SphericalMap sphericalMap(config.max_point_existence_time_ms, 50);
  for (auto port_name : config.port_names)
  {
    unitree_lidar_sdk::UnitreeLidarReader *lreader =
        unitree_lidar_sdk::createUnitreeLidarReader();
    if (lreader->initialize(config.cloud_scan_num, port_name))
    {
      printf("Unilidar initialization failed! Exit here!\n");
      exit(-1);
    }

    std::cout << "lidar reader initialized" << std::endl;

    lidar_readers.push_back(lreader);
  }

  httplib::Server svr;
  svr.Post("/post-json", makePOSTHandler(sphericalMap));

  std::thread server_thread(
      [&svr, &config]()
      { svr.listen("0.0.0.0", config.server_port); });

  sleep(1);

  for (auto lreader : lidar_readers)
  {
    lreader->setLidarWorkingMode(unitree_lidar_sdk::NORMAL);
    std::cout << "lidar reader set to standby" << std::endl;
  }

  unitree_lidar_sdk::MessageType result;
  while (true)
  {
    for (auto lreader : lidar_readers)
    {
      result = lreader->runParse();

      switch (result)
      {
      case unitree_lidar_sdk::NONE:
        break;

      case unitree_lidar_sdk::IMU:
        // TODO: idk maybe we can also use this imu somehow. dono tho...
        break;

      case unitree_lidar_sdk::POINTCLOUD:
        // std::cout << "lidar reader got pointcloud" << std::endl;
        for (auto point : lreader->getCloud().points)
        {
          sphericalMap.addPoint(point.y, point.z, point.x,
                                getCurrentTimeMs());
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