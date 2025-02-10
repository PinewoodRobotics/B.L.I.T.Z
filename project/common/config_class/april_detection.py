from pydantic import BaseModel


class AprilDetectionMessageConfig(BaseModel):
    post_camera_output_topic: str
    post_tag_output_topic: str


class AprilDetectionConfig(BaseModel):
    tag_size: float
    family: str
    nthreads: int
    quad_decimate: float
    quad_sigma: float
    refine_edges: bool
    decode_sharpening: float
    searchpath: str
    debug: bool
    message: AprilDetectionMessageConfig
