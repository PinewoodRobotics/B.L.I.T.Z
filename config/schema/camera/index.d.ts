import { Matrix, Vector } from "../type-util/math-util";

export interface CameraParameters {
  pi_to_run_on: string;

  name: string;

  camera_matrix: Matrix<number, 3, 3>;
  dist_coeff: Vector<number, 5>;
  camera_path: string;

  max_fps: number;
  width: number;
  height: number;
  flags: number;
}
