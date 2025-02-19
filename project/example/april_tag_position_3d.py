import asyncio
import numpy as np
import open3d as o3d
from project.autobahn.autobahn_python.Listener import Autobahn
from generated.AprilTag_pb2 import AprilTags
from queue import Queue


class SimpleTagVisualizer:
    def __init__(self):
        # Initialize Open3D visualizer
        self.vis = o3d.visualization.Visualizer()
        self.vis.create_window(window_name="AprilTag Positions", width=1024, height=768)
        self.vis.get_view_control().set_constant_z_far(1000)

        # Add coordinate system at origin
        self.origin_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5)
        self.vis.add_geometry(self.origin_frame)

        # Dictionary to store tag LineSet geometries
        self.tag_markers = {}

        # Set up camera view (looking down +Y axis)
        self.setup_camera()

    def setup_camera(self):
        ctr = self.vis.get_view_control()
        ctr.set_zoom(0.8)
        ctr.set_front([0, -1, 0])  # Looking down +Y axis
        ctr.set_up([0, 0, 1])  # Z is up

    def update_tag_position(self, tag_id, position, pos_R=None):
        # Define tag size and corners
        tag_size = 0.04
        half_size = tag_size / 2
        corners = np.array(
            [
                [-half_size, -half_size, 0],  # Bottom-left
                [half_size, -half_size, 0],  # Bottom-right
                [half_size, half_size, 0],  # Top-right
                [-half_size, half_size, 0],  # Top-left
            ]
        )

        # Transform corners to tag position
        corners = corners + position

        # Define lines connecting corners
        lines = [[0, 1], [1, 2], [2, 3], [3, 0]]  # Square outline
        colors = [[1, 0, 0] for _ in range(len(lines))]  # Red lines

        if tag_id not in self.tag_markers:
            # Create a new LineSet if the tag is not already visualized
            line_set = o3d.geometry.LineSet()
            line_set.points = o3d.utility.Vector3dVector(corners)
            line_set.lines = o3d.utility.Vector2iVector(lines)
            line_set.colors = o3d.utility.Vector3dVector(colors)
            self.tag_markers[tag_id] = line_set
            self.vis.add_geometry(line_set)
        else:
            # Update existing LineSet
            line_set = self.tag_markers[tag_id]
            line_set.points = o3d.utility.Vector3dVector(corners)

        # Add a directional vector if rotation matrix is provided
        if pos_R is not None:
            forward_vector = np.array(
                [0, 0, 1]
            )  # Define the "forward" direction in local frame
            rotated_vector = (
                pos_R @ forward_vector
            )  # Rotate it to the tag's orientation
            arrow_start = position
            arrow_end = position + 0.1 * rotated_vector  # Scale for visualization

            # Create an arrow geometry
            arrow = o3d.geometry.TriangleMesh.create_arrow(
                cone_radius=0.01,
                cone_height=0.03,
                cylinder_radius=0.005,
                cylinder_height=0.07,
            )
            arrow.translate(arrow_start)
            arrow_direction = arrow_end - arrow_start
            arrow_length = np.linalg.norm(arrow_direction)
            arrow_direction /= arrow_length  # Normalize

            # Apply rotation to align the arrow
            z_axis = np.array([0, 0, 1])  # Default arrow points along Z
            axis_rotation = np.cross(z_axis, arrow_direction)
            if np.linalg.norm(axis_rotation) > 1e-6:  # Avoid divide-by-zero
                axis_rotation /= np.linalg.norm(axis_rotation)
            angle = np.arccos(np.dot(z_axis, arrow_direction))
            R_arrow = o3d.geometry.get_rotation_matrix_from_axis_angle(
                axis_rotation * angle
            )

            arrow.rotate(R_arrow, center=arrow_start)

            # Check if the arrow already exists
            arrow_key = f"{tag_id}_arrow"
            if arrow_key in self.tag_markers:
                self.vis.remove_geometry(self.tag_markers[arrow_key])
            self.vis.add_geometry(arrow)
            self.tag_markers[arrow_key] = arrow

    def poll_events(self):
        for tag_id, line_set in self.tag_markers.items():
            self.vis.update_geometry(line_set)
        self.vis.poll_events()
        self.vis.update_renderer()

    def close(self):
        self.vis.destroy_window()


async def main():
    autobahn_server = Autobahn("localhost", 8080)
    await autobahn_server.begin()

    visualizer = SimpleTagVisualizer()
    update_queue = Queue()

    async def process_tags(msg: bytes):
        res = AprilTags()
        res.ParseFromString(msg)

        for tag in res.tags:
            # Extract position
            position = np.array(
                [
                    tag.position_x_relative,
                    tag.position_y_relative,
                    tag.position_z_relative,
                ],
                dtype=np.float64,
            )

            # Extract rotation matrix
            pos_R = np.array(
                [
                    [tag.pose_R[0], tag.pose_R[1], tag.pose_R[2]],
                    [tag.pose_R[3], tag.pose_R[4], tag.pose_R[5]],
                    [tag.pose_R[6], tag.pose_R[7], tag.pose_R[8]],
                ],
                dtype=np.float64,
            )

            # Use tag ID as identifier
            tag_id = tag.tag_id

            # Queue the update for thread safety
            update_queue.put((tag_id, position, pos_R))

    await autobahn_server.subscribe("apriltag/tag", process_tags)

    try:
        while True:
            # Process visualization updates from the queue
            while not update_queue.empty():
                tag_id, position, pos_R = update_queue.get()
                visualizer.update_tag_position(tag_id, position, pos_R)

            visualizer.poll_events()  # Continuously refresh Open3D window
            await asyncio.sleep(0.01)  # Prevent busy waiting

    except KeyboardInterrupt:
        print("Closing visualizer...")
    finally:
        visualizer.close()


if __name__ == "__main__":
    asyncio.run(main())
