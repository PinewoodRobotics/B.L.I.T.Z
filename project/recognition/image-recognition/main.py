import argparse
import asyncio
from dataclasses import dataclass
import signal
import time

from generated.Image_pb2 import ImageMessage
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.common.camera.transform import from_proto_to_cv2
from project.common.config import Config
from util.bridge import ImageRecognition

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=str, default=None)

@dataclass
class QueueItem:
    image_message_data: ImageMessage
    timestamp: float

async def main():
    stop_event = asyncio.Event()
    args = parser.parse_args()
    config = Config.from_uncertainty_config(args.config)
    process_queue: asyncio.Queue[QueueItem] = asyncio.Queue()
    
    autobahn_server = Autobahn(Address(config.autobahn.host, config.autobahn.port))
    await autobahn_server.begin()
    
    image_recognition = ImageRecognition(config.image_recognition)
    await image_recognition.warmup()
    
    await autobahn_server.subscribe(
        config.image_recognition.detection.image_input_topic,
        lambda message: process_queue.put(QueueItem(ImageMessage.FromString(message), time.time() * 1000))
    )
    
    def signal_handler():
        print("Received stop signal, shutting down...")
        stop_event.set()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_running_loop().add_signal_handler(
            sig,
            signal_handler
        )
    
    while not stop_event.is_set():
        message = await process_queue.get()
        if time.time() * 1000 - message.timestamp > config.image_recognition.throwaway_time_ms:
            continue
        
        image = from_proto_to_cv2(message.image_message_data)
        inferences = image_recognition.predict(image, message.image_message_data.camera_name, message.image_message_data.image_id)
        
        await autobahn_server.publish(
            config.image_recognition.detection.image_output_topic,
            inferences.SerializeToString()
        )

if __name__ == "__main__":
    asyncio.run(main())