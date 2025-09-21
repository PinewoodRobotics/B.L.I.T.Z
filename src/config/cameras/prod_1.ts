import { type CameraParameters } from "generated/thrift/gen-nodejs/camera_types";
import { MatrixUtil, VectorUtil } from "../util/math";
import { CameraTypeE, CameraTypeUtil } from "../util/struct";

const prod1: CameraParameters = {
  pi_to_run_on: "agathaking",
  name: "one",
  camera_path: "/dev/usb_top_left_cam",
  flags: 0,
  width: 1280,
  height: 720,
  max_fps: 60,
  camera_matrix: MatrixUtil.buildMatrix([
    [1049.942799553104, 0.0, 561.9225142372616],
    [0.0, 1052.4526742839457, 360.83362717632707],
    [0.0, 0.0, 1.0],
  ]),
  dist_coeff: VectorUtil.fromArray([
    -0.482563871739925, 0.23813344092383001, -0.0029867183132381452,
    0.015132672208272843, -0.08845096264340181,
  ]),
  exposure_time: 10,
  camera_type: CameraTypeUtil.fromEnum(CameraTypeE.OV2311),
  compression_quality: 20,
  do_compression: true,
};

export default prod1;
