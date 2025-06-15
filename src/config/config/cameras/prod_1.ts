import {
  type CameraParameters,
  type CameraType,
} from "../../../blitz/generated/thrift/ts_schema/camera_types";
import { MatrixUtil, VectorUtil } from "../util/math";

const prod1: CameraParameters = {
  pi_to_run_on: "tripoli",
  name: "one",
  camera_path: "0",
  flags: 0,
  width: 640,
  height: 480,
  max_fps: 30,
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
  camera_type: "OV2311" as unknown as CameraType, // unfortunately we have to do this because the thrift types are not properly exported
};

export default prod1;
