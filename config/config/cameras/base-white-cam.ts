import type { CameraParameters } from "../../schema/camera";
import { buildMatrixFromArray, buildVector } from "../util/math";

const baseWhiteCam: CameraParameters = {
  name: "base-white-cam",
  port: 0,
  flags: 120,
  width: 640,
  height: 480,
  max_fps: 30,
  camera_matrix: buildMatrixFromArray<number, 3, 3>([
    [582.60632078, 0.0, 352.39906585],
    [0.0, 586.62228744, 242.78557652],
    [0.0, 0.0, 1.0],
  ]),
  dist_coeff: buildVector<number, 5>(
    -0.31413388,
    -0.08118998,
    -0.00139866,
    -0.00150931,
    0.31581663
  ),
  direction_vector: buildVector<number, 3>(0.0, 0.0, 0.0),
  position: buildVector<number, 3>(0.0, 0.0, 0.0),
};

export default baseWhiteCam;
