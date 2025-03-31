import type { CameraParameters } from "../../schema/camera";
import { buildMatrixFromArray, buildVector } from "../util/math";

const prod1: CameraParameters = {
  pi_to_run_on: "tripoli",
  name: "front_right",
  camera_path: "/dev/video0",
  flags: 0,
  width: 640,
  height: 480,
  max_fps: 30,
  camera_matrix: buildMatrixFromArray<number, 3, 3>([
    [545.67965312, 0, 432.72230551],
    [0, 549.31248491, 332.97096527],
    [0, 0, 1],
  ]),
  dist_coeff: buildVector<number, 5>(
    8.71187465e-3,
    -8.77374006e-2,
    -1.62906725e-5,
    -1.47495281e-3,
    2.16825631e-2
  ),
};

export default prod1;
