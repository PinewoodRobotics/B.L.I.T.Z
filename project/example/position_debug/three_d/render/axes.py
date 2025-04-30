from ursina import *


class Axes(Entity):
    def __init__(self, length: float = 1, thickness: float = 0.02, **kwargs):
        super().__init__(**kwargs)
        # X axis
        Entity(
            parent=self,
            model="cube",
            color=color.red,
            scale=(length, thickness, thickness),
            position=(length / 2, 0, 0),
        )
        # Y axis
        Entity(
            parent=self,
            model="cube",
            color=color.green,
            scale=(thickness, length, thickness),
            position=(0, length / 2, 0),
        )
        # Z axis
        Entity(
            parent=self,
            model="cube",
            color=color.blue,
            scale=(thickness, thickness, length),
            position=(0, 0, length / 2),
        )


'''
def render_point_cloud_instanced(
    points, point_size=0.1, color=color.white, parent=None
):
    """
    Alternative renderer using instanced rendering for maximum performance
    with very large point clouds.

    Args:
        points (list): List of point positions as Vec3 or tuples (x,y,z)
        point_size (float): Size of each point
        color: Either a single Color or a list of Colors (one per point)
        parent (Entity): Optional parent entity

    Returns:
        Entity: Point cloud entity
    """
    # Create a parent entity
    point_cloud = Entity(parent=parent)

    try:
        from ursina.shaders import instancing_shader

        # Create a single point sphere with instancing shader
        point = Entity(
            parent=point_cloud,
            model="sphere",
            scale=point_size,
            shader=instancing_shader,
            color=color if not isinstance(color, list) else color.white,
        )

        # Set instance count based on number of points
        point.setInstanceCount(len(points))

        # Set offsets for all instances
        point.set_shader_input("position_offsets", points)

        # Handle colors
        if isinstance(color, list) and len(color) == len(points):
            point.set_shader_input("colors", color)

    except (ImportError, AttributeError):
        print(
            "Warning: Instanced rendering not available. Falling back to standard point cloud."
        )
        return render_point_cloud(points, point_size, color, parent)

    return point_cloud
'''
