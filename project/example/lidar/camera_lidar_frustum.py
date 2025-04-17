import asyncio
import json
import time
import cv2
import nats
import numpy as np
import requests
import random
import open3d as o3d
from dataclasses import asdict, dataclass

from project.common.camera.box_frustum_conversion import bbox_to_frustum
from project.common.camera.image_inference_helper import ImageInferenceHelper
from generated.Image_pb2 import ImageMessage


@dataclass
class Point3D:
    x: float
    y: float
    z: float

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(json_str: str):
        data = json.loads(json_str)
        return Point3D(**data)


class LidarPointsFrustum:
    def __init__(self, port: int):
        self.port = port

    def get_frustum_points(self, origin: Point3D, other: list[Point3D]):
        headers = {"Content-Type": "application/json"}

        json_data = {
            "origin": {"x": origin.x, "y": origin.y, "z": origin.z},
            "directions": [{"x": p.x, "y": p.y, "z": p.z} for p in other],
        }

        response = requests.post(
            f"http://localhost:{self.port}/post-json", json=json_data, headers=headers
        )
        response.raise_for_status()

        json_res = response.json()

        if json_res is None or "points" not in json_res:
            return None
        return [Point3D(pt["x"], pt["y"], pt["z"]) for pt in json_res["points"]]


def render_frustum_and_points_with_axes(frustum_points, lidar_points):
    # Create frustum as a LineSet
    frustum_lines = [
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],  # Base
        [0, 4],
        [1, 4],
        [2, 4],
        [3, 4],  # Sides connecting to apex
    ]
    frustum_colors = [[0, 1, 0] for _ in range(len(frustum_lines))]  # Green lines

    frustum_vertices = np.array(frustum_points)
    frustum_lineset = o3d.geometry.LineSet(
        points=o3d.utility.Vector3dVector(frustum_vertices),
        lines=o3d.utility.Vector2iVector(frustum_lines),
    )
    frustum_lineset.colors = o3d.utility.Vector3dVector(frustum_colors)
    coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
        size=1.0, origin=[0, 0, 0]
    )

    if lidar_points is not None:
        # Create point cloud for lidar points
        lidar_points_np = np.array([[p.x, p.y, p.z] for p in lidar_points])
        lidar_point_cloud = o3d.geometry.PointCloud()
        lidar_point_cloud.points = o3d.utility.Vector3dVector(lidar_points_np)
        lidar_point_cloud.paint_uniform_color([1, 0, 0])  # Red points

        # Add coordinate axes
        return [frustum_lineset, lidar_point_cloud, coordinate_frame]
    # Combine geometries

    return [frustum_lineset, coordinate_frame]


def create_sphere_mesh(center, radius=0.02, color=[1, 0, 0]):
    sphere = o3d.geometry.TriangleMesh.create_sphere(radius=radius)
    sphere.translate(center)
    sphere.paint_uniform_color(color)
    return sphere


def update_spheres_mesh(spheres_mesh, points, radius=0.02, color=[1, 0, 0]):
    """
    Update a single mesh to represent lidar points as spheres.
    This avoids adding and removing multiple geometries, preserving the camera viewpoint.
    """
    combined_mesh = o3d.geometry.TriangleMesh()
    for point in points:
        sphere = create_sphere_mesh(point, radius=radius, color=color)
        combined_mesh += sphere
    spheres_mesh.clear()
    spheres_mesh += combined_mesh


async def main():
    cap = cv2.VideoCapture(0)
    lidar_frustum = LidarPointsFrustum(8080)
    camera_matrix = np.array(
        [  # for small black camera
            [1411.0, 0.0, 1411.0 / 4.5],
            [0.0, 1408.0, 1408.0 / 6],
            [0.0, 0.0, 1.0],
        ]
    )
    _dist_coef = np.array(
        [
            -0.4513475113205368,
            0.21139658631382788,
            -0.0028846973373456855,
            0.0021349747481580624,
            -0.055584296827295585,
        ]
    )
    origin = Point3D(0, 0, 0)

    image_inference_helper = ImageInferenceHelper(
        await nats.connect("nats://localhost:4222"),
        "recognition/image_input",
        "recognition/image_output",
    )
    await image_inference_helper.start_subscribe()

    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Frustum and Lidar Points", width=1500, height=1411)
    coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
        size=1.0, origin=[0, 0, 0]
    )
    vis.add_geometry(coordinate_frame)

    vis.get_view_control().set_constant_z_far(1000)

    frustum_lineset = o3d.geometry.LineSet()
    vis.add_geometry(frustum_lineset)

    # Create a single mesh for lidar spheres
    lidar_spheres_mesh = o3d.geometry.TriangleMesh()
    vis.add_geometry(lidar_spheres_mesh)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            _, compressed_image = cv2.imencode(".jpg", frame)

            image_id = random.randint(0, 1000000)
            msg = ImageMessage(
                image=compressed_image.tobytes(),
                camera_name="camera0",
                is_gray=False,
                id=image_id,
                height=frame.shape[0],
                width=frame.shape[1],
                timestamp=int(time.time() * 1000),
            )

            await image_inference_helper.send_image_message(msg, frame)
            inference = await image_inference_helper.get_latest_inference()

            for inf in inference.inferences:
                bounding_box = inf.bounding_box

                frustum_points = bbox_to_frustum(camera_matrix, bounding_box, 10)
                lidar_points = lidar_frustum.get_frustum_points(
                    origin, [Point3D(pt[0], pt[1], pt[2]) for pt in frustum_points]
                )

                # print(lidar_points)

                # Update frustum geometry
                frustum_lineset.points = o3d.utility.Vector3dVector(
                    np.array(frustum_points)
                )
                frustum_lineset.lines = o3d.utility.Vector2iVector(
                    [[0, 1], [1, 2], [2, 3], [3, 0], [0, 4], [1, 4], [2, 4], [3, 4]]
                )
                frustum_lineset.colors = o3d.utility.Vector3dVector([[0, 1, 0]] * 8)

                # Update lidar spheres mesh
                if lidar_points:
                    lidar_points_np = np.array([[p.x, p.y, p.z] for p in lidar_points])
                    update_spheres_mesh(lidar_spheres_mesh, lidar_points_np)

                # Update visualizer
                vis.update_geometry(frustum_lineset)
                vis.update_geometry(lidar_spheres_mesh)
                vis.poll_events()
                vis.update_renderer()

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        vis.destroy_window()


asyncio.run(main())
