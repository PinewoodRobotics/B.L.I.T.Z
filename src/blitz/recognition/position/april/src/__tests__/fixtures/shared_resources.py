import pytest
import numpy as np
import pyapriltags


@pytest.fixture(scope="session")
def get_detector():
    return pyapriltags.Detector(
        families="tag36h11",
        nthreads=1,
        quad_decimate=1.0,
        quad_sigma=0.0,
    )


@pytest.fixture(scope="session")
def camera_1_matrix():
    return np.array(
        [
            [450, 0, 400],
            [0, 450, 300],
            [0, 0, 1],
        ]
    )


@pytest.fixture(scope="session")
def camera_1_dist_coeff():
    return np.array(
        [
            0.02421893240091871,
            -0.019483745628435203,
            -0.0002353973963860865,
            0.0010526889774734997,
            -0.032565426732841275,
        ]
    )
