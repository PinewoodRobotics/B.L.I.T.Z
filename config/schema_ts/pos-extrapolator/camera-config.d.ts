import { type Vector } from "../type-util/math-util";

export interface CameraConfig {
  camera_robot_position: Vector<number, 3>;
  camera_robot_direction: Vector<number, 3>;
}
