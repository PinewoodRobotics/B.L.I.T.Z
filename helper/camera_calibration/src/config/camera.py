from pydantic import BaseModel


class CameraConfig(BaseModel):
    camera_port: int
