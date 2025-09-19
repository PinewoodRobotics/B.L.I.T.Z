import { MatrixUtil, VectorUtil } from "../../util/math";

export const comp_lab = {
  30: {
    position: VectorUtil.fromArray([0, 0, 0]),
    rotation: MatrixUtil.buildMatrix([
      [0, 0, 1],
      [0, 1, 0],
      [-1, 0, 0],
    ]),
  },
};
