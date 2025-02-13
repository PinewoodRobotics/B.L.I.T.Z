import asyncio
import time

from project.autobahn.autobahn_python.autobahn import Autobahn


async def pong_callback(payload: bytes):
    # Convert payload to string and print it
    message = payload.decode("utf-8")
    print(f"Received pong message: {(time.time() - float(message)) * 1000}")


async def main():
    # Create Autobahn instance
    autobahn = Autobahn("localhost", 8080)  # Adjust host and port as needed

    # Start the connection
    await autobahn.begin()

    # Subscribe to "pong" topic
    await autobahn.subscribe("pong", pong_callback)

    print("Subscribed to 'pong' topic. Listening for messages...")

    # Keep the script running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
