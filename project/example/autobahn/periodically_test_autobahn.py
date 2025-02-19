import asyncio
import time
from collections import deque
from statistics import mean

from project.autobahn.autobahn_python.autobahn import Autobahn
from project.autobahn.autobahn_python.util import Address

# Store last N measurements for moving average
WINDOW_SIZE = 10
latency_history = deque(maxlen=WINDOW_SIZE)


async def on_ping_received(payload: bytes):
    timestamp = float(payload.decode("utf-8"))
    current_time = time.time()
    latency = (current_time - timestamp) * 1000  # Convert to milliseconds
    latency_history.append(latency)

    avg_latency = mean(latency_history) if latency_history else 0
    # Clear the terminal and print updated stats
    print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
    print(f"Current latency: {latency:.2f}ms")
    print(
        f"Moving average (last {len(latency_history)} measurements): {avg_latency:.2f}ms"
    )


async def main():
    autobahn = Autobahn(Address("localhost", 8080))
    await autobahn.begin()
    await autobahn.subscribe("pong", on_ping_received)

    try:
        while True:
            # Send current timestamp as payload
            timestamp = str(time.time()).encode("utf-8")
            await autobahn.publish("pong", timestamp)
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Stopping ping service...")


if __name__ == "__main__":
    asyncio.run(main())
