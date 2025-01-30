import numpy as np
import cv2
import pyapriltags
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def get_detector():
    return pyapriltags.Detector(
        families=str("tag36h11"),
        nthreads=2,
    )
