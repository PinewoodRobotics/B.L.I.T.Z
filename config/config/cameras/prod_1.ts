import type { CameraParameters } from "../../schema/camera";
import { buildMatrixFromArray, buildVector } from "../util/math";

const prod1: CameraParameters = {
  pi_to_run_on: "tripoli",
  name: "front_right",
  port: 0,
  flags: 120,
  width: 640,
  height: 480,
  max_fps: 30,
  camera_matrix: buildMatrixFromArray<number, 3, 3>([
    [235.33329217, 0.0, 316.90720596],
    [0.0, 235.35214724, 229.1143798],
    [0.0, 0.0, 1.0],
  ]),
  dist_coeff: buildVector<number, 5>(
    0.00949906,
    -0.03209404,
    0.00047645,
    0.00056713,
    0.00574621
  ),
};

export default prod1;
