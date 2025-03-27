# Using vendor:product ID
from project.recognition.position.april.src.util import find_camera_port


port = find_camera_port(vendor_product="32e4:0234", serial_number="01.00.00")

if port is not None:
    print(f"Camera found at port {port}")
else:
    print("Camera not found.")
