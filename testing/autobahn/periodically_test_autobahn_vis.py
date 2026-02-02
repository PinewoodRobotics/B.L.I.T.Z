import asyncio
import time
from collections import deque
from statistics import mean
import pygame

from autobahn_client.client import Autobahn, Address
from generated.PiStatus_pb2 import Ping, Pong

WINDOW_SIZE = 100
latency_history = deque(maxlen=WINDOW_SIZE)

MAX_POINTS = 100
latencies = deque(maxlen=MAX_POINTS)
avg_latencies = deque(maxlen=MAX_POINTS)

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400
PADDING = 50
POINT_RADIUS = 2
MAX_LATENCY = 10

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Real-time Latency Monitor")


def draw_visualization():
    screen.fill((255, 255, 255))
    pygame.draw.line(
        screen,
        (0, 0, 0),
        (PADDING, SCREEN_HEIGHT - PADDING),
        (SCREEN_WIDTH - PADDING, SCREEN_HEIGHT - PADDING),
    )
    pygame.draw.line(
        screen, (0, 0, 0), (PADDING, PADDING), (PADDING, SCREEN_HEIGHT - PADDING)
    )
    font = pygame.font.Font(None, 24)
    for i in range(7):
        ms_val = int(i * (MAX_LATENCY / 6))
        y_pos = SCREEN_HEIGHT - PADDING - (i * (SCREEN_HEIGHT - 2 * PADDING) / 6)
        pygame.draw.line(screen, (0, 0, 0), (PADDING - 5, y_pos), (PADDING + 5, y_pos))
        label = font.render(f"{ms_val}ms", True, (0, 0, 0))
        screen.blit(label, (PADDING - 50, y_pos - 10))

    for i in range(0, MAX_POINTS + 1, 20):
        x_pos = PADDING + (SCREEN_WIDTH - 2 * PADDING) * (i / MAX_POINTS)
        pygame.draw.line(
            screen,
            (0, 0, 0),
            (x_pos, SCREEN_HEIGHT - PADDING + 5),
            (x_pos, SCREEN_HEIGHT - PADDING - 5),
        )
        label = font.render(str(i), True, (0, 0, 0))
        screen.blit(label, (x_pos - 10, SCREEN_HEIGHT - PADDING + 10))

    if latencies and avg_latencies:
        for i, latency in enumerate(latencies):
            x = PADDING + (SCREEN_WIDTH - 2 * PADDING) * (i / MAX_POINTS)
            ly = max(min(latency, MAX_LATENCY), 0)
            y = (
                SCREEN_HEIGHT
                - PADDING
                - (SCREEN_HEIGHT - 2 * PADDING) * (ly / MAX_LATENCY)
            )
            pygame.draw.circle(screen, (173, 216, 230), (int(x), int(y)), POINT_RADIUS)

        avg_points = []
        for i, avg_latency in enumerate(avg_latencies):
            x = PADDING + (SCREEN_WIDTH - 2 * PADDING) * (i / MAX_POINTS)
            ay = max(min(avg_latency, MAX_LATENCY), 0)
            y = (
                SCREEN_HEIGHT
                - PADDING
                - (SCREEN_HEIGHT - 2 * PADDING) * (ay / MAX_LATENCY)
            )
            avg_points.append((int(x), int(y)))

        if len(avg_points) > 1:
            pygame.draw.lines(screen, (255, 0, 0), False, avg_points, 2)

    pygame.display.flip()


async def on_pong_received(payload: bytes):
    pong = Pong.FromString(payload)
    sent_timestamp = pong.timestamp_ms_original / 1000.0
    receive_local_time = time.time()
    latency = (receive_local_time - sent_timestamp) * 1000
    latency_history.append(latency)
    latencies.append(latency)
    avg_latency = mean(latency_history) if latency_history else 0
    avg_latencies.append(avg_latency)
    print(f"Current latency: {latency:.2f}ms")
    print(
        f"Moving average (last {len(latency_history)} measurements): {avg_latency:.2f}ms"
    )


async def main():
    autobahn = Autobahn(Address("nathanhale.local", 8080))
    await autobahn.begin()
    await autobahn.subscribe("pi-pong", on_pong_received)

    last_render_time = 0
    render_interval = 0.2

    try:
        while True:
            now_ms = int(time.time() * 1000)
            ping = Ping(timestamp=now_ms)
            await autobahn.publish("pi-ping", ping.SerializeToString())

            current_time = time.time()
            if current_time - last_render_time >= render_interval:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise KeyboardInterrupt
                draw_visualization()
                last_render_time = current_time

            await asyncio.sleep(0.005)
    except KeyboardInterrupt:
        print("Stopping ping service...")
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
