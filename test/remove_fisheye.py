import cv2
import numpy as np

from common import profiler
from common.camera.transform import unfisheye_image
from common.config_class.profiler import ProfilerConfig
from test.test_config import PROFILER_CONFIG

camera_matrix = np.array(
    [
        [1457.5931734170763, 0.0, 997.1660947238562],
        [0.0, 1401.1036215895347, 539.0780233970917],
        [0.0, 0.0, 1.0],
    ]
)

dist_coeff = np.array(
    [
        -0.3699966980628528,
        0.1821265728482258,
        -0.000017146753545554133,
        0.001312177635207973,
        0.060869889777672416,
    ]
)


def main():
    cap = cv2.VideoCapture(0)
    profiler.init_profiler(ProfilerConfig(config=PROFILER_CONFIG))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = unfisheye_image(frame, camera_matrix, dist_coeff)

        cv2.imshow("frame", frame)
        cv2.waitKey(1)


if __name__ == "__main__":
    main()
