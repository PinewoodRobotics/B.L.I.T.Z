import type { CameraParameters } from "../../schema/camera";
import { buildMatrixFromArray, buildVector } from "../util/math";

const arducam_1: CameraParameters = {
  pi_to_run_on: "tripoli",
  name: "rear_left",
  port: 0,
  flags: 120,
  width: 640,
  height: 480,
  max_fps: 30,
  camera_matrix: buildMatrixFromArray<number, 3, 3>([
    [563.0486962, 0, 330.88254863],
    [0, 564.21292152, 251.09757613],
    [0, 0, 1],
  ]),
  dist_coeff: buildVector<number, 5>(
    0.00151333,
    0.27473498,
    0.00333275,
    0.00333855,
    -0.4665363
  ),
};

export default arducam_1;
