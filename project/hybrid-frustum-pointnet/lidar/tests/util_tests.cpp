#include <gtest/gtest.h>

#include "../src/util/frustum.h"

TEST(FrustumTest, InsideX) {
  Vec3 origin(0.0f, 0.0f, 0.0f);
  std::array<Vec3, 4> corners = {
      Vec3(-1.0f, -1.0f, -1.0f),  // Upper left
      Vec3(-1.0f, 1.0f, -1.0f),   // Upper right
      Vec3(-1.0f, 1.0f, 1.0f),    // Lower right
      Vec3(-1.0f, -1.0f, 1.0f)    // Lower left
  };
}