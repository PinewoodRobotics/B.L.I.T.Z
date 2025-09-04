import { type CameraParameters } from "generated/thrift/gen-nodejs/camera_types";
import { MatrixUtil, VectorUtil } from "../util/math";
import { CameraTypeE, CameraTypeUtil } from "../util/struct";

const prod1: CameraParameters = {
  pi_to_run_on: "tripoli",
  name: "one",
  camera_path: "/dev/video0",
  flags: 0,
  width: 800,
  height: 600,
  max_fps: 100,
  camera_matrix: MatrixUtil.buildMatrix<3, 3>([
    [454.7917491985464, 0.0, 405.6029022992675],
    [0.0, 454.729749644609, 321.75698981738134],
    [0.0, 0.0, 1.0],
  ]),
  dist_coeff: VectorUtil.fromArray<5>([
    0.04216332435519303, -0.06145045363038189, 5.072789006860842e-6,
    -0.0002106044632593869, 0.004071613340637429,
  ]),
  exposure_time: 8,
  camera_type: CameraTypeUtil.fromEnum(CameraTypeE.OV2311),
};

export default prod1;
