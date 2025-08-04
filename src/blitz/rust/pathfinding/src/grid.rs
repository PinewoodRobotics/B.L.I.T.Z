use common_core::thrift::common::MapData;

pub struct Grid {
    pub width: usize,
    pub height: usize,
    pub cells: Vec<bool>,
}

impl Grid {
    pub fn new(width: usize, height: usize, map_data: &[bool]) -> Self {
        Self {
            width,
            height,
            cells: map_data.to_vec(),
        }
    }

    pub fn from_map_data(map_data: MapData) -> Self {
        let width = map_data.map_size_x as usize;
        let height = map_data.map_size_y as usize;
        Self {
            width,
            height,
            cells: map_data.map_data.iter().map(|&x| x).collect(),
        }
    }
}
