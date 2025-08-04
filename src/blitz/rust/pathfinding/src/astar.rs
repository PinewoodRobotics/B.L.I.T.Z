use nalgebra::Vector2;
use std::collections::HashMap;

use crate::grid::Grid2d;

use std::cmp::Ordering;
use std::collections::BinaryHeap;

#[derive(Eq, PartialEq)]
struct Node {
    pos: Vector2<usize>,
    f: usize,
    g: usize,
}

impl Ord for Node {
    fn cmp(&self, other: &Self) -> Ordering {
        other.f.cmp(&self.f).then_with(|| other.g.cmp(&self.g))
    }
}

impl PartialOrd for Node {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Grid2d {
    fn heuristic(a: Vector2<usize>, b: Vector2<usize>) -> usize {
        let dx = if a.x > b.x { a.x - b.x } else { b.x - a.x };
        let dy = if a.y > b.y { a.y - b.y } else { b.y - a.y };
        dx + dy
    }

    pub fn astar(&self, start: Vector2<usize>, goal: Vector2<usize>) -> Vec<Vector2<usize>> {
        if !self.in_bounds(start) || !self.in_bounds(goal) {
            return Vec::new();
        }
        if !self.is_passable(start) || !self.is_passable(goal) {
            return Vec::new();
        }
        let mut open_set = BinaryHeap::new();
        let mut came_from = HashMap::with_capacity(self.width * self.height);
        let mut g_score = HashMap::with_capacity(self.width * self.height);

        g_score.insert(start, 0);
        open_set.push(Node {
            pos: start,
            f: Self::heuristic(start, goal),
            g: 0,
        });

        while let Some(Node {
            pos: current,
            g: current_g,
            ..
        }) = open_set.pop()
        {
            if current == goal {
                let mut path = vec![current];
                let mut curr = current;
                while let Some(&prev) = came_from.get(&curr) {
                    path.push(prev);
                    curr = prev;
                }

                path.reverse();
                return path;
            }

            if let Some(&old_g) = g_score.get(&current) {
                if current_g > old_g {
                    continue;
                }
            }

            for neighbor in self.neighbors(current) {
                let tentative_g = current_g + 1;
                let neighbor_g = g_score.get(&neighbor).copied().unwrap_or(usize::MAX);
                if tentative_g < neighbor_g {
                    came_from.insert(neighbor, current);
                    g_score.insert(neighbor, tentative_g);
                    let f = tentative_g + Self::heuristic(neighbor, goal);
                    open_set.push(Node {
                        pos: neighbor,
                        f,
                        g: tentative_g,
                    });
                }
            }
        }
        Vec::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_grid(width: usize, height: usize, open: &[(usize, usize)]) -> Grid2d {
        let mut cells = vec![false; width * height];
        for &(x, y) in open {
            cells[y * width + x] = true;
        }
        Grid2d::new(width, height, &cells)
    }

    #[test]
    fn test_astar_simple_straight_line() {
        let width = 5;
        let height = 1;
        let open = (0..5).map(|x| (x, 0)).collect::<Vec<_>>();
        let grid = make_grid(width, height, &open);
        let start = Vector2::new(0, 0);
        let goal = Vector2::new(4, 0);
        let path = grid.astar(start, goal);
        assert_eq!(
            path,
            vec![
                Vector2::new(0, 0),
                Vector2::new(1, 0),
                Vector2::new(2, 0),
                Vector2::new(3, 0),
                Vector2::new(4, 0)
            ]
        );
    }

    #[test]
    fn test_astar_simple_vertical() {
        let width = 1;
        let height = 5;
        let open = (0..5).map(|y| (0, y)).collect::<Vec<_>>();
        let grid = make_grid(width, height, &open);
        let start = Vector2::new(0, 0);
        let goal = Vector2::new(0, 4);
        let path = grid.astar(start, goal);
        assert_eq!(
            path,
            vec![
                Vector2::new(0, 0),
                Vector2::new(0, 1),
                Vector2::new(0, 2),
                Vector2::new(0, 3),
                Vector2::new(0, 4)
            ]
        );
    }

    #[test]
    fn test_astar_with_obstacle() {
        let width = 3;
        let height = 3;
        let open = vec![
            (0, 0),
            (1, 0),
            (2, 0),
            (0, 1),
            (2, 1),
            (0, 2),
            (1, 2),
            (2, 2),
        ];
        let grid = make_grid(width, height, &open);
        let start = Vector2::new(0, 0);
        let goal = Vector2::new(2, 2);
        let path = grid.astar(start, goal);
        let expected = vec![
            Vector2::new(0, 0),
            Vector2::new(1, 0),
            Vector2::new(2, 0),
            Vector2::new(2, 1),
            Vector2::new(2, 2),
        ];
        assert_eq!(path, expected);
    }

    #[test]
    fn test_astar_no_path() {
        let width = 3;
        let height = 3;
        let open = vec![(0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)];
        let grid = make_grid(width, height, &open);
        let start = Vector2::new(0, 0);
        let goal = Vector2::new(1, 2);
        let path = grid.astar(start, goal);
        assert!(path.is_empty());
    }

    #[test]
    fn test_astar_start_is_goal() {
        let width = 3;
        let height = 3;
        let open = vec![
            (0, 0),
            (1, 0),
            (2, 0),
            (0, 1),
            (1, 1),
            (2, 1),
            (0, 2),
            (1, 2),
            (2, 2),
        ];
        let grid = make_grid(width, height, &open);
        let start = Vector2::new(1, 1);
        let goal = Vector2::new(1, 1);
        let path = grid.astar(start, goal);
        assert_eq!(path, vec![Vector2::new(1, 1)]);
    }

    #[test]
    fn test_astar_large_grid() {
        let width = 10;
        let height = 10;
        let open = (0..width)
            .flat_map(|x| (0..height).map(move |y| (x, y)))
            .collect::<Vec<_>>();
        let grid = make_grid(width, height, &open);
        let start = Vector2::new(0, 0);
        let goal = Vector2::new(9, 9);
        let path = grid.astar(start, goal);
        assert_eq!(path.first(), Some(&start));
        assert_eq!(path.last(), Some(&goal));
        assert_eq!(path.len(), 19);
    }

    #[test]
    fn test_astar_blocked_start() {
        let width = 3;
        let height = 3;
        let open = vec![
            (1, 0),
            (2, 0),
            (0, 1),
            (1, 1),
            (2, 1),
            (0, 2),
            (1, 2),
            (2, 2),
        ];
        let grid = make_grid(width, height, &open);
        let start = Vector2::new(0, 0);
        let goal = Vector2::new(2, 2);
        let path = grid.astar(start, goal);
        assert!(path.is_empty());
    }

    #[test]
    fn test_astar_blocked_goal() {
        let width = 3;
        let height = 3;
        let open = vec![
            (0, 0),
            (1, 0),
            (2, 0),
            (0, 1),
            (1, 1),
            (2, 1),
            (0, 2),
            (1, 2),
        ];
        let grid = make_grid(width, height, &open);
        let start = Vector2::new(0, 0);
        let goal = Vector2::new(2, 2);
        let path = grid.astar(start, goal);
        assert!(path.is_empty());
    }

    #[test]
    fn test_astar_diagonal_blocked() {
        let width = 3;
        let height = 3;
        let open = vec![
            (0, 0),
            (1, 0),
            (2, 0),
            (0, 1),
            (2, 1),
            (0, 2),
            (1, 2),
            (2, 2),
        ];
        let grid = make_grid(width, height, &open);
        let start = Vector2::new(0, 2);
        let goal = Vector2::new(2, 0);
        let path = grid.astar(start, goal);
        let expected = vec![
            Vector2::new(0, 2),
            Vector2::new(1, 2),
            Vector2::new(2, 2),
            Vector2::new(2, 1),
            Vector2::new(2, 0),
        ];
        assert_eq!(path, expected);
    }
}
