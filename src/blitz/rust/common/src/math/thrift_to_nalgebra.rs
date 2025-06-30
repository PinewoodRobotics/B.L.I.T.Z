use nalgebra::{Matrix3, Matrix4, Matrix5, Matrix6, Vector2, Vector3, Vector4, Vector5, Vector6};

use crate::thrift::common::{
    Matrix3x3, Matrix4x4, Matrix5x5, Matrix6x6, Vector2D, Vector3D, Vector4D, Vector5D, Vector6D,
};

macro_rules! impl_vector_conversions {
    ($thrift_type:ty, $nalgebra_type:ty, $($field:ident => $accessor:ident),*) => {
        impl From<$thrift_type> for $nalgebra_type {
            fn from(vector: $thrift_type) -> Self {
                <$nalgebra_type>::new($(vector.$field.into()),*)
            }
        }

        impl From<$nalgebra_type> for $thrift_type {
            fn from(vector: $nalgebra_type) -> Self {
                Self {
                    $($field: vector.$accessor.into()),*
                }
            }
        }
    };
}

impl_vector_conversions!(Vector2D, Vector2<f64>, k1 => x, k2 => y);
impl_vector_conversions!(Vector3D, Vector3<f64>, k1 => x, k2 => y, k3 => z);
impl_vector_conversions!(Vector4D, Vector4<f64>, k1 => x, k2 => y, k3 => z, k4 => w);
impl_vector_conversions!(Vector5D, Vector5<f64>, k1 => x, k2 => y, k3 => z, k4 => w, k5 => a);
impl_vector_conversions!(Vector6D, Vector6<f64>, k1 => x, k2 => y, k3 => z, k4 => w, k5 => a, k6 => b);

macro_rules! impl_matrix_conversions {
    ($thrift_type:ty, $nalgebra_type:ty, $($row_field:ident => $pos_field:ident),*) => {
        impl From<$thrift_type> for $nalgebra_type {
            fn from(matrix: $thrift_type) -> Self {
                <$nalgebra_type>::new($(matrix.$row_field.$pos_field.into()),*)
            }
        }
    };
}

impl_matrix_conversions!(Matrix3x3, Matrix3<f64>, r1 => k1, r1 => k2, r1 => k3, r2 => k1, r2 => k2, r2 => k3, r3 => k1, r3 => k2, r3 => k3);
impl_matrix_conversions!(Matrix4x4, Matrix4<f64>, r1 => k1, r1 => k2, r1 => k3, r1 => k4, r2 => k1, r2 => k2, r2 => k3, r2 => k4, r3 => k1, r3 => k2, r3 => k3, r3 => k4, r4 => k1, r4 => k2, r4 => k3, r4 => k4);
impl_matrix_conversions!(Matrix5x5, Matrix5<f64>, r1 => k1, r1 => k2, r1 => k3, r1 => k4, r1 => k5, r2 => k1, r2 => k2, r2 => k3, r2 => k4, r2 => k5, r3 => k1, r3 => k2, r3 => k3, r3 => k4, r3 => k5, r4 => k1, r4 => k2, r4 => k3, r4 => k4, r4 => k5, r5 => k1, r5 => k2, r5 => k3, r5 => k4, r5 => k5);
impl_matrix_conversions!(Matrix6x6, Matrix6<f64>, r1 => k1, r1 => k2, r1 => k3, r1 => k4, r1 => k5, r1 => k6, r2 => k1, r2 => k2, r2 => k3, r2 => k4, r2 => k5, r2 => k6, r3 => k1, r3 => k2, r3 => k3, r3 => k4, r3 => k5, r3 => k6, r4 => k1, r4 => k2, r4 => k3, r4 => k4, r4 => k5, r4 => k6, r5 => k1, r5 => k2, r5 => k3, r5 => k4, r5 => k5, r5 => k6, r6 => k1, r6 => k2, r6 => k3, r6 => k4, r6 => k5, r6 => k6);
