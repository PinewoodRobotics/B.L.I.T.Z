use common_core::{proto::pathfind, thrift::common::MapData};
use nalgebra::Vector2;

#[derive(Clone)]
pub enum Cell {
    Passable,
    Obstacle,
    Temporary(Box<Cell>),
}

impl Cell {
    pub fn serialize(&self) -> pathfind::Cell {
        match self {
            Cell::Passable => pathfind::Cell::Passable,
            Cell::Obstacle => pathfind::Cell::Obstacle,
            Cell::Temporary(_) => pathfind::Cell::Temporary,
        }
    }
}

pub struct Grid2d {
    pub width: usize,
    pub height: usize,
    pub cells: Vec<Cell>,
}

impl Grid2d {
    pub fn new(width: usize, height: usize, map_data: &[bool]) -> Self {
        Self {
            width,
            height,
            cells: map_data
                .iter()
                .map(|&x| if x { Cell::Passable } else { Cell::Obstacle })
                .collect(),
        }
    }

    pub fn from_map_data(map_data: MapData) -> Self {
        let width = map_data.map_size_x as usize;
        let height = map_data.map_size_y as usize;
        Self {
            width,
            height,
            cells: map_data
                .map_data
                .iter()
                .map(|&x| if x { Cell::Passable } else { Cell::Obstacle })
                .collect(),
        }
    }

    pub fn get_cell_location(&self, pos: Vector2<usize>) -> usize {
        pos.y * self.width + pos.x
    }

    pub fn in_bounds(&self, pos: Vector2<usize>) -> bool {
        pos.x < self.width && pos.y < self.height
    }

    pub fn is_passable(&self, pos: Vector2<usize>) -> bool {
        match self.cells[pos.y * self.width + pos.x] {
            Cell::Passable => true,
            Cell::Obstacle => false,
            Cell::Temporary(_) => false,
        }
    }

    pub fn neighbors(&self, pos: Vector2<usize>) -> impl Iterator<Item = Vector2<usize>> + '_ {
        let deltas = [(1isize, 0isize), (0, 1), (-1, 0), (0, -1)];
        deltas.into_iter().filter_map(move |(dx, dy)| {
            let nx = pos.x as isize + dx;
            let ny = pos.y as isize + dy;
            if nx >= 0 && ny >= 0 {
                let npos = Vector2::new(nx as usize, ny as usize);
                if self.in_bounds(npos) && self.is_passable(npos) {
                    Some(npos)
                } else {
                    None
                }
            } else {
                None
            }
        })
    }

    pub fn set_temporary(&mut self, pos: Vector2<usize>) {
        let idx = self.get_cell_location(pos);
        let cell = std::mem::replace(&mut self.cells[idx], Cell::Passable);
        self.cells[idx] = Cell::Temporary(Box::new(cell));
    }

    pub fn clear_temporary_at(&mut self, pos: Vector2<usize>) {
        let idx = self.get_cell_location(pos);
        if let Cell::Temporary(inner) = std::mem::replace(&mut self.cells[idx], Cell::Passable) {
            self.cells[idx] = *inner;
        }
    }

    pub fn add_temporary(&mut self, pos: Vec<Vector2<usize>>) {
        for p in pos {
            self.set_temporary(p);
        }
    }

    pub fn clear_temporary(&mut self, pos: Vec<Vector2<usize>>) {
        for p in pos {
            self.clear_temporary_at(p);
        }
    }

    pub fn clear_temporary_all(&mut self) {
        for i in 0..self.cells.len() {
            if let Cell::Temporary(_) = self.cells[i] {
                self.cells[i] = Cell::Passable;
            }
        }
    }

    pub fn serialize(&self) -> pathfind::Grid2d {
        pathfind::Grid2d {
            width: self.width as i32,
            height: self.height as i32,
            grid: self.cells.iter().map(|c| c.serialize() as i32).collect(),
        }
    }
}
