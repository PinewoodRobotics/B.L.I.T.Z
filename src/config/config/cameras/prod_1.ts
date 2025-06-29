import { type CameraParameters } from "../../../blitz/generated/thrift/gen-nodejs/camera_types";
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
    [450, 0, 400],
    [0, 450, 300],
    [0, 0, 1],
  ]),
  dist_coeff: VectorUtil.fromArray<5>([
    0.02421893240091871, -0.019483745628435203, -0.0002353973963860865,
    0.0010526889774734997, -0.032565426732841275,
  ]),
  exposure_time: 8,
  camera_type: CameraTypeUtil.fromEnum(CameraTypeE.OV2311),
};

export default prod1;
