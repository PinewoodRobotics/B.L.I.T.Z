import pygame
import time

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
GRID_SIZE = 40
ROWS, COLS = HEIGHT // GRID_SIZE, WIDTH // GRID_SIZE

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GRAY = (200, 200, 200)

# Screen setup
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pathfinding Visualization: IDA* and Fringe Search")

# Clock for controlling animation speed
clock = pygame.time.Clock()


# Node class for grid representation
class Node:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.x = col * GRID_SIZE
        self.y = row * GRID_SIZE
        self.neighbors = []
        self.color = WHITE
        self.g_cost = float("inf")  # Cost to reach this node
        self.f_cost = float("inf")  # f = g + h
        self.parent = None

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x, self.y, GRID_SIZE, GRID_SIZE))
        pygame.draw.rect(screen, GRAY, (self.x, self.y, GRID_SIZE, GRID_SIZE), 1)

    def update_neighbors(self, grid):
        self.neighbors = []
        if self.row > 0 and grid[self.row - 1][self.col].color != BLACK:  # Up
            self.neighbors.append(grid[self.row - 1][self.col])
        if self.row < ROWS - 1 and grid[self.row + 1][self.col].color != BLACK:  # Down
            self.neighbors.append(grid[self.row + 1][self.col])
        if self.col > 0 and grid[self.row][self.col - 1].color != BLACK:  # Left
            self.neighbors.append(grid[self.row][self.col - 1])
        if self.col < COLS - 1 and grid[self.row][self.col + 1].color != BLACK:  # Right
            self.neighbors.append(grid[self.row][self.col + 1])


# Heuristic function (Manhattan distance)
def heuristic(node1, node2):
    return abs(node1.row - node2.row) + abs(node1.col - node2.col)


# Draw grid on screen
def draw_grid(grid):
    for row in grid:
        for node in row:
            node.draw(screen)
    pygame.display.update()


# Reconstruct and draw the path
def reconstruct_path(node):
    while node.parent:
        node.color = BLUE
        node = node.parent
        draw_grid(grid)
        time.sleep(0.1)


# IDA* algorithm
def ida_star(start, end):
    def search(path, g, threshold):
        current = path[-1]
        f = g + heuristic(current, end)
        if f > threshold:
            return f
        if current == end:
            return True
        minimum = float("inf")
        for neighbor in current.neighbors:
            if neighbor not in path:
                path.append(neighbor)
                temp = search(path, g + 1, threshold)
                if temp is True:
                    return True
                if temp < minimum:
                    minimum = temp
                path.pop()
        return minimum

    threshold = heuristic(start, end)
    path = [start]
    while True:
        temp = search(path, 0, threshold)
        if temp is True:
            return True
        if temp == float("inf"):
            return False
        threshold = temp


# Fringe Search algorithm
def fringe_search(start, end):
    open_list = [start]
    open_set = set(open_list)

    while open_list:
        current = open_list.pop(0)
        open_set.remove(current)

        if current == end:
            reconstruct_path(end)
            return True

        for neighbor in current.neighbors:
            if neighbor not in open_set and neighbor.color != BLACK:
                neighbor.parent = current
                open_list.append(neighbor)
                open_set.add(neighbor)

        current.color = GREEN
        draw_grid(grid)
        time.sleep(0.01)

    return False


# Create grid
grid = [[Node(row, col) for col in range(COLS)] for row in range(ROWS)]


# Main function
def main():
    global grid

    start = None
    end = None
    running = True

    while running:
        screen.fill(WHITE)
        draw_grid(grid)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if pygame.mouse.get_pressed()[0]:  # Left click
                pos = pygame.mouse.get_pos()
                row, col = pos[1] // GRID_SIZE, pos[0] // GRID_SIZE
                node = grid[row][col]
                if not start and node != end:
                    start = node
                    start.color = RED
                elif not end and node != start:
                    end = node
                    end.color = BLUE
                elif node != start and node != end:
                    node.color = BLACK

            elif pygame.mouse.get_pressed()[2]:  # Right click
                pos = pygame.mouse.get_pos()
                row, col = pos[1] // GRID_SIZE, pos[0] // GRID_SIZE
                node = grid[row][col]
                node.color = WHITE
                if node == start:
                    start = None
                elif node == end:
                    end = None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and start and end:
                    for row in grid:
                        for node in row:
                            node.update_neighbors(grid)

                    ida_star(start, end)
                    fringe_search(start, end)

                if event.key == pygame.K_c:
                    start = None
                    end = None
                    grid = [
                        [Node(row, col) for col in range(COLS)] for row in range(ROWS)
                    ]

        pygame.display.update()
    pygame.quit()


if __name__ == "__main__":
    main()
