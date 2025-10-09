import asyncio
import os
import time
from collections import deque
from statistics import mean
import pygame

from autobahn_client.client import Autobahn, Address

WINDOW_SIZE = 100
latency_history = deque(maxlen=WINDOW_SIZE)

MAX_POINTS = 100
timestamps = deque(maxlen=MAX_POINTS)
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
        y_pos = SCREEN_HEIGHT - PADDING - (i * (SCREEN_HEIGHT - 2 * PADDING) / 6)
        pygame.draw.line(screen, (0, 0, 0), (PADDING - 5, y_pos), (PADDING + 5, y_pos))
        label = font.render(f"{i}ms", True, (0, 0, 0))
        screen.blit(label, (PADDING - 40, y_pos - 10))

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
            y = (
                SCREEN_HEIGHT
                - PADDING
                - (SCREEN_HEIGHT - 2 * PADDING) * (latency / MAX_LATENCY)
            )
            pygame.draw.circle(screen, (173, 216, 230), (int(x), int(y)), POINT_RADIUS)

        avg_points = []
        for i, avg_latency in enumerate(avg_latencies):
            x = PADDING + (SCREEN_WIDTH - 2 * PADDING) * (i / MAX_POINTS)
            y = (
                SCREEN_HEIGHT
                - PADDING
                - (SCREEN_HEIGHT - 2 * PADDING) * (avg_latency / MAX_LATENCY)
            )
            avg_points.append((int(x), int(y)))

        if len(avg_points) > 1:
            pygame.draw.lines(screen, (255, 0, 0), False, avg_points, 2)

    pygame.display.flip()


async def on_ping_received(payload: bytes):
    try:
        timestamp = float(payload[:payload.index(b' ')].decode("utf-8")) / 1000
        current_time = time.time()
        latency = (current_time - timestamp) * 1000

        latency_history.append(latency)
        timestamps.append(current_time)
        latencies.append(latency)
        avg_latency = mean(latency_history)
        avg_latencies.append(avg_latency)

        print(f"Current latency: {latency:.2f}ms")
        print(f"Moving average (last {len(latency_history)} measurements): {avg_latency:.2f}ms")
    except (ValueError, AttributeError) as e:
        print(f"Error processing ping payload: {e}")

def generate_random_payload(num_bytes: int):
    return os.urandom(num_bytes)

async def main():
    autobahn = Autobahn(Address("localhost", 8080))
    await autobahn.begin()
    await autobahn.subscribe("pong1", on_ping_received)

    last_render_time = 0
    render_interval = 0.3
    send_interval = 0.01
    
    time_to_run_seconds = 100
    time_to_run = time.time() + time_to_run_seconds

    try:
        while True:
            payload = generate_random_payload(480_000)
            current_time = time.time()
            print(f"Sending ping at {current_time}")

            timestamp = str(current_time * 1000).encode("utf-8") + b' ' + payload
            await autobahn.publish("pong1", timestamp)

            if current_time - last_render_time >= render_interval:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise KeyboardInterrupt

                draw_visualization()
                last_render_time = current_time

            if current_time > time_to_run:
                break

            await asyncio.sleep(send_interval)

    except KeyboardInterrupt:
        print("Stopping ping service...")
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
