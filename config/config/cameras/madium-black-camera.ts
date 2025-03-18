import type { CameraParameters } from "../../schema/camera";
import { buildMatrixFromArray, buildVector } from "../util/math";

const mediumBlackCam: CameraParameters = {
  name: "medium-black-cam",
  port: 2,
  flags: 120,
  width: 640,
  height: 480,
  max_fps: 30,
  camera_matrix: buildMatrixFromArray<number, 3, 3>([
    [644.12542785, 0.0, 318.47939346],
    [0.0, 639.36517808, 218.74994066],
    [0.0, 0.0, 1.0],
  ]),
  dist_coeff: buildVector<number, 5>(
    -0.43899338,
    0.33405716,
    0.00489076,
    -0.00426836,
    -0.3116031
  ),
  pi_to_run_on: "tripoli",
};

export default mediumBlackCam;
