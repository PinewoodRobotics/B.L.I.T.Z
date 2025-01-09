#include <iostream>
#include <pcl/point_types.h>
#include <pcl/visualization/pcl_visualizer.h>
#include <boost/thread/pthread/thread_data.hpp>
#include "unitree_lidar_sdk.h"

int main()
{
    // Lidar initialization
    unitree_lidar_sdk::UnitreeLidarReader *lreader = unitree_lidar_sdk::createUnitreeLidarReader();
    if (lreader->initialize(100, "/dev/ttyUSB0"))
    { // Replace "/dev/ttyUSB0" with your actual lidar port
        printf("Unilidar initialization failed! Exit here!\n");
        exit(-1);
    }

    std::cout << "lidar reader initialized" << std::endl;

    // Create a PCL visualizer
    pcl::visualization::PCLVisualizer viewer("3D Viewer");
    viewer.setBackgroundColor(0, 0, 0);
    viewer.addCoordinateSystem(1.0);
    viewer.initCameraParameters();

    while (true)
    {
        std::cout << "!!!!" << std::endl;
        // Get point cloud from lidar
        unitree_lidar_sdk::MessageType result = lreader->runParse();
        if (result == unitree_lidar_sdk::POINTCLOUD)
        {
            std::cout << "lidar reader got pointcloud" << std::endl;
            pcl::PointCloud<pcl::PointXYZ>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZ>());

            auto pointCloud = lreader->getCloud();

            // Ensure the point cloud is valid
            if (pointCloud.points.empty()) {
                std::cout << "No points in the point cloud!" << std::endl;
                continue;
            }

            cloud->width = pointCloud.points.size();
            cloud->height = 1;
            for (int i = 0; i < pointCloud.points.size(); i++)
            {
                cloud->points.push_back(pcl::PointXYZ(pointCloud.points[i].x, pointCloud.points[i].y, pointCloud.points[i].z));
            }

            // Clear previous point cloud
            viewer.removeAllPointClouds();

            // Add new point cloud to visualizer
            viewer.addPointCloud<pcl::PointXYZ>(cloud, "sample cloud");
            viewer.setPointCloudRenderingProperties(1, 1, "sample cloud");
        }

        // Update visualizer
        viewer.spinOnce(100);
    }


    return 0;
}