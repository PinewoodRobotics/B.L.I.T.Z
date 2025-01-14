from pydantic import BaseModel

from schema.update_calibration_params import (
    UpdateCalibrationParams,
)


class CheckerboardConfig(BaseModel):
    cols: int
    rows: int
    square_size: float

    def update_config(self, new_config: UpdateCalibrationParams):
        self.cols = new_config.checkerboard_width
        self.rows = new_config.checkerboard_height
        self.square_size = new_config.checkerboard_square_size


class CalibrationConfig(BaseModel):
    checkerboard: CheckerboardConfig
