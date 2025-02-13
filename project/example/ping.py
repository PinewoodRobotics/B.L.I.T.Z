import asyncio
import time

from project.autobahn.autobahn_python.autobahn import Autobahn


async def on_ping_received(payload: bytes):
    timestamp = float(payload.decode("utf-8"))
    current_time = time.time()
    latency = (current_time - timestamp) * 1000  # Convert to milliseconds
    print(f"Received ping! Latency: {latency:.2f}ms")


async def main():
    # Create Autobahn client
    client = Autobahn("localhost", 8080)  # Adjust host/port as needed

    # Start the client
    await client.begin()
    await client.subscribe("pong", on_ping_received)

    # Periodically send pings
    try:
        while True:
            # Send current timestamp as payload
            timestamp = str(time.time()).encode("utf-8")
            await client.publish("pong", timestamp)
            await asyncio.sleep(1)  # Send ping every second
    except KeyboardInterrupt:
        print("Stopping ping service...")


if __name__ == "__main__":
    asyncio.run(main())
