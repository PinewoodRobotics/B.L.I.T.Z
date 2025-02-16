import pyapriltags


def get_detector():
    return pyapriltags.Detector(families=str("tag36h11"), nthreads=2, quad_decimate=1)
