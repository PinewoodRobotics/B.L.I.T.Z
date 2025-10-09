import pygame
import asyncio


class PygameWindow:
    def __init__(self, width=1200, height=800, title="Pygame Window"):
        pygame.init()
        self.width = width
        self.height = height
        self.title = title
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.objects = []  # List of (x, y) tuples for objects
        self.center_point = (
            self.width / 2,
            self.height / 2,
        )  # (x, y) for the center point
        self.bg_color = (30, 30, 30)  # Background color

    def update_objects(self, objects):
        """
        Update the list of objects to display.
        :param objects: List of (x, y) tuples representing object positions.
        """
        self.objects = objects

    def set_center_point(self, center):
        """
        Set the center point of the display.
        :param center: (x, y) tuple for the center point.
        """
        self.center_point = center

    def draw_objects(self):
        """
        Draw the objects on the screen.
        """
        for x, y in self.objects:
            pygame.draw.circle(
                self.screen,
                (0, 255, 0),
                (int(x + self.center_point[0]), int(y + self.center_point[1])),
                5,
            )  # Green circles

    def draw_center_point(self):
        """
        Draw the center point on the screen, if it is set.
        """
        if self.center_point:
            x, y = self.center_point
            pygame.draw.circle(
                self.screen, (255, 0, 0), (int(x), int(y)), 7
            )  # Red circle
            pygame.draw.line(
                self.screen, (255, 0, 0), (x - 10, y), (x + 10, y), 2
            )  # Crosshairs
            pygame.draw.line(self.screen, (255, 0, 0), (x, y - 10), (x, y + 10), 2)

    async def run(self):
        """
        Asynchronous main loop for the window.
        """
        while self.running:
            # Handle Pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            # Clear the screen
            self.screen.fill(self.bg_color)

            # Draw objects and center point
            self.draw_objects()
            self.draw_center_point()

            # Update the display
            pygame.display.flip()

            # Cap the frame rate (60 FPS)
            self.clock.tick(60)

            # Yield control to the event loop
            await asyncio.sleep(0)  # Allows other asyncio tasks to run

        pygame.quit()
