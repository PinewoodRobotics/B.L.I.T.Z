use nalgebra::{
    Matrix2, Matrix3, Matrix4, Matrix5, Matrix6, Vector2, Vector3, Vector4, Vector5, Vector6,
};
use thrift::OrderedFloat;

use crate::thrift::common::{GenericMatrix, GenericVector};

macro_rules! impl_vector_conversions {
    ($thrift_type:ty, $nalgebra_type:ty, $ftype:ty) => {
        impl From<$thrift_type> for $nalgebra_type {
            fn from(vector: $thrift_type) -> Self {
                let values: Vec<$ftype> = vector
                    .values
                    .iter()
                    .map(|v| (*v.clone() as f64) as $ftype)
                    .collect();
                <$nalgebra_type>::from_row_slice(&values)
            }
        }

        impl From<$nalgebra_type> for $thrift_type {
            fn from(vector: $nalgebra_type) -> Self {
                let values: Vec<_> = vector
                    .into_iter()
                    .map(|x| (x.clone() as f64).into())
                    .collect();
                let size = values.len() as i32;
                Self { values, size }
            }
        }
    };
}

macro_rules! impl_matrix_conversions {
    ($thrift_type:ty, $nalgebra_type:ty, $ftype:ty) => {
        impl From<$thrift_type> for $nalgebra_type {
            fn from(matrix: $thrift_type) -> Self {
                let mat_flat: Vec<Vec<OrderedFloat<f64>>> = matrix.values;
                let mat_flat: Vec<$ftype> = mat_flat
                    .iter()
                    .flatten()
                    .cloned()
                    .map(|x| (*x as f64) as $ftype)
                    .collect();

                <$nalgebra_type>::from_row_slice(&mat_flat)
            }
        }

        impl From<$nalgebra_type> for $thrift_type {
            fn from(matrix: $nalgebra_type) -> Self {
                let values: Vec<Vec<OrderedFloat<f64>>> = matrix
                    .row_iter()
                    .map(|x| x.iter().map(|y| (*y as f64).into()).collect())
                    .collect();
                let rows = values.len() as i32;
                let cols = if rows > 0 { values[0].len() as i32 } else { 0 };

                Self { values, rows, cols }
            }
        }
    };
}

// Vector conversions
impl_vector_conversions!(GenericVector, Vector2<f64>, f64);
impl_vector_conversions!(GenericVector, Vector2<f32>, f32);

impl_vector_conversions!(GenericVector, Vector3<f64>, f64);
impl_vector_conversions!(GenericVector, Vector3<f32>, f32);

impl_vector_conversions!(GenericVector, Vector4<f64>, f64);
impl_vector_conversions!(GenericVector, Vector4<f32>, f32);

impl_vector_conversions!(GenericVector, Vector5<f64>, f64);
impl_vector_conversions!(GenericVector, Vector5<f32>, f32);

// Matrix conversions
impl_matrix_conversions!(GenericMatrix, Matrix2<f64>, f64);
impl_matrix_conversions!(GenericMatrix, Matrix2<f32>, f32);

impl_matrix_conversions!(GenericMatrix, Matrix3<f64>, f64);
impl_matrix_conversions!(GenericMatrix, Matrix3<f32>, f32);

impl_matrix_conversions!(GenericMatrix, Matrix4<f64>, f64);
impl_matrix_conversions!(GenericMatrix, Matrix4<f32>, f32);

#[cfg(test)]
mod tests {
    use super::*;

    fn get_thrift_matrix() -> GenericMatrix {
        GenericMatrix {
            values: vec![
                vec![OrderedFloat(1.0), OrderedFloat(2.0), OrderedFloat(3.0)],
                vec![OrderedFloat(4.0), OrderedFloat(5.0), OrderedFloat(6.0)],
                vec![OrderedFloat(7.0), OrderedFloat(8.0), OrderedFloat(9.0)],
            ],
            rows: 3,
            cols: 3,
        }
    }

    fn get_nalgebra_matrix() -> Matrix3<f64> {
        Matrix3::new(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
    }

    fn get_thrift_vector() -> GenericVector {
        GenericVector {
            values: vec![OrderedFloat(1.0), OrderedFloat(2.0), OrderedFloat(3.0)],
            size: 3,
        }
    }

    fn get_nalgebra_vector() -> Vector3<f64> {
        Vector3::new(1.0, 2.0, 3.0)
    }

    #[test]
    fn test_thrift_to_nalgebra() {
        let thrift_matrix = get_thrift_matrix();
        let nalgebra_matrix = Matrix3::from(thrift_matrix);
        assert_eq!(
            nalgebra_matrix,
            Matrix3::new(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
        );
    }

    #[test]
    fn test_nalgebra_to_thrift() {
        let nalgebra_matrix = get_nalgebra_matrix();
        let thrift_matrix = GenericMatrix::from(nalgebra_matrix);
        assert_eq!(thrift_matrix, get_thrift_matrix());
    }

    #[test]
    fn test_thrift_to_nalgebra_vector() {
        let thrift_vector = get_thrift_vector();
        let nalgebra_vector = Vector3::from(thrift_vector);
        assert_eq!(nalgebra_vector, Vector3::new(1.0, 2.0, 3.0));
    }

    #[test]
    fn test_nalgebra_to_thrift_vector() {
        let nalgebra_vector = get_nalgebra_vector();
        let thrift_vector = GenericVector::from(nalgebra_vector);
        assert_eq!(thrift_vector, get_thrift_vector());
    }
}
