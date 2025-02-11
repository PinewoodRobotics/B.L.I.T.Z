import type { CameraParameters } from "../../schema/camera";
import { buildMatrixFromArray, buildVector } from "../util/math";

const large640480: CameraParameters = {
  name: "large-640-480",
  port: 0,
  flags: 120,
  width: 640,
  height: 480,
  max_fps: 30,
  camera_matrix: buildMatrixFromArray<number, 3, 3>([
    [714.3657467427181, 0.0, 287.53860848736053],
    [0.0, 717.6147860101706, 265.401578402327],
    [0.0, 0.0, 1.0],
  ]),
  dist_coeff: buildVector<number, 5>(
    -0.4868060470989732,
    0.11666111049150646,
    -0.002602028212347974,
    0.0019306561102483734,
    0.4520188231908469
  ),
  direction_vector: buildVector<number, 3>(0.0, 0.0, 0.0), // From rotation-vector in config
  position: buildVector<number, 3>(0.0, 0.0, 0.0), // From translation-vector in config
};

export default large640480;
