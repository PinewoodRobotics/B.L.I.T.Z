import { Matrix, Vector } from "../type-util/math-util";

export interface CameraParameters {
  camera_matrix: Matrix<number, 3, 3>;
  dist_coeff: Vector<number, 5>;
  port: number;

  direction_vector: Vector<number, 3>;
  position: Vector<number, 3>;

  max_fps: number;
  width: number;
  height: number;
  flags: number;
}
