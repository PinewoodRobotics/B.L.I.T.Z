use nalgebra::{Matrix3, Matrix4, Matrix5, Matrix6, Vector2, Vector3, Vector4, Vector5, Vector6};
use thrift::OrderedFloat;

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

impl_vector_conversions!(crate::thrift::common::GenericVector, Vector2<f64>, f64);
impl_vector_conversions!(crate::thrift::common::GenericVector, Vector2<f32>, f32);

impl_vector_conversions!(crate::thrift::common::GenericVector, Vector3<f64>, f64);

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

impl_matrix_conversions!(crate::thrift::common::GenericMatrix, Matrix3<f64>, f64);
impl_matrix_conversions!(crate::thrift::common::GenericMatrix, Matrix3<f32>, f32);

impl_matrix_conversions!(crate::thrift::common::GenericMatrix, Matrix4<f64>, f64);
