import glob
import os
import platform
import re
import subprocess
import numpy as np
import pyapriltags

from generated.AprilTag_pb2 import Tag


def to_float_list(arr: np.ndarray) -> list:
    return list(arr.flatten()) if arr is not None else []


def to_float(val) -> float:
    if isinstance(val, np.ndarray):
        return float(val.item())
    return float(val) if val is not None else 0.0


def from_detection_to_proto(detection: pyapriltags.Detection) -> Tag:
    if detection.pose_t is None:
        raise ValueError("Detection has no pose data")

    distance_to_camera = float(np.linalg.norm(detection.pose_t))

    x, y, z = detection.pose_t[0], detection.pose_t[1], detection.pose_t[2]

    angle_relative_to_camera_yaw = float(np.arctan2(x, z))
    angle_relative_to_camera_pitch = float(np.arctan2(y, z))

    position_x_relative = float(x)
    position_y_relative = float(y)
    position_z_relative = float(z)

    return Tag(
        tag_family=str(detection.tag_family),
        tag_id=detection.tag_id,
        hamming=detection.hamming,
        decision_margin=detection.decision_margin,
        homography=to_float_list(detection.homography),
        center=to_float_list(detection.center),
        corners=to_float_list(detection.corners),
        pose_R=to_float_list(detection.pose_R) if detection.pose_R is not None else [],
        pose_t=to_float_list(detection.pose_t),
        pose_err=detection.pose_err,
        tag_size=detection.tag_size,
        distance_to_camera=distance_to_camera,
        angle_relative_to_camera_yaw=angle_relative_to_camera_yaw,
        angle_relative_to_camera_pitch=angle_relative_to_camera_pitch,
        position_x_relative=position_x_relative,
        position_y_relative=position_y_relative,
        position_z_relative=position_z_relative,
    )


def find_camera_port(
    *, serial_number: str | None = None, vendor_product: str | None = None
) -> int | None:
    """
    Cross-platform function to find camera port number (OpenCV index) based on serial number
    or vendor:product ID. Supports Linux and macOS.

    Args:
        serial_number (str): Camera serial number (e.g., "01.00.00")
        vendor_product (str): Vendor:Product ID in hex (e.g., "046d:0825" or "32e4:0234")

    Returns:
        int or None: Camera port number (e.g., 0 for /dev/video0), or None if not found.
    """
    system = platform.system()

    if system == "Linux":
        try:
            if vendor_product:
                vendor, product = vendor_product.split(":")
                video_devices = glob.glob("/sys/class/video4linux/video*")
                for video_path in video_devices:
                    device_link = os.path.join(video_path, "device")
                    sysfs_path = os.path.realpath(device_link)
                    id_vendor_path = os.path.join(sysfs_path, "idVendor")
                    id_product_path = os.path.join(sysfs_path, "idProduct")
                    serial_path = os.path.join(sysfs_path, "serial")

                    vid = pid = serial = None
                    if os.path.exists(id_vendor_path):
                        with open(id_vendor_path, "r") as f:
                            vid = f.read().strip()
                    if os.path.exists(id_product_path):
                        with open(id_product_path, "r") as f:
                            pid = f.read().strip()
                    if os.path.exists(serial_path):
                        with open(serial_path, "r") as f:
                            serial = f.read().strip()

                    if (
                        vendor_product
                        and vid is not None
                        and pid is not None
                        and vid.lower() == vendor.lower()
                        and pid.lower() == product.lower()
                    ) or (
                        serial_number
                        and serial
                        and serial.strip() == serial_number.strip()
                    ):
                        video_device = os.path.basename(video_path)
                        match = re.search(r"(\d+)", video_device)
                        if match:
                            return int(match.group(1))
        except Exception as e:
            print("Linux camera detection error:", e)
            return None

    elif system == "Darwin":  # macOS
        try:
            # List available video devices with ffmpeg
            result = subprocess.run(
                ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                stderr=subprocess.PIPE,
                text=True,
            )
            output = result.stderr
            matches = re.findall(r"\[\d+\] (.+)", output)
            if not matches:
                print("No video devices found.")
                return None

            # Get USB info from system_profiler
            usb_info = subprocess.check_output(
                ["system_profiler", "SPUSBDataType"], text=True
            )

            for i, name in enumerate(matches):
                if serial_number and serial_number in usb_info and name in usb_info:
                    return i
                elif vendor_product:
                    vendor, product = vendor_product.lower().split(":")
                    vendor_hex = f"0x{vendor.lower()}"
                    product_hex = f"0x{product.lower()}"
                    if (
                        vendor_hex in usb_info
                        and product_hex in usb_info
                        and name in usb_info
                    ):
                        return i
        except Exception as e:
            print("macOS camera detection error:", e)
            return None

    else:
        print("Unsupported platform:", system)
        return None
