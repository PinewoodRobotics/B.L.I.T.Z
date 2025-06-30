use crate::proto::util::{Vector2, Vector3};

macro_rules! impl_vector_conversions {
    ($proto_type:ty, $nalgebra_type:ty, $($field:ident => $accessor:ident),*) => {
        impl From<$proto_type> for $nalgebra_type {
            fn from(vector: $proto_type) -> Self {
                <$nalgebra_type>::new($(vector.$field.into()),*)
            }
        }

        impl From<$nalgebra_type> for $proto_type {
            fn from(vector: $nalgebra_type) -> Self {
                Self {
                    $($field: vector.$accessor.into()),*
                }
            }
        }
    };
}

impl_vector_conversions!(Vector3, nalgebra::Vector3<f32>, x => x, y => y, z => z);
impl_vector_conversions!(Vector2, nalgebra::Vector2<f32>, x => x, y => y);
