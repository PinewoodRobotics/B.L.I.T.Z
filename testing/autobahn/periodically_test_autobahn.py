import asyncio
import time
from collections import deque
from statistics import mean
from autobahn_client.client import Autobahn, Address

WINDOW_SIZE = 10
latency_history = deque(maxlen=WINDOW_SIZE)

from generated.PiStatus_pb2 import Ping, Pong


async def on_pong_received(payload: bytes):
    pong = Pong.FromString(payload)
    sent_timestamp = pong.timestamp_ms_original / 1000.0
    receive_local_time = time.time()
    latency = (receive_local_time - sent_timestamp) * 1000
    latency_history.append(latency)

    avg_latency = mean(latency_history) if latency_history else 0
    print("\033[2J\033[H", end="")
    print(f"Current latency: {latency:.2f}ms")
    print(
        f"Moving average (last {len(latency_history)} measurements): {avg_latency:.2f}ms"
    )


async def main():
    autobahn = Autobahn(Address("nathanhale.local", 8080))
    await autobahn.begin()

    await autobahn.subscribe("pi-pong", on_pong_received)

    try:
        while True:
            now_ms = int(time.time() * 1000)
            ping = Ping(timestamp=now_ms)
            await autobahn.publish("pi-ping", ping.SerializeToString())
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping ping service...")


if __name__ == "__main__":
    asyncio.run(main())
