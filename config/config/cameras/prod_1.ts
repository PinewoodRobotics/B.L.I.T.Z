import { CameraParameters } from "../../generated_schema/camera_types";
import { MatrixUtil, VectorUtil } from "../util/math";

const prod1: CameraParameters = {
  pi_to_run_on: "tripoli",
  name: "one",
  camera_path: "/dev/video0",
  flags: 0,
  width: 640,
  height: 480,
  max_fps: 30,
  camera_matrix: MatrixUtil.buildMatrix<3, 3>([
    [545.67965312, 0, 432.72230551],
    [0, 549.31248491, 332.97096527],
    [0, 0, 1],
  ]),
  dist_coeff: VectorUtil.fromArray<5>([
    8.71187465e-3, -8.77374006e-2, -1.62906725e-5, -1.47495281e-3,
    2.16825631e-2,
  ]),
  exposure_time: 8,
};

export default prod1;
