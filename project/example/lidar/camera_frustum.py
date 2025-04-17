import asyncio
import time
import cv2
import nats
import numpy as np
from asyncio import CancelledError
import open3d
import random

from project.common.camera.box_frustum_conversion import bbox_to_frustum
from project.common.camera.image_inference_helper import ImageInferenceHelper
from project.common.camera.transform import unfisheye_image
from generated.Image_pb2 import ImageMessage

from open3d import visualization

camera_matrix = np.array(
    [
        [1487.1124346674526, 0.0, 945.122412363984],
        [0.0, 1434.705975660968, 547.8805261625706],
        [0.0, 0.0, 1.0],
    ]
)

dist_coef = np.array(
    [
        -0.4513475113205368,
        0.21139658631382788,
        -0.0028846973373456855,
        0.0021349747481580624,
        -0.055584296827295585,
    ]
)


def create_frustum_geometry(frustum_points):
    """
    Create a LineSet geometry for the camera frustum.

    :param frustum_points: List of 3D points [(x, y, z), ...] representing the corners of the frustum.
    :return: Open3D LineSet object representing the frustum.
    """
    lines = [
        [0, 1],
        [1, 3],
        [3, 2],
        [2, 0],  # Rectangle (base)
        [0, 4],
        [1, 4],
        [2, 4],
        [3, 4],  # Connecting lines to the camera
    ]
    colors = [[1, 0, 0] for _ in lines]  # Set line color (red)

    line_set = open3d.geometry.LineSet()
    line_set.points = open3d.utility.Vector3dVector(frustum_points)
    line_set.lines = open3d.utility.Vector2iVector(lines)
    line_set.colors = open3d.utility.Vector3dVector(colors)

    return line_set


async def main():
    cap = cv2.VideoCapture(2)
    nt = await nats.connect("nats://localhost:4222")
    image_inference_helper = ImageInferenceHelper(
        nt, "recognition/image_input", "recognition/image_output"
    )
    await image_inference_helper.start_subscribe()

    vis = visualization.Visualizer()  # Open3D visualizer
    vis.create_window()

    # Geometry placeholders
    frustum_geometry = None
    image_geometry = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            unfisheyed_image = unfisheye_image(frame, camera_matrix, dist_coef)

            # Convert the frame to Open3D Image format
            o3d_image = open3d.geometry.Image(
                cv2.cvtColor(unfisheyed_image, cv2.COLOR_BGR2RGB)
            )

            # Encode and prepare image message
            _, compressed_image = cv2.imencode(".jpg", unfisheyed_image)
            image_id = random.randint(0, 1000000)

            msg = ImageMessage(
                image=compressed_image.tobytes(),
                camera_name="camera0",
                is_gray=False,
                image_id=image_id,
                height=unfisheyed_image.shape[0],
                width=unfisheyed_image.shape[1],
                timestamp=int(time.time() * 1000),
            )

            await image_inference_helper.send_image_message(msg, unfisheyed_image)

            # Update Open3D visualization
            if image_geometry is None:
                image_geometry = o3d_image
                vis.add_geometry(image_geometry)
            else:
                image_geometry.clear()
                image_geometry = o3d_image
                vis.update_geometry(image_geometry)

            inference = await image_inference_helper.get_latest_inference()
            for inf in inference.inferences:
                frustum_points = bbox_to_frustum(camera_matrix, inf.bounding_box, 0.5)
                frustum_points.append((0, 0, 0))

                # Update frustum geometry
                if frustum_geometry is None:
                    frustum_geometry = create_frustum_geometry(frustum_points)
                    vis.add_geometry(frustum_geometry)
                else:
                    frustum_geometry.points = open3d.utility.Vector3dVector(
                        frustum_points
                    )
                    vis.update_geometry(frustum_geometry)

            vis.poll_events()
            vis.update_renderer()

    except KeyboardInterrupt:
        print("Exiting...")
    except CancelledError:
        print("Exiting...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        vis.destroy_window()


asyncio.run(main())
