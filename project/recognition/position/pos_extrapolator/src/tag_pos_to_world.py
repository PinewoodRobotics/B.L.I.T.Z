from pydantic import BaseModel


class TagPos(BaseModel):
    x: float
    y: float
    z: float


class TagPosConfig(BaseModel):
    tags_list: list[TagPos]


class TagPosToWorld:
    def __init__(self, file_path: str, mock=False):
        if mock:
            self.tag_pos_config = TagPosConfig(tags_list=[TagPos(x=0, y=0, z=0)])
        else:
            self.tag_pos_config = TagPosConfig.model_validate_json(
                open(file_path).read()
            )
        self.mock = mock

    def get_world_pos(
        self, tag_pos: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        if self.mock:
            return (
                tag_pos[0] + self.tag_pos_config.tags_list[0].x,
                tag_pos[1] + self.tag_pos_config.tags_list[0].y,
                tag_pos[2] + self.tag_pos_config.tags_list[0].z,
            )
        else:
            return tag_pos
